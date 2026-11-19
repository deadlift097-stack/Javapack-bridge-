#pragma once

#include <optional>
#include "mod/Config.h"
#include <pl/Mod.hpp>

namespace javapack_bridge {

class JavaPackMod {
  public:
    static JavaPackMod &instance();
    JavaPackMod();

    [[nodiscard]] ll::mod::NativeMod &getSelf() const { return mSelf; }

    bool load();
    bool enable();
    bool disable();
    bool unload();

    void syncJavaPacks();

  private:
    ll::mod::NativeMod &mSelf;
    ModConfig mConfig;
    std::optional<pl::config::ConfigFile<ModConfig>> mConfigFile;
};

} // namespace javapack_bridge
