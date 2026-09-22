from pathlib import Path
import csv
from collections import Counter

# ============================================================
# ENOS MEDIA MANAGER
# DEFINITE NON-DATABASE FILE CHECK
# ============================================================
#
# READ-ONLY.
#
# This script DOES NOT:
#   - delete files
#   - move files
#   - rename files
#   - modify files
#
# A local image is considered DEFINITELY NOT IN THE MEDIA
# DATABASE only when this exact identity is absent:
#
#     Year + Photographer + Filename
#
# Anything that does not meet this strict rule is NOT counted
# as a definite deletion candidate.
#
# ============================================================


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(r"C:\Enos Desktop Manager")

CSV_PATH = (
    ROOT
    / "Python App"
    / "data"
    / "Enos_Media_Manager_v1 - Media Database (1).csv"
)

INDEX_PATH = (
    ROOT
    / "Python App"
    / "original_image_index.csv"
)

REPORT_DIR = (
    ROOT
    / "Python App"
    / "cleanup"
    / "reports"
)


# ============================================================
# HELPERS
# ============================================================

def clean(value):
    return str(value or "").strip()


def key_part(value):
    return clean(value).casefold()


def make_key(year, photographer, filename):
    return (
        key_part(year),
        key_part(photographer),
        key_part(filename),
    )


def find_column(fieldnames, wanted):
    for field in fieldnames:
        if clean(field).casefold() == wanted.casefold():
            return field
    return None


# ============================================================
# PREFLIGHT
# ============================================================

print("\n" + "=" * 78)
print(" ENOS MEDIA MANAGER - DEFINITE NON-DATABASE CHECK")
print("=" * 78)

print("\nREAD-ONLY CHECK")
print("No files will be deleted, moved, renamed, or modified.")

print(f"\nMedia Database:")
print(f"  {CSV_PATH}")

print(f"\nOriginal image index:")
print(f"  {INDEX_PATH}")

if not CSV_PATH.is_file():
    raise SystemExit(
        f"\nERROR: Media Database not found:\n{CSV_PATH}"
    )

if not INDEX_PATH.is_file():
    raise SystemExit(
        f"\nERROR: Original image index not found:\n{INDEX_PATH}"
    )


# ============================================================
# LOAD MEDIA DATABASE
# ============================================================

print("\n" + "-" * 78)
print("LOADING MEDIA DATABASE")
print("-" * 78)

with CSV_PATH.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    db_fields = reader.fieldnames or []
    db_rows = list(reader)


db_year = find_column(db_fields, "Year")
db_photographer = find_column(db_fields, "Photographer")
db_filename = find_column(db_fields, "File Name")

if not db_year:
    raise SystemExit("ERROR: Media Database has no Year column.")

if not db_photographer:
    raise SystemExit(
        "ERROR: Media Database has no Photographer column."
    )

if not db_filename:
    raise SystemExit(
        "ERROR: Media Database has no File Name column."
    )


# ============================================================
# BUILD EXACT KEEP SET
# ============================================================

database_keys = set()

blank_database_records = 0

for row in db_rows:

    year = clean(row.get(db_year))
    photographer = clean(row.get(db_photographer))
    filename = clean(row.get(db_filename))

    if not filename:
        blank_database_records += 1
        continue

    database_keys.add(
        make_key(
            year,
            photographer,
            filename
        )
    )


# ============================================================
# LOAD ORIGINAL IMAGE INDEX
# ============================================================

print("\n" + "-" * 78)
print("LOADING ORIGINAL IMAGE INDEX")
print("-" * 78)

with INDEX_PATH.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    index_fields = reader.fieldnames or []
    index_rows = list(reader)


idx_year = find_column(index_fields, "Year")
idx_photographer = find_column(index_fields, "Photographer")
idx_filename = find_column(index_fields, "Filename")

if not idx_year:
    raise SystemExit("ERROR: Original index has no Year column.")

if not idx_photographer:
    raise SystemExit(
        "ERROR: Original index has no Photographer column."
    )

if not idx_filename:
    raise SystemExit(
        "ERROR: Original index has no Filename column."
    )


# ============================================================
# COMPARE
# ============================================================

definite_non_db = []
matched = []

duplicate_local_keys = Counter()

for row in index_rows:

    year = clean(row.get(idx_year))
    photographer = clean(row.get(idx_photographer))
    filename = clean(row.get(idx_filename))

    key = make_key(
        year,
        photographer,
        filename
    )

    duplicate_local_keys[key] += 1

    if key in database_keys:

        matched.append(row)

    else:

        definite_non_db.append(row)


# ============================================================
# DUPLICATES
# ============================================================

duplicate_groups = {
    key: count
    for key, count in duplicate_local_keys.items()
    if count > 1
}


# ============================================================
# WRITE REPORT
# ============================================================

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

report_path = (
    REPORT_DIR
    / "definite_non_database_files.csv"
)

report_fields = [
    "Year",
    "Photographer",
    "Filename",
    "Full Path",
    "Extension",
    "File Size (bytes)",
    "Width",
    "Height",
    "Date Taken",
    "EXIF Status",
    "Dimension Status",
    "Hash",
    "Reason",
]


with report_path.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=report_fields,
        extrasaction="ignore"
    )

    writer.writeheader()

    for row in definite_non_db:

        output = dict(row)

        output["Reason"] = (
            "EXACT_YEAR_PHOTOGRAPHER_FILENAME_NOT_IN_MEDIA_DATABASE"
        )

        writer.writerow(output)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 78)
print("RESULT")
print("=" * 78)

print(f"\nMedia Database rows:             {len(db_rows):,}")
print(f"Unique DB identities:            {len(database_keys):,}")
print(f"Blank DB filenames:              {blank_database_records:,}")

print(f"\nLocal indexed images:             {len(index_rows):,}")

print(f"\nExact DB matches:                 {len(matched):,}")

print(
    f"Definitely NOT in Media Database:"
    f" {len(definite_non_db):,}"
)

print(f"\nLocal duplicate identity groups:  {len(duplicate_groups):,}")

print("\n" + "-" * 78)
print("DEFINITION OF 'DEFINITE'")
print("-" * 78)

print(
    "\nA file is counted as DEFINITELY NOT IN THE DATABASE only when:"
)

print(
    "  Year + Photographer + Filename"
)

print(
    "does not exist in the Media Database."
)

print("\nNo fuzzy matching was used.")
print("No metadata assumptions were used.")
print("No files were changed.")

print("\nReport:")
print(f"  {report_path}")

print("\n" + "=" * 78)
print("CHECK COMPLETE - NOTHING WAS DELETED")
print("=" * 78)
