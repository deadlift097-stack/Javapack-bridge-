"""Core Java -> Bedrock resource pack conversion (stdlib only)."""
from __future__ import annotations

import json
import re
import struct
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import mappings

NAMESPACE = uuid.UUID("6f1c2d4e-0a53-4a1e-9b7d-3c5e8a1f2b90")
MIN_ENGINE = [1, 20, 0]


@dataclass
class ConversionReport:
    name: str = ""
    converted: int = 0
    renamed: int = 0
    animations: int = 0
    skipped: dict = field(default_factory=dict)  # reason -> [paths]

    def skip(self, reason: str, path: str) -> None:
        self.skipped.setdefault(reason, []).append(path)

    def summary(self) -> str:
        lines = [f"Pack: {self.name}",
                 f"  textures converted: {self.converted} ({self.renamed} renamed)",
                 f"  animations:         {self.animations}"]
        for reason, paths in self.skipped.items():
            lines.append(f"  skipped ({reason}): {len(paths)}")
        return "\n".join(lines)


def _read_source(src: Path) -> dict[str, bytes]:
    """Load a pack (zip or folder) into {posix_path: bytes}."""
    files: dict[str, bytes] = {}
    if src.is_dir():
        for p in src.rglob("*"):
            if p.is_file():
                files[p.relative_to(src).as_posix()] = p.read_bytes()
    else:
        with zipfile.ZipFile(src) as z:
            for info in z.infolist():
                if not info.is_dir():
                    files[info.filename.replace("\\", "/")] = z.read(info)
    # Some zips wrap everything in one top-level folder.
    if "pack.mcmeta" not in files:
        tops = {k.split("/", 1)[0] for k in files if "/" in k}
        for t in tops:
            if f"{t}/pack.mcmeta" in files:
                n = len(t) + 1
                files = {k[n:]: v for k, v in files.items() if k.startswith(t + "/")}
                break
    return files


def _flatten_description(desc) -> str:
    if isinstance(desc, str):
        return re.sub("\u00a7.", "", desc)
    if isinstance(desc, list):
        return "".join(_flatten_description(d) for d in desc)
    if isinstance(desc, dict):
        return _flatten_description(desc.get("text", "")) + _flatten_description(desc.get("extra", ""))
    return ""


def _png_size(data: bytes):
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    return None


def _flipbook(bedrock_path: str, atlas_tile: str, png: bytes, meta: dict):
    anim = meta.get("animation", {})
    size = _png_size(png)
    default_frames = (size[1] // size[0]) if size and size[0] else 1
    frametime = max(1, int(anim.get("frametime", 1)))
    entry = {"flipbook_texture": bedrock_path, "atlas_tile": atlas_tile,
             "ticks_per_frame": frametime}
    frames = anim.get("frames")
    if frames:
        idx = []
        for f in frames:
            if isinstance(f, dict):
                idx.extend([int(f["index"])] * max(1, int(f.get("time", frametime)) // frametime))
            else:
                idx.append(int(f))
        entry["frames"] = idx
    else:
        entry["frames"] = list(range(default_frames))
    if anim.get("interpolate"):
        entry["blend_frames"] = True
    return entry


def convert_pack(src, out_path, display_name: str | None = None) -> ConversionReport:
    """Convert Java pack `src` (zip or dir) to a Bedrock .mcpack at `out_path`."""
    src, out_path = Path(src), Path(out_path)
    files = _read_source(src)
    report = ConversionReport()

    if "pack.mcmeta" not in files:
        raise ValueError("Not a Java resource pack: pack.mcmeta not found")
    meta = {}
    try:
        meta = json.loads(files["pack.mcmeta"].decode("utf-8-sig"))
    except ValueError:
        report.skip("unreadable pack.mcmeta", "pack.mcmeta")
    pack_meta = meta.get("pack", {}) if isinstance(meta, dict) else {}
    name = display_name or src.stem
    report.name = name
    description = _flatten_description(pack_meta.get("description", "")) or "Converted Java pack"

    out: dict[str, bytes] = {}
    terrain: dict[str, dict] = {}
    items: dict[str, dict] = {}
    flipbooks: list[dict] = []
    seen_bedrock: set[str] = set()
    routes = sorted(mappings.FOLDERS, key=len, reverse=True)

    for path, data in sorted(files.items()):
        if not path.startswith("assets/minecraft/textures/"):
            if path in ("pack.mcmeta", "pack.png") or path.endswith(".mcmeta"):
                continue
            if path.startswith("assets/minecraft/"):
                report.skip(f"unsupported: {path.split('/')[2]}", path)
            continue
        rel = PurePosixPath(path).relative_to("assets/minecraft/textures")
        suffix = rel.suffix.lower()
        if suffix == ".mcmeta":
            continue
        if suffix not in (".png", ".tga", ".jpg", ".jpeg"):
            report.skip("non-image file", path)
            continue

        rel_s = rel.as_posix()
        route = next((r for r in routes if rel_s.startswith(r + "/")), None)
        if route is None or suffix != ".png":
            out[f"textures/{rel_s}"] = data  # gui/, misc/, etc. keep their path
            report.converted += 1
            continue

        bed_folder, atlas = mappings.FOLDERS[route]
        stem = rel_s[len(route) + 1:-4]
        bed_stem = stem
        if atlas == "terrain":
            bed_stem = mappings.BLOCKS.get(stem, stem)
        elif atlas == "items":
            bed_stem = mappings.ITEMS.get(stem, stem)
        if bed_stem != stem:
            report.renamed += 1
        bed_path = f"{bed_folder}/{bed_stem}"
        if bed_path in seen_bedrock:
            report.skip("name collision", path)
            continue
        seen_bedrock.add(bed_path)
        out[f"{bed_path}.png"] = data
        report.converted += 1

        if atlas and "/" not in bed_stem:  # atlas keys are flat names
            (terrain if atlas == "terrain" else items)[bed_stem] = {"textures": bed_path}
        mcmeta = files.get(path + ".mcmeta")
        if mcmeta and atlas == "terrain" and "/" not in bed_stem:
            try:
                flipbooks.append(_flipbook(bed_path, bed_stem, data,
                                           json.loads(mcmeta.decode("utf-8-sig"))))
                report.animations += 1
            except (ValueError, KeyError):
                report.skip("bad animation mcmeta", path + ".mcmeta")
        elif mcmeta:
            report.skip("animation on non-block texture", path + ".mcmeta")

    if terrain:
        out["textures/terrain_texture.json"] = json.dumps({
            "resource_pack_name": name, "texture_name": "atlas.terrain",
            "padding": 8, "num_mip_levels": 4, "texture_data": terrain}, indent=2).encode()
    if items:
        out["textures/item_texture.json"] = json.dumps({
            "resource_pack_name": name, "texture_name": "atlas.items",
            "texture_data": items}, indent=2).encode()
    if flipbooks:
        out["textures/flipbook_textures.json"] = json.dumps(flipbooks, indent=2).encode()
    if "pack.png" in files:
        out["pack_icon.png"] = files["pack.png"]

    out["manifest.json"] = json.dumps({
        "format_version": 2,
        "header": {"name": name, "description": description,
                   "uuid": str(uuid.uuid5(NAMESPACE, name + "/header")),
                   "version": [1, 0, 0], "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "description": description,
                     "uuid": str(uuid.uuid5(NAMESPACE, name + "/module")),
                     "version": [1, 0, 0]}],
    }, indent=2).encode()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for k in sorted(out):
            z.writestr(k, out[k])
    return report
