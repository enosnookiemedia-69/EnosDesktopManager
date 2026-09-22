from pathlib import Path
import csv
from collections import defaultdict

ROOT = Path(r"C:\Enos Desktop Manager")
APP = ROOT / "Python App"

DB_CSV = APP / "data" / "Enos_Media_Manager_v1 - Media Database (1).csv"
INDEX_CSV = APP / "original_image_index.csv"

REPORT_DIR = APP / "cleanup" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = REPORT_DIR / "2025_non_database_files.csv"


def norm(value):
    return str(value or "").strip().casefold()


def identity(year, photographer, filename):
    return (
        norm(year),
        norm(photographer),
        norm(filename),
    )


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
# Load Media Database
# ONLY 2025 records are considered.
# ------------------------------------------------------------
with DB_CSV.open("r", encoding="utf-8-sig", newline="") as f:
    db_rows = list(csv.DictReader(f))

db_2025 = [
    r for r in db_rows
    if norm(r.get("Year")) == "2025"
]

db_ids_2025 = {
    identity(
        r.get("Year"),
        r.get("Photographer"),
        r.get("File Name"),
    )
    for r in db_2025
    if norm(r.get("File Name"))
}


# ------------------------------------------------------------
# Load local original index
# ONLY 2025 files are considered.
# ------------------------------------------------------------
local_rows = []

with INDEX_CSV.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if norm(row.get("Year")) == "2025":
            local_rows.append(row)


# ------------------------------------------------------------
# Find exact 2025 non-DB files
# ------------------------------------------------------------
non_db = [
    r
    for r in local_rows
    if identity(
        r.get("Year"),
        r.get("Photographer"),
        r.get("Filename"),
    ) not in db_ids_2025
]


# ------------------------------------------------------------
# Write detailed CSV
# ------------------------------------------------------------
fields = list(local_rows[0].keys()) + ["Reason"]

with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for row in non_db:
        out = dict(row)
        out["Reason"] = (
            "2025_EXACT_YEAR_PHOTOGRAPHER_FILENAME_NOT_IN_MEDIA_DATABASE"
        )
        writer.writerow(out)


# ------------------------------------------------------------
# Summaries
# ------------------------------------------------------------
by_photographer = defaultdict(lambda: {"count": 0, "bytes": 0})
by_extension = defaultdict(lambda: {"count": 0, "bytes": 0})

for row in non_db:
    photographer = (
        str(row.get("Photographer") or "").strip()
        or "[BLANK]"
    )

    extension = (
        str(row.get("Extension") or "").strip().lower()
        or "[NO EXT]"
    )

    size = size_bytes(row)

    by_photographer[photographer]["count"] += 1
    by_photographer[photographer]["bytes"] += size

    by_extension[extension]["count"] += 1
    by_extension[extension]["bytes"] += size


total_bytes = sum(size_bytes(r) for r in non_db)


# ------------------------------------------------------------
# Print results
# ------------------------------------------------------------
print()
print("=" * 72)
print("2025-ONLY NON-DATABASE AUDIT")
print("=" * 72)
print()
print("YEAR BOUNDARY: 2025 ONLY")
print()
print("Matching rule:")
print("  Year + Photographer + Filename")
print("  Case-insensitive and trimmed")
print()
print("READ-ONLY:")
print("  No files were moved, renamed, modified or deleted.")
print()

print(f"2025 Media Database rows:          {len(db_2025):,}")
print(f"Unique 2025 DB identities:         {len(db_ids_2025):,}")
print(f"2025 local indexed images:         {len(local_rows):,}")
print(f"Exact 2025 DB matches:             {len(local_rows) - len(non_db):,}")
print(f"Exact 2025 non-DB files:           {len(non_db):,}")
print(f"Potential storage represented:     {gb(total_bytes):.2f} GB")
print()

print("-" * 72)
print("BY PHOTOGRAPHER")
print("-" * 72)

for name, data in sorted(
    by_photographer.items(),
    key=lambda x: (-x[1]["bytes"], x[0]),
):
    print(
        f"{name}: "
        f"{data['count']:,} files | "
        f"{gb(data['bytes']):.2f} GB"
    )

print()
print("-" * 72)
print("BY EXTENSION")
print("-" * 72)

for ext, data in sorted(
    by_extension.items(),
    key=lambda x: (-x[1]["bytes"], x[0]),
):
    print(
        f"{ext}: "
        f"{data['count']:,} files | "
        f"{gb(data['bytes']):.2f} GB"
    )

print()
print(f"Detailed report:")
print(OUT_CSV)
print()
print("=" * 72)
