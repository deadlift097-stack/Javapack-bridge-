import argparse
import sys
from pathlib import Path

from . import __version__
from .convert import convert_pack


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="javapack-bridge",
                                 description="Convert Java resource packs to Bedrock .mcpack")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("pack", type=Path, nargs="+", help="Java pack .zip or folder")
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("."),
                    help="output directory (default: current)")
    ap.add_argument("-v", "--verbose", action="store_true", help="list skipped files")
    args = ap.parse_args(argv)

    rc = 0
    for pack in args.pack:
        try:
            report = convert_pack(pack, args.out_dir / f"{pack.stem}.mcpack")
        except (ValueError, OSError) as e:
            print(f"{pack}: {e}", file=sys.stderr)
            rc = 1
            continue
        print(report.summary())
        if args.verbose:
            for reason, paths in report.skipped.items():
                print(f"  [{reason}]")
                for p in paths:
                    print(f"    {p}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
