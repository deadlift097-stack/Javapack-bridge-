# Roadmap: in-game loading like IriOptic

IriOptic (a `.levipack`) is a zip containing `manifest.json` (`"type": "preload-native"`,
`"entry": "libIriOptic.so"`), the AArch64 library, and an icon. Inspecting the library
shows what a native loader for this project would need:

- Exports `JNI_OnLoad` and `PLGetModRegistration`; links `libpreloader.so`.
- Uses `pl::memory::hook` / `unhook` to hook game functions, and
  `pl::modmenu::registerModule` to add an in-game menu entry.
- Embeds its Android UI as dex (a file picker for importing `.zip` packs, rescanning
  the pack folder, on/off toggles).

Goal: a `javapack-bridge.levipack` where the user picks a Java `.zip` in game and it
is converted and enabled without leaving the app.

## Phases

1. **Converter (done):** the Python tool in this repo. Fixes the format mapping.
2. **Port core to C++17:** miniz for zip, a small JSON lib, same mapping tables
   (generate them from `mappings.py` so there is one source of truth).
3. **Native mod:** NDK build producing `libJavaPackBridge.so`, registered through
   the preloader. On import, convert into `games/com.mojang/resource_packs/`.
   This needs the preloader's `ModuleInfo` / `ModRegistration` ABI, which I have not
   recovered; it must be taken from the preloader headers or its source.
4. **Pack refresh:** trigger the game's pack-list reload through a hooked
   resource-pack-manager function, rather than requiring a restart.
5. **CI:** GitHub Actions with the NDK to build and zip the `.levipack` artifact.

Phases 3 and 4 depend on the target Minecraft version's symbols, so they have to
be tested on a device.
