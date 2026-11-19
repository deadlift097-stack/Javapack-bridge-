# JavaPack Bridge (LeviLauncher Edition)

Run **Minecraft Java Edition resource packs** (`.zip`) directly on **Minecraft Bedrock** via **LeviLauncher** (`.levipack`) or convert them on desktop via Python CLI.

## How it works on Android (LeviLauncher)

1. Download `javapack_bridge-<version>-arm64-v8a.levipack` from **Releases** (or build via GitHub Actions).
2. Import the `.levipack` into **LeviLauncher**.
3. Place any Java Edition resource pack `.zip` into `/sdcard/games/JavaPackBridge/packs/`.
4. Launch Minecraft — the native C++20 mod (`libJavaPackBridge.so`) automatically converts the Java textures, animations (`.png.mcmeta`), and pack metadata into `/sdcard/games/com.mojang/resource_packs/` so you can enable it under **Settings → Global Resources**.
5. You can also trigger an immediate re-scan anytime from the **LeviLauncher ModMenu** (`JavaPack Bridge`).

## Desktop Python CLI

```bash
pip install .
javapack-bridge "My Java Pack.zip" -o out/      # -> out/My Java Pack.mcpack
javapack-bridge -v pack1.zip pack2.zip          # -v lists skipped files
```

## Local Native Build (`.levipack`)

Requirements: Android SDK, Android NDK `28.2.13676358`, CMake `3.22+`, Ninja, PowerShell 7+.

```powershell
python scripts/generate_mappings.py
./scripts/package.ps1 -Abi arm64-v8a
```

## What converts

| Java Edition | Bedrock Edition |
|---|---|
| `pack.mcmeta` / `pack.png` | `manifest.json` / `pack_icon.png` |
| `textures/block/*` | `textures/blocks/*` + `terrain_texture.json` (remapped names, e.g. `oak_planks` -> `planks_oak`) |
| `textures/item/*` | `textures/items/*` + `item_texture.json` |
| `.png.mcmeta` block animations | `flipbook_textures.json` |
| `entity`, `environment`, `colormap`, `particle`, `painting`, `gui`, `models/armor` | copied to matching Bedrock paths |
