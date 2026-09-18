"""
Enos Media Manager - Move Polaroids Files
-------------------------------------------
Moves the confirmed Polaroids images out of:
    C:\\Enos Desktop Manager\\2026\\Pacome\\
into their own folder:
    C:\\Enos Desktop Manager\\2026\\Polaroids\\

The filenames below were confirmed on 2026-09-17 by matching the
Media Database's "Polaroids" (2026) rows against the local
Pacome 2026 folder - all 28 filenames matched exactly.

USAGE
-----
Dry run first (default - does not move anything):
    python move_polaroids.py

Review the printed list, then actually move the files:
    python move_polaroids.py --move
"""

import argparse
import shutil
from pathlib import Path

SOURCE_FOLDER = Path(r"C:\Enos Desktop Manager\2026\Pacome")
DEST_FOLDER = Path(r"C:\Enos Desktop Manager\2026\Polaroids")

POLAROID_FILENAMES = [
    "PXL_20260501_171800896.jpg",
    "PXL_20260428_224239928.jpg",
    "PXL_20260428_172222709.NIGHT.jpg",
    "PXL_20260428_172130774.NIGHT.jpg",
    "PXL_20260503_173152787.jpg",
    "PXL_20260503_173126734.NIGHT.jpg",
    "PXL_20260503_173037394.jpg",
    "PXL_20260503_173013851.jpg",
    "PXL_20260503_172948081.jpg",
    "PXL_20260503_172928749.jpg",
    "PXL_20260503_172915976.jpg",
    "PXL_20260503_172851791.jpg",
    "PXL_20260503_172842255.jpg",
    "PXL_20260503_172823302.jpg",
    "PXL_20260503_172804447.jpg",
    "PXL_20260503_172657873.jpg",
    "PXL_20260503_172647316.jpg",
    "PXL_20260503_172608514.jpg",
    "PXL_20260503_172552359.jpg",
    "PXL_20260503_172356820.jpg",
    "PXL_20260503_173209548.jpg",
    "PXL_20260503_173109487.NIGHT.jpg",
    "PXL_20260503_172715972.jpg",
    "PXL_20260503_172635052.jpg",
    "PXL_20260503_172626365.jpg",
    "PXL_20260502_021036196.jpg",
    "PXL_20260502_021019485.jpg",
    "PXL_20260428_172151268.NIGHT.jpg",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--move", action="store_true",
                         help="Actually move the files. Without this flag, "
                              "only a dry-run report is printed.")
    args = parser.parse_args()

    if not SOURCE_FOLDER.is_dir():
        print(f"Source folder not found: {SOURCE_FOLDER}")
        return

    found = []
    missing = []
    for filename in POLAROID_FILENAMES:
        src = SOURCE_FOLDER / filename
        if src.is_file():
            found.append(src)
        else:
            missing.append(filename)

    print(f"Confirmed on disk in Pacome: {len(found)} / {len(POLAROID_FILENAMES)}")
    if missing:
        print("\nWARNING - not found in Pacome folder:")
        for m in missing:
            print(f"  {m}")

    if not found:
        print("\nNothing to move.")
        return

    print(f"\n{'Would move' if not args.move else 'Moving'} "
          f"{len(found)} files to: {DEST_FOLDER}\n")
    for f in found:
        print(f"  {f.name}")

    if args.move:
        DEST_FOLDER.mkdir(parents=True, exist_ok=True)
        moved = 0
        failed = 0
        for src in found:
            dest = DEST_FOLDER / src.name
            try:
                shutil.move(str(src), str(dest))
                moved += 1
            except OSError as e:
                print(f"[FAILED] {src.name}: {e}")
                failed += 1
        print(f"\nMoved {moved} files. Failed: {failed}")
    else:
        print("\nDry run only - no files were moved.")
        print("Re-run with --move to actually move them.")


if __name__ == "__main__":
    main()
