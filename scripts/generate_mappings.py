#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from javapack_bridge import mappings


def main():
    lines = [
        "#pragma once",
        "",
        "#include <string>",
        "#include <string_view>",
        "#include <unordered_map>",
        "#include <vector>",
        "",
        "namespace javapack_bridge::mappings {",
        "",
        "struct FolderRoute {",
        "    std::string_view javaPrefix;",
        "    std::string_view bedrockFolder;",
        "    std::string_view atlasKind;",
        "};",
        "",
        "inline const std::vector<FolderRoute> FOLDERS = {",
    ]
    for java_dir in sorted(mappings.FOLDERS, key=len, reverse=True):
        bed_dir, atlas = mappings.FOLDERS[java_dir]
        lines.append(f'    {{"{java_dir}", "{bed_dir}", "{atlas or ""}"}},')
    lines += [
        "};",
        "",
        "inline const std::unordered_map<std::string_view, std::string_view> BLOCKS = {",
    ]
    for k, v in mappings.BLOCKS.items():
        lines.append(f'    {{"{k}", "{v}"}},')
    lines += [
        "};",
        "",
        "inline const std::unordered_map<std::string_view, std::string_view> ITEMS = {",
    ]
    for k, v in mappings.ITEMS.items():
        lines.append(f'    {{"{k}", "{v}"}},')
    lines += [
        "};",
        "",
        "} // namespace javapack_bridge::mappings",
        "",
    ]

    out = ROOT / "src/mod/Mappings.h"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
