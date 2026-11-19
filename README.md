# JavaPack Bridge

Use **Minecraft Java Edition resource packs** on **Bedrock** (including Android
launchers such as LeviLauncher). It converts a Java pack `.zip` or folder into a
Bedrock `.mcpack` you can import normally.

```
pip install .
javapack-bridge "My Java Pack.zip" -o out/      # -> out/My Java Pack.mcpack
javapack-bridge -v pack1.zip pack2.zip          # -v lists skipped files
```

Python 3.9+, no dependencies. Re-converting the same pack keeps the same UUIDs,
so Bedrock updates the pack instead of installing a duplicate.

## What converts

| Java | Bedrock |
|---|---|
| `pack.mcmeta` / `pack.png` | `manifest.json` / `pack_icon.png` |
| `textures/block/*` | `textures/blocks/*` + generated `terrain_texture.json` (names remapped, e.g. `oak_planks` -> `planks_oak`) |
| `textures/item/*` | `textures/items/*` + generated `item_texture.json` |
| `.png.mcmeta` block animations | `flipbook_textures.json` |
| `entity`, `environment`, `colormap`, `particle`, `painting`, `gui`, armor | copied to the matching Bedrock path |

## What does not convert (reported as skipped)

Java models and blockstates, CIT/CEM, sounds, language files, fonts, and shader
programs. Bedrock has no equivalent format for most of these, and the sound and
language keys differ between editions. Texture names missing from
`javapack_bridge/mappings.py` pass through unchanged; if a texture does not show
up in game, its name probably needs a mapping. PRs adding entries are welcome.

## Status

Tested with synthetic packs only (`pytest`). It has **not** yet been verified in
game against real packs, so expect gaps in the name tables. See
[docs/ROADMAP.md](docs/ROADMAP.md) for the planned in-game loader.
