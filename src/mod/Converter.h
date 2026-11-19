#pragma once

#include <filesystem>
#include <string>

namespace javapack_bridge {

struct ConversionStats {
    std::string packName;
    int converted = 0;
    int renamed = 0;
    int animations = 0;
};

ConversionStats convertJavaZipToBedrockDir(
    const std::filesystem::path &zipPath,
    const std::filesystem::path &bedrockPacksRoot
);

} // namespace javapack_bridge
