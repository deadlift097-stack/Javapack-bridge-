import json
import struct
import zipfile
import zlib

import pytest

from javapack_bridge import convert_pack
from javapack_bridge.cli import main


def make_png(w, h):
    raw = b"".join(b"\x00" + b"\xff\x00\x00\xff" * w for _ in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


@pytest.fixture
def java_pack(tmp_path):
    p = tmp_path / "Cool Pack.zip"
    T = "assets/minecraft/textures/"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("pack.mcmeta", json.dumps({"pack": {"pack_format": 15,
                   "description": [{"text": "Hello "}, {"text": "World"}]}}))
        z.writestr("pack.png", make_png(64, 64))
        z.writestr(T + "block/grass_block_side.png", make_png(16, 16))
        z.writestr(T + "block/oak_planks.png", make_png(16, 16))
        z.writestr(T + "block/light_gray_wool.png", make_png(16, 16))
        z.writestr(T + "block/stone.png", make_png(16, 16))
        z.writestr(T + "block/water_still.png", make_png(16, 64))
        z.writestr(T + "block/water_still.png.mcmeta",
                   json.dumps({"animation": {"frametime": 2}}))
        z.writestr(T + "item/golden_sword.png", make_png(16, 16))
        z.writestr(T + "entity/creeper/creeper.png", make_png(64, 32))
        z.writestr(T + "gui/widgets.png", make_png(256, 256))
        z.writestr("assets/minecraft/models/block/stone.json", "{}")
        z.writestr("assets/minecraft/sounds.json", "{}")
    return p


def read(out):
    z = zipfile.ZipFile(out)
    return z, set(z.namelist())


def test_conversion(java_pack, tmp_path):
    out = tmp_path / "o.mcpack"
    r = convert_pack(java_pack, out)
    z, names = read(out)
    assert {"manifest.json", "pack_icon.png", "textures/blocks/grass_side.png",
            "textures/blocks/planks_oak.png", "textures/blocks/wool_colored_silver.png",
            "textures/blocks/stone.png", "textures/items/gold_sword.png",
            "textures/entity/creeper/creeper.png", "textures/gui/widgets.png",
            "textures/terrain_texture.json", "textures/item_texture.json",
            "textures/flipbook_textures.json"} <= names
    man = json.loads(z.read("manifest.json"))
    assert man["header"]["description"] == "Hello World"
    assert man["header"]["uuid"] != man["modules"][0]["uuid"]
    terrain = json.loads(z.read("textures/terrain_texture.json"))["texture_data"]
    assert terrain["grass_side"]["textures"] == "textures/blocks/grass_side"
    assert "grass_block_side" not in terrain
    flip = json.loads(z.read("textures/flipbook_textures.json"))[0]
    assert flip["frames"] == [0, 1, 2, 3] and flip["ticks_per_frame"] == 2
    assert r.animations == 1 and r.renamed == 4
    assert any("unsupported: models" in k for k in r.skipped)


def test_deterministic_uuids(java_pack, tmp_path):
    convert_pack(java_pack, tmp_path / "a.mcpack")
    convert_pack(java_pack, tmp_path / "b.mcpack")
    ma = json.loads(zipfile.ZipFile(tmp_path / "a.mcpack").read("manifest.json"))
    mb = json.loads(zipfile.ZipFile(tmp_path / "b.mcpack").read("manifest.json"))
    assert ma == mb


def test_not_a_pack(tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("readme.txt", "x")
    with pytest.raises(ValueError):
        convert_pack(bad, tmp_path / "x.mcpack")


def test_wrapped_folder_and_cli(java_pack, tmp_path):
    wrapped = tmp_path / "wrapped.zip"
    with zipfile.ZipFile(java_pack) as src, zipfile.ZipFile(wrapped, "w") as dst:
        for n in src.namelist():
            dst.writestr("Inner/" + n, src.read(n))
    assert main([str(wrapped), "-o", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "wrapped.mcpack").exists()
