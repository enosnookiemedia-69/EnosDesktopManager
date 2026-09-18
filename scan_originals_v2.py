"""
Enos Media Manager - Original Image Folder Scanner (v2)
----------------------------------------------------------
Adds EXIF capture date/time and real HEIC dimension support on top
of the original scanner, so files can be matched against the Media
Database by DATE TAKEN + DIMENSIONS instead of filename (filenames
don't line up because the Media Database holds a separately
converted/renamed JPG export).

Expected structure (unchanged):

    C:\\Enos Desktop Manager\\
        2025\\
            Photographer Name\\
                image files...
        2026\\
            Photographer Name\\
                image files...

The source folders are READ-ONLY.
This script does not move, rename, delete, modify, resize,
compress, or rewrite any original files.

Creates: original_image_index.csv with columns:
    Year, Photographer, Filename, Full Path, Extension,
    File Size (bytes), Width, Height, Date Taken, EXIF Status, Hash

Date Taken is in the same format the Media Database uses:
    YYYY:MM:DD HH:MM:SS

EXIF Status tells you how much to trust a row:
    OK        - date and dimensions both read successfully
    NO_EXIF   - file opened fine but had no capture date (dimensions
                may still be present)
    UNREADABLE - could not open the file at all (e.g. unsupported
                RAW format without the right plugin); Date Taken
                and dimensions will be blank
"""

import sys
import csv
import hashlib
from pathlib import Path

# ------------------------------------------------------------------
# Pillow + HEIC support
# Install with:
#   py -m pip install Pillow pillow-heif
# ------------------------------------------------------------------
try:
    from PIL import Image, ExifTags
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False


ROOT_FOLDER = r"C:\Enos Desktop Manager"
OUTPUT_CSV = "original_image_index.csv"
SOURCE_YEARS = {"2025", "2026"}

VALID_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic",
    ".cr2", ".cr3", ".nef", ".arw", ".dng",
}

HASH_ALGORITHM = "sha256"

# EXIF tag id for DateTimeOriginal (fallback to DateTime if missing)
DATETIME_ORIGINAL_TAG = 36867
DATETIME_TAG = 306


def get_image_info(path):
    """
    Returns (width, height, date_taken_str, status).
    status is one of: OK, NO_EXIF, UNREADABLE
    """
    if not HAS_PIL:
        return None, None, None, "UNREADABLE"

    try:
        with Image.open(path) as img:
            width, height = img.width, img.height

            date_taken = None
            try:
                exif = img.getexif()
                if exif:
                    date_taken = exif.get(DATETIME_ORIGINAL_TAG) or exif.get(DATETIME_TAG)
            except Exception:
                date_taken = None

            if date_taken:
                return width, height, date_taken, "OK"
            else:
                return width, height, None, "NO_EXIF"

    except Exception:
        return None, None, None, "UNREADABLE"


def compute_hash(path, algorithm=HASH_ALGORITHM, chunk_size=1024 * 1024):
    if not algorithm:
        return ""
    hasher = hashlib.new(algorithm)
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as error:
        print(f"WARNING: Could not hash {path}\n         {error}")
        return ""


def scan_originals(root_folder):
    root = Path(root_folder)

    if not root.exists() or not root.is_dir():
        print(f"\nERROR: Root folder not found or not a folder:\n{root}")
        sys.exit(1)

    records = []
    skipped_files = 0
    scanned_files = 0
    status_counts = {"OK": 0, "NO_EXIF": 0, "UNREADABLE": 0}
    missing_years = []

    print()
    print("=" * 70)
    print("ENOS MEDIA MANAGER - ORIGINAL IMAGE SCANNER (v2)")
    print("=" * 70)
    print()
    print(f"HEIC support: {'ENABLED' if HAS_HEIF else 'NOT INSTALLED (pip install pillow-heif)'}")
    print(f"Source folder:\n  {root}")
    print()

    for year in sorted(SOURCE_YEARS):
        year_folder = root / year

        if not year_folder.exists():
            print(f"WARNING: Year folder not found: {year_folder}")
            missing_years.append(year)
            continue

        print(f"Scanning {year}...")

        photographer_folders = sorted(p for p in year_folder.iterdir() if p.is_dir())
        print(f"  Found {len(photographer_folders)} photographer folders.")

        for photographer_folder in photographer_folders:
            photographer = photographer_folder.name
            print(f"    {photographer}")

            for file_path in photographer_folder.rglob("*"):
                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()
                if ext not in VALID_EXTENSIONS:
                    skipped_files += 1
                    continue

                scanned_files += 1

                width, height, date_taken, status = get_image_info(file_path)
                status_counts[status] += 1

                try:
                    file_size = file_path.stat().st_size
                except Exception as error:
                    print(f"WARNING: Could not read file size:\n         {file_path}\n         {error}")
                    file_size = ""

                file_hash = compute_hash(file_path)

                records.append({
                    "Year": year,
                    "Photographer": photographer,
                    "Filename": file_path.name,
                    "Full Path": str(file_path),
                    "Extension": ext,
                    "File Size (bytes)": file_size,
                    "Width": width if width else "",
                    "Height": height if height else "",
                    "Date Taken": date_taken if date_taken else "",
                    "EXIF Status": status,
                    "Hash": file_hash,
                })

    print()
    print("=" * 70)
    print("SCAN COMPLETE")
    print("=" * 70)
    print()
    print(f"Images indexed:        {len(records)}")
    print(f"Files skipped:         {skipped_files}")
    print(f"  With date+dims OK:   {status_counts['OK']}")
    print(f"  No EXIF date:        {status_counts['NO_EXIF']}")
    print(f"  Unreadable (RAW etc):{status_counts['UNREADABLE']}")

    if missing_years:
        print("\nMissing year folders:")
        for year in missing_years:
            print(f"  {year}")

    print()
    return records


def write_csv(records, output_path):
    if not records:
        print("No records to write.")
        return

    fieldnames = [
        "Year", "Photographer", "Filename", "Full Path", "Extension",
        "File Size (bytes)", "Width", "Height", "Date Taken",
        "EXIF Status", "Hash",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Index CSV created:\n  {output_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = ROOT_FOLDER

    records = scan_originals(root)
    output_path = Path(__file__).parent / OUTPUT_CSV
    write_csv(records, output_path)

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print()
    print("The original files were NOT modified.")
    print(f"\nIndex saved to:\n  {output_path}")
    print()
    if not HAS_HEIF:
        print("NOTE: pillow-heif is not installed, so HEIC files got NO_EXIF/")
        print("UNREADABLE dimensions and dates. Install it for accurate results:")
        print("  py -m pip install pillow-heif")
        print()
