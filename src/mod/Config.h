#pragma once

#include <string>
#include <string_view>

#include <pl/Config.hpp>

namespace javapack_bridge {

struct ModConfig {
    int version = 1;
    bool enabled = true;
    bool autoConvertOnStartup = true;
    std::string javaPacksDir = "/sdcard/games/JavaPackBridge/packs";
    std::string bedrockResourcePacksDir = "/sdcard/games/com.mojang/resource_packs";
};

nlohmann::json makeDefaultConfigJson();
nlohmann::json makeConfigSchemaJson();

} // namespace javapack_bridge

template <> struct pl::config::Schema<javapack_bridge::ModConfig> {
    static constexpr std::string_view title = "JavaPack Bridge Config";
    static constexpr std::string_view description =
        "Settings for converting Java .zip resource packs to Bedrock.";

    static constexpr FieldSchema field(std::string_view name) {
        if (name == "version")
            return {.title = "Version", .readOnly = true};
        if (name == "enabled")
            return {.title = "Enabled", .description = "Enable or disable JavaPack Bridge."};
        if (name == "autoConvertOnStartup")
            return {.title = "Auto-Convert on Startup",
                    .description = "Automatically convert .zip packs placed in the Java packs folder when the game starts."};
        if (name == "javaPacksDir")
            return {.title = "Java Packs Folder",
                    .description = "Folder where Java Edition .zip resource packs are placed."};
        if (name == "bedrockResourcePacksDir")
            return {.title = "Bedrock Resource Packs Folder",
                    .description = "Target Bedrock games/com.mojang/resource_packs path."};
        return {};
    }
};
