#include "mod/Converter.h"
#include "mod/Mappings.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <miniz.h>
#include <nlohmann/json.hpp>
#include <regex>
#include <set>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace javapack_bridge {
namespace {

using json = nlohmann::json;

std::string deterministicUuid(const std::string &seed) {
    uint64_t h1 = 14695981039346656037ULL;
    uint64_t h2 = 1099511628211ULL;
    for (unsigned char c : seed) {
        h1 ^= c;
        h1 *= 1099511628211ULL;
        h2 ^= (c + 0x9e);
        h2 *= 14695981039346656037ULL;
    }
    uint32_t time_low = static_cast<uint32_t>(h1 >> 32);
    uint16_t time_mid = static_cast<uint16_t>((h1 >> 16) & 0xFFFF);
    uint16_t time_hi = static_cast<uint16_t>((h1 & 0x0FFF) | 0x5000);
    uint16_t clock_seq = static_cast<uint16_t>(((h2 >> 48) & 0x3FFF) | 0x8000);
    uint64_t node = h2 & 0xFFFFFFFFFFFFULL;

    char buf[37];
    std::snprintf(buf, sizeof(buf), "%08x-%04x-%04x-%04x-%012llx",
                  time_low, time_mid, time_hi, clock_seq,
                  static_cast<unsigned long long>(node));
    return std::string(buf);
}

std::string flattenDescription(const json &desc) {
    if (desc.is_string()) {
        static const std::regex sectionRegex("\xC2\xA7.");
        return std::regex_replace(desc.get<std::string>(), sectionRegex, "");
    }
    if (desc.is_array()) {
        std::string out;
        for (const auto &item : desc) out += flattenDescription(item);
        return out;
    }
    if (desc.is_object()) {
        std::string out;
        if (desc.contains("text")) out += flattenDescription(desc["text"]);
        if (desc.contains("extra")) out += flattenDescription(desc["extra"]);
        return out;
    }
    return "";
}

std::pair<uint32_t, uint32_t> pngSize(const std::vector<uint8_t> &data) {
    static constexpr uint8_t sig[8] = {0x89, 'P', 'N', 'G', '\r', '\n', 0x1A, '\n'};
    if (data.size() >= 24 && std::memcmp(data.data(), sig, 8) == 0 &&
        std::memcmp(data.data() + 12, "IHDR", 4) == 0) {
        uint32_t w = (uint32_t(data[16]) << 24) | (uint32_t(data[17]) << 16) |
                     (uint32_t(data[18]) << 8) | uint32_t(data[19]);
        uint32_t h = (uint32_t(data[20]) << 24) | (uint32_t(data[21]) << 16) |
                     (uint32_t(data[22]) << 8) | uint32_t(data[23]);
        return {w, h};
    }
    return {0, 0};
}

json makeFlipbook(const std::string &bedrockPath, const std::string &atlasTile,
                  const std::vector<uint8_t> &png, const json &meta) {
    json anim = meta.value("animation", json::object());
    auto [w, h] = pngSize(png);
    int defaultFrames = (w > 0) ? std::max(1, int(h / w)) : 1;
    int frametime = std::max(1, anim.value("frametime", 1));

    json entry = {
        {"flipbook_texture", bedrockPath},
        {"atlas_tile", atlasTile},
        {"ticks_per_frame", frametime}
    };

    std::vector<int> framesOut;
    if (anim.contains("frames") && anim["frames"].is_array()) {
        for (const auto &f : anim["frames"]) {
            if (f.is_object()) {
                int idx = f.value("index", 0);
                int time = f.value("time", frametime);
                int count = std::max(1, time / frametime);
                for (int i = 0; i < count; ++i) framesOut.push_back(idx);
            } else if (f.is_number_integer()) {
                framesOut.push_back(f.get<int>());
            }
        }
    } else {
        for (int i = 0; i < defaultFrames; ++i) framesOut.push_back(i);
    }
    entry["frames"] = framesOut;
    if (anim.value("interpolate", false)) {
        entry["blend_frames"] = true;
    }
    return entry;
}

void writeFile(const std::filesystem::path &path, const uint8_t *data, size_t size) {
    std::error_code ec;
    std::filesystem::create_directories(path.parent_path(), ec);
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    out.write(reinterpret_cast<const char *>(data), static_cast<std::streamsize>(size));
}

void writeTextFile(const std::filesystem::path &path, const std::string &content) {
    writeFile(path, reinterpret_cast<const uint8_t *>(content.data()), content.size());
}

} // namespace

ConversionStats convertJavaZipToBedrockDir(
    const std::filesystem::path &zipPath,
    const std::filesystem::path &bedrockPacksRoot
) {
    mz_zip_archive zip{};
    if (!mz_zip_reader_init_file(&zip, zipPath.string().c_str(), 0)) {
        throw std::runtime_error("Failed to open zip: " + zipPath.string());
    }

    std::unordered_map<std::string, std::vector<uint8_t>> files;
    mz_uint numFiles = mz_zip_reader_get_num_files(&zip);
    for (mz_uint i = 0; i < numFiles; ++i) {
        if (mz_zip_reader_is_file_a_directory(&zip, i)) continue;
        char filename[1024];
        mz_zip_reader_get_filename(&zip, i, filename, sizeof(filename));
        std::string name(filename);
        std::replace(name.begin(), name.end(), '\\', '/');

        size_t uncompSize = 0;
        void *p = mz_zip_reader_extract_to_heap(&zip, i, &uncompSize, 0);
        if (p) {
            std::vector<uint8_t> buf(static_cast<uint8_t *>(p),
                                     static_cast<uint8_t *>(p) + uncompSize);
            mz_free(p);
            files.emplace(std::move(name), std::move(buf));
        }
    }
    mz_zip_reader_end(&zip);

    if (files.find("pack.mcmeta") == files.end()) {
        std::string topPrefix;
        for (const auto &[k, _] : files) {
            auto pos = k.find('/');
            if (pos != std::string::npos) {
                std::string candidate = k.substr(0, pos + 1);
                if (files.find(candidate + "pack.mcmeta") != files.end()) {
                    topPrefix = candidate;
                    break;
                }
            }
        }
        if (!topPrefix.empty()) {
            std::unordered_map<std::string, std::vector<uint8_t>> stripped;
            for (auto &[k, v] : files) {
                if (k.rfind(topPrefix, 0) == 0) {
                    stripped.emplace(k.substr(topPrefix.size()), std::move(v));
                }
            }
            files = std::move(stripped);
        }
    }

    auto mcmetaIt = files.find("pack.mcmeta");
    if (mcmetaIt == files.end()) {
        throw std::runtime_error("Not a Java resource pack (missing pack.mcmeta): " + zipPath.string());
    }

    json meta = json::object();
    try {
        std::string raw(mcmetaIt->second.begin(), mcmetaIt->second.end());
        if (raw.size() >= 3 && (unsigned char)raw[0] == 0xEF &&
            (unsigned char)raw[1] == 0xBB && (unsigned char)raw[2] == 0xBF) {
            raw.erase(0, 3);
        }
        meta = json::parse(raw);
    } catch (...) {}

    ConversionStats stats;
    stats.packName = zipPath.stem().string();
    std::string description = "Converted Java pack";
    if (meta.contains("pack") && meta["pack"].is_object() && meta["pack"].contains("description")) {
        auto parsed = flattenDescription(meta["pack"]["description"]);
        if (!parsed.empty()) description = parsed;
    }

    const std::filesystem::path targetDir = bedrockPacksRoot / ("jpb_" + stats.packName);
    std::error_code ec;
    std::filesystem::remove_all(targetDir, ec);
    std::filesystem::create_directories(targetDir, ec);

    json terrain = json::object();
    json items = json::object();
    json flipbooks = json::array();
    std::set<std::string> seenBedrock;

    const std::string texPrefix = "assets/minecraft/textures/";
    for (const auto &[path, data] : files) {
        if (path.rfind(texPrefix, 0) != 0) continue;
        std::string rel = path.substr(texPrefix.size());

        auto dotPos = rel.rfind('.');
        if (dotPos == std::string::npos) continue;
        std::string ext = rel.substr(dotPos);
        std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

        if (ext == ".mcmeta") continue;
        if (ext != ".png" && ext != ".tga" && ext != ".jpg" && ext != ".jpeg") continue;

        const mappings::FolderRoute *matchedRoute = nullptr;
        for (const auto &route : mappings::FOLDERS) {
            std::string prefix = std::string(route.javaPrefix) + "/";
            if (rel.rfind(prefix, 0) == 0) {
                matchedRoute = &route;
                break;
            }
        }

        if (!matchedRoute || ext != ".png") {
            writeFile(targetDir / "textures" / rel, data.data(), data.size());
            stats.converted++;
            continue;
        }

        std::string stem = rel.substr(matchedRoute->javaPrefix.size() + 1,
                                      rel.size() - matchedRoute->javaPrefix.size() - 1 - 4);
        std::string bedStem = stem;
        if (matchedRoute->atlasKind == "terrain") {
            auto it = mappings::BLOCKS.find(stem);
            if (it != mappings::BLOCKS.end()) bedStem = std::string(it->second);
        } else if (matchedRoute->atlasKind == "items") {
            auto it = mappings::ITEMS.find(stem);
            if (it != mappings::ITEMS.end()) bedStem = std::string(it->second);
        }

        if (bedStem != stem) stats.renamed++;

        std::string bedPath = std::string(matchedRoute->bedrockFolder) + "/" + bedStem;
        if (!seenBedrock.insert(bedPath).second) continue;

        writeFile(targetDir / (bedPath + ".png"), data.data(), data.size());
        stats.converted++;

        if (!matchedRoute->atlasKind.empty() && bedStem.find('/') == std::string::npos) {
            if (matchedRoute->atlasKind == "terrain") {
                terrain[bedStem] = {{"textures", bedPath}};
            } else {
                items[bedStem] = {{"textures", bedPath}};
            }
        }

        auto animIt = files.find(path + ".mcmeta");
        if (animIt != files.end() && matchedRoute->atlasKind == "terrain" &&
            bedStem.find('/') == std::string::npos) {
            try {
                std::string rawAnim(animIt->second.begin(), animIt->second.end());
                flipbooks.push_back(makeFlipbook(bedPath, bedStem, data, json::parse(rawAnim)));
                stats.animations++;
            } catch (...) {}
        }
    }

    if (!terrain.empty()) {
        json j = {
            {"resource_pack_name", stats.packName},
            {"texture_name", "atlas.terrain"},
            {"padding", 8},
            {"num_mip_levels", 4},
            {"texture_data", terrain}
        };
        writeTextFile(targetDir / "textures/terrain_texture.json", j.dump(2));
    }

    if (!items.empty()) {
        json j = {
            {"resource_pack_name", stats.packName},
            {"texture_name", "atlas.items"},
            {"texture_data", items}
        };
        writeTextFile(targetDir / "textures/item_texture.json", j.dump(2));
    }

    if (!flipbooks.empty()) {
        writeTextFile(targetDir / "textures/flipbook_textures.json", flipbooks.dump(2));
    }

    auto iconIt = files.find("pack.png");
    if (iconIt != files.end()) {
        writeFile(targetDir / "pack_icon.png", iconIt->second.data(), iconIt->second.size());
    }

    json manifest = {
        {"format_version", 2},
        {"header", {
            {"name", stats.packName},
            {"description", description},
            {"uuid", deterministicUuid(stats.packName + "/header")},
            {"version", {1, 0, 0}},
            {"min_engine_version", {1, 20, 0}}
        }},
        {"modules", json::array({
            {
                {"type", "resources"},
                {"description", description},
                {"uuid", deterministicUuid(stats.packName + "/module")},
                {"version", {1, 0, 0}}
            }
        })}
    };
    writeTextFile(targetDir / "manifest.json", manifest.dump(2));

    return stats;
}

} // namespace javapack_bridge
