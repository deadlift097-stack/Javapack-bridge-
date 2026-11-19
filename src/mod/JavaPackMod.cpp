#include "mod/JavaPackMod.h"
#include "mod/Converter.h"

#include <filesystem>
#include <fstream>
#include <pl/Mod.hpp>
#include <pl/ModMenu.hpp>

namespace javapack_bridge {

JavaPackMod &JavaPackMod::instance() {
    static JavaPackMod instance;
    return instance;
}

JavaPackMod::JavaPackMod() : mSelf(*ll::mod::NativeMod::current()) {}

bool JavaPackMod::load() {
    auto &self = getSelf();
    std::error_code ec;
    std::filesystem::create_directories(self.getDataDir(), ec);
    std::filesystem::create_directories(self.getConfigDir(), ec);

    mConfigFile.emplace();
    if (!mConfigFile->load()) {
        self.getLogger().warn("Failed to load config; using defaults");
    } else {
        mConfig = mConfigFile->value();
    }

    std::filesystem::create_directories(mConfig.javaPacksDir, ec);
    self.getLogger().info("JavaPack Bridge loaded. Drop Java .zip packs into: {}", mConfig.javaPacksDir);
    return true;
}

bool JavaPackMod::enable() {
    auto &self = getSelf();
    if (!mConfig.enabled) {
        self.getLogger().info("JavaPack Bridge is disabled in config.");
        return true;
    }

    pl::modmenu::registerModule({
        .name = "JavaPack Bridge",
        .description = "Convert Java Edition .zip resource packs into Bedrock resource packs.",
        .onAction = [this]() { this->syncJavaPacks(); }
    });

    if (mConfig.autoConvertOnStartup) {
        syncJavaPacks();
    }

    return true;
}

bool JavaPackMod::disable() {
    pl::modmenu::unregisterModule("JavaPack Bridge");
    return true;
}

bool JavaPackMod::unload() {
    mConfigFile.reset();
    return true;
}

void JavaPackMod::syncJavaPacks() {
    auto &self = getSelf();
    std::error_code ec;
    const std::filesystem::path inputDir(mConfig.javaPacksDir);
    const std::filesystem::path outputDir(mConfig.bedrockResourcePacksDir);

    if (!std::filesystem::exists(inputDir, ec)) {
        std::filesystem::create_directories(inputDir, ec);
        return;
    }
    std::filesystem::create_directories(outputDir, ec);

    const std::filesystem::path stateDir = self.getDataDir() / "converted_stamps";
    std::filesystem::create_directories(stateDir, ec);

    for (const auto &entry : std::filesystem::directory_iterator(inputDir, ec)) {
        if (!entry.is_regular_file()) continue;
        if (entry.path().extension() != ".zip") continue;

        auto lastWrite = std::filesystem::last_write_time(entry.path(), ec).time_since_epoch().count();
        std::filesystem::path stampFile = stateDir / (entry.path().filename().string() + ".stamp");

        long long recordedWrite = 0;
        if (std::filesystem::exists(stampFile, ec)) {
            std::ifstream in(stampFile);
            in >> recordedWrite;
        }

        if (recordedWrite == lastWrite &&
            std::filesystem::exists(outputDir / ("jpb_" + entry.path().stem().string()), ec)) {
            continue;
        }

        try {
            auto stats = convertJavaZipToBedrockDir(entry.path(), outputDir);
            std::ofstream out(stampFile, std::ios::trunc);
            out << lastWrite;
            self.getLogger().info("Converted '{}' -> {} textures ({} renamed, {} animations)",
                                  stats.packName, stats.converted, stats.renamed, stats.animations);
        } catch (const std::exception &ex) {
            self.getLogger().error("Failed converting {}: {}", entry.path().filename().string(), ex.what());
        }
    }
}

} // namespace javapack_bridge
