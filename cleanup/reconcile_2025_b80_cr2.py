from pathlib import Path
import csv
from collections import defaultdict

ROOT = Path(r"C:\Enos Desktop Manager")
APP = ROOT / "Python App"

DB_CSV = APP / "data" / "Enos_Media_Manager_v1 - Media Database (1).csv"
INDEX_CSV = APP / "original_image_index.csv"

REPORT_DIR = APP / "cleanup" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = REPORT_DIR / "2025_B80_CR2_reconciliation.csv"


def norm(value):
    return str(value or "").strip().casefold()


def filename_stem(value):
    return Path(str(value or "").strip()).stem.casefold()


def size_bytes(row):
    try:
        return int(
            str(row.get("File Size (bytes)", "0"))
            .replace(",", "")
            .strip()
            or 0
        )
    except ValueError:
        return 0


def gb(value):
    return value / (1024 ** 3)


# ------------------------------------------------------------
# LOAD MEDIA DATABASE
# ------------------------------------------------------------
with DB_CSV.open("r", encoding="utf-8-sig", newline="") as f:
    db_rows = list(csv.DictReader(f))


# ------------------------------------------------------------
# 2025 B80 DATABASE RECORDS
#
# Local folder name:
#     B80
#
# Media Database photographer:
#     Photos B80
#
# We therefore identify B80 records using BOTH the photographer
# name and the folder path, rather than requiring an exact
# photographer-name match.
# ------------------------------------------------------------
db_b80 = []

for row in db_rows:

    if norm(row.get("Year")) != "2025":
        continue

    photographer = norm(row.get("Photographer"))
    folder_path = norm(row.get("Folder Path"))

    is_b80 = (
        photographer in {"b80", "photos b80"}
        or "photos b80" in folder_path
        or "b80 - cannon 700d" in folder_path
    )

    if is_b80 and norm(row.get("File Name")):
        db_b80.append(row)


# ------------------------------------------------------------
# LOAD LOCAL B80 CR2 FILES
# ------------------------------------------------------------
local_b80_cr2 = []

with INDEX_CSV.open("r", encoding="utf-8-sig", newline="") as f:

    for row in csv.DictReader(f):

        if (
            norm(row.get("Year")) == "2025"
            and norm(row.get("Photographer")) == "b80"
            and norm(row.get("Extension")) in {".cr2", "cr2"}
        ):
            local_b80_cr2.append(row)


# ------------------------------------------------------------
# INDEX DB RECORDS BY FILENAME STEM
#
# IMG_3404.jpg -> IMG_3404
# IMG_3404.CR2 -> IMG_3404
# ------------------------------------------------------------
db_by_stem = defaultdict(list)

for row in db_b80:

    filename = row.get("File Name", "")
    db_by_stem[filename_stem(filename)].append(row)


# ------------------------------------------------------------
# RECONCILE
# ------------------------------------------------------------
results = []

for local in local_b80_cr2:

    local_filename = local.get("Filename", "")
    local_stem = filename_stem(local_filename)

    matches = db_by_stem.get(local_stem, [])

    if matches:
        classification = "MATCHING_DB_FILENAME_DIFFERENT_EXTENSION"
        reason = (
            "Local B80 CR2 has the same filename stem as a "
            "2025 B80 Media Database record."
        )
    else:
        classification = "NO_MATCHING_DB_FILENAME_STEM"
        reason = (
            "No 2025 B80 Media Database record has the same "
            "filename stem."
        )

    db_names = " | ".join(
        str(m.get("File Name", ""))
        for m in matches
    )

    db_ids = " | ".join(
        str(m.get("File ID", ""))
        for m in matches
    )

    db_dimensions = " | ".join(
        f"{m.get('Width (px)', '')}x{m.get('Height (px)', '')}"
        for m in matches
    )

    db_extensions = " | ".join(
        str(m.get("File Extension", ""))
        for m in matches
    )

    db_paths = " | ".join(
        str(m.get("Folder Path", ""))
        for m in matches
    )

    results.append({
        "Year": local.get("Year", ""),
        "Photographer": local.get("Photographer", ""),
        "Local Filename": local_filename,
        "Local Full Path": local.get("Full Path", ""),
        "Local Extension": local.get("Extension", ""),
        "Local File Size (bytes)": local.get("File Size (bytes)", ""),
        "Local Width": local.get("Width", ""),
        "Local Height": local.get("Height", ""),
        "Local Date Taken": local.get("Date Taken", ""),
        "Local Camera Make": local.get("Camera Make", ""),
        "Local Camera Model": local.get("Camera Model", ""),
        "Classification": classification,
        "Reason": reason,
        "DB Filename": db_names,
        "DB File ID": db_ids,
        "DB Extension": db_extensions,
        "DB Dimensions": db_dimensions,
        "DB Folder Path": db_paths,
        "DB Match Count": len(matches),
    })


# ------------------------------------------------------------
# WRITE REPORT
# ------------------------------------------------------------
fields = [
    "Year",
    "Photographer",
    "Local Filename",
    "Local Full Path",
    "Local Extension",
    "Local File Size (bytes)",
    "Local Width",
    "Local Height",
    "Local Date Taken",
    "Local Camera Make",
    "Local Camera Model",
    "Classification",
    "Reason",
    "DB Filename",
    "DB File ID",
    "DB Extension",
    "DB Dimensions",
    "DB Folder Path",
    "DB Match Count",
]

with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------
summary = defaultdict(
    lambda: {
        "count": 0,
        "bytes": 0,
    }
)

for result, source in zip(results, local_b80_cr2):

    classification = result["Classification"]

    summary[classification]["count"] += 1
    summary[classification]["bytes"] += size_bytes(source)


total_bytes = sum(
    size_bytes(row)
    for row in local_b80_cr2
)


# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------
print()
print("=" * 72)
print("2025 B80 CR2 RECONCILIATION — CORRECTED")
print("=" * 72)
print()
print("READ-ONLY — NO FILES WERE MODIFIED OR DELETED")
print()
print("B80 naming handled as:")
print("  Local photographer:      B80")
print("  Media Database:          Photos B80")
print("  Folder:                  Photos B80 - Cannon 700D")
print()

print(f"2025 B80 Media Database records: {len(db_b80):,}")
print(f"2025 B80 local CR2 files:        {len(local_b80_cr2):,}")
print()

print("-" * 72)
print("CLASSIFICATION")
print("-" * 72)

for classification, data in sorted(
    summary.items(),
    key=lambda x: -x[1]["bytes"],
):

    print(
        f"{classification}: "
        f"{data['count']:,} files | "
        f"{gb(data['bytes']):.2f} GB"
    )

print()
print("-" * 72)
print("TOTAL")
print("-" * 72)

print(
    f"B80 CR2 files: {len(local_b80_cr2):,} | "
    f"{gb(total_bytes):.2f} GB"
)

print()
print("Report:")
print(OUT_CSV)
print()
print("=" * 72)
