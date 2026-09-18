"""
Enos Media Manager — Original Image Folder Scanner
---------------------------------------------------
Scans the Enos original image folders and creates an index CSV.

Expected structure:

    C:\Enos Desktop Manager\
        2025\
            Photographer Name\
                image files...
        2026\
            Photographer Name\
                image files...

The source folders are READ-ONLY.
This script does not move, rename, delete, modify, resize,
compress, or rewrite any original files.

It creates:
    original_image_index.csv

The CSV contains:
    Year
    Photographer
    Filename
    Full Path
    Extension
    File Size (bytes)
    Width
    Height
    Hash (SHA-256)
"""

import sys
import csv
import hashlib
from pathlib import Path

# Pillow is used to read image dimensions.
# Install with:
# py -m pip install Pillow

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ==========================================================
# SETTINGS
# ==========================================================

ROOT_FOLDER = r"C:\Enos Desktop Manager"

OUTPUT_CSV = "original_image_index.csv"

# Only scan these year folders.
SOURCE_YEARS = {"2025", "2026"}

# Image formats to include.
VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".cr2",
    ".cr3",
    ".nef",
    ".arw",
    ".dng",
}

# SHA-256 gives us a reliable way of identifying identical files.
HASH_ALGORITHM = "sha256"


# ==========================================================
# IMAGE DIMENSIONS
# ==========================================================

def get_image_dimensions(path):

    if not HAS_PIL:
        return None, None

    try:
        with Image.open(path) as img:
            return img.width, img.height

    except Exception:
        return None, None


# ==========================================================
# FILE HASH
# ==========================================================

def compute_hash(path, algorithm=HASH_ALGORITHM, chunk_size=1024 * 1024):

    if not algorithm:
        return ""

    hasher = hashlib.new(algorithm)

    try:
        with open(path, "rb") as f:

            for chunk in iter(
                lambda: f.read(chunk_size),
                b""
            ):
                hasher.update(chunk)

        return hasher.hexdigest()

    except Exception as error:

        print(f"WARNING: Could not hash {path}")
        print(f"         {error}")

        return ""


# ==========================================================
# SCAN ORIGINALS
# ==========================================================

def scan_originals(root_folder):

    root = Path(root_folder)

    if not root.exists():
        print()
        print("ERROR: Root folder not found:")
        print(root)
        sys.exit(1)

    if not root.is_dir():
        print()
        print("ERROR: Root path is not a folder:")
        print(root)
        sys.exit(1)

    records = []

    skipped_files = 0
    scanned_files = 0
    missing_years = []

    print()
    print("=" * 70)
    print("ENOS MEDIA MANAGER — ORIGINAL IMAGE SCANNER")
    print("=" * 70)
    print()
    print(f"Source folder:")
    print(f"  {root}")
    print()
    print("Years being scanned:")
    print(f"  {', '.join(sorted(SOURCE_YEARS))}")
    print()

    # ======================================================
    # YEAR FOLDERS
    # ======================================================

    for year in sorted(SOURCE_YEARS):

        year_folder = root / year

        if not year_folder.exists():
            print(f"WARNING: Year folder not found: {year_folder}")
            missing_years.append(year)
            continue

        if not year_folder.is_dir():
            print(f"WARNING: Not a folder: {year_folder}")
            continue

        print(f"Scanning {year}...")
        print(f"  {year_folder}")

        # ==================================================
        # PHOTOGRAPHER FOLDERS
        # ==================================================

        photographer_folders = sorted(
            p for p in year_folder.iterdir()
            if p.is_dir()
        )

        print(
            f"  Found {len(photographer_folders)} "
            f"photographer folders."
        )

        for photographer_folder in photographer_folders:

            photographer = photographer_folder.name

            print(f"    {photographer}")

            # ==================================================
            # IMAGE FILES
            # ==================================================

            for file_path in photographer_folder.rglob("*"):

                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()

                if ext not in VALID_EXTENSIONS:
                    skipped_files += 1
                    continue

                scanned_files += 1

                print(
                    f"      Indexing: {file_path.name}"
                )

                # ----------------------------------------------
                # Dimensions
                # ----------------------------------------------

                width, height = get_image_dimensions(
                    file_path
                )

                # ----------------------------------------------
                # File size
                # ----------------------------------------------

                try:
                    file_size = file_path.stat().st_size

                except Exception as error:

                    print(
                        f"WARNING: Could not read file size:"
                    )
                    print(f"         {file_path}")
                    print(f"         {error}")

                    file_size = ""

                # ----------------------------------------------
                # SHA-256
                # ----------------------------------------------

                file_hash = compute_hash(file_path)

                # ----------------------------------------------
                # Record
                # ----------------------------------------------

                records.append({

                    "Year": year,

                    "Photographer": photographer,

                    "Filename": file_path.name,

                    "Full Path": str(file_path),

                    "Extension": ext,

                    "File Size (bytes)": file_size,

                    "Width": width if width else "",

                    "Height": height if height else "",

                    "Hash": file_hash,
                })

    # ======================================================
    # SUMMARY
    # ======================================================

    print()
    print("=" * 70)
    print("SCAN COMPLETE")
    print("=" * 70)

    print()
    print(f"Images indexed:        {len(records)}")
    print(f"Files skipped:         {skipped_files}")

    if missing_years:

        print()
        print("Missing year folders:")

        for year in missing_years:
            print(f"  {year}")

    print()

    return records


# ==========================================================
# WRITE CSV
# ==========================================================

def write_csv(records, output_path):

    if not records:

        print("No records to write.")
        return

    fieldnames = [

        "Year",

        "Photographer",

        "Filename",

        "Full Path",

        "Extension",

        "File Size (bytes)",

        "Width",

        "Height",

        "Hash",
    ]

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(records)

    print(f"Index CSV created:")
    print(f"  {output_path}")


# ==========================================================
# DUPLICATE CHECK
# ==========================================================

def check_duplicates(records):

    seen = {}

    for record in records:

        key = (
            record["Year"],
            record["Photographer"],
            record["Filename"]
        )

        seen.setdefault(key, []).append(
            record["Full Path"]
        )

    duplicates = {
        key: paths
        for key, paths in seen.items()
        if len(paths) > 1
    }

    print()
    print("=" * 70)
    print("DUPLICATE CHECK")
    print("=" * 70)

    if duplicates:

        print()
        print(
            f"WARNING: {len(duplicates)} duplicate "
            "Year / Photographer / Filename combinations found."
        )

        for key, paths in duplicates.items():

            print()
            print(f"  {key}")

            for path in paths:
                print(f"    - {path}")

        print()
        print(
            "These files will need additional matching logic "
            "before the collector copies them."
        )

    else:

        print()
        print(
            "No duplicate Year / Photographer / Filename "
            "combinations found."
        )


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    # Allow an optional folder to be supplied from the command line.
    #
    # Example:
    #
    # py scan_originals.py "D:\Another Folder"

    if len(sys.argv) > 1:

        root = sys.argv[1]

    else:

        root = ROOT_FOLDER

    records = scan_originals(root)

    output_path = Path(__file__).parent / OUTPUT_CSV

    write_csv(
        records,
        output_path
    )

    check_duplicates(records)

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print()
    print("The original files were NOT modified.")
    print()
    print(f"Index saved to:")
    print(f"  {output_path}")
    print()
