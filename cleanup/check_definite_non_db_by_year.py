from pathlib import Path
import csv

ROOT = Path(r"C:\Enos Desktop Manager")
APP = ROOT / "Python App"
DB_CSV = APP / "data" / "Enos_Media_Manager_v1 - Media Database (1).csv"
INDEX_CSV = APP / "original_image_index.csv"
REPORT_DIR = APP / "cleanup" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = REPORT_DIR / "definite_non_database_files_by_year.csv"


def norm(value):
    return str(value or "").strip().casefold()


def identity(year, photographer, filename):
    return (
        norm(year),
        norm(photographer),
        norm(filename),
    )


def size_bytes(rows):
    total = 0
    for r in rows:
        try:
            total += int(
                str(r.get("File Size (bytes)", "0"))
                .replace(",", "")
                .strip()
                or 0
            )
        except ValueError:
            pass
    return total


def gb(n):
    return n / (1024 ** 3)


# ------------------------------------------------------------
# Load Media Database
# ------------------------------------------------------------
with DB_CSV.open("r", encoding="utf-8-sig", newline="") as f:
    db_rows = list(csv.DictReader(f))

db_ids = {
    identity(
        r.get("Year"),
        r.get("Photographer"),
        r.get("File Name"),
    )
    for r in db_rows
    if norm(r.get("File Name"))
}


# ------------------------------------------------------------
# Load local original index
# ------------------------------------------------------------
local_rows = []

with INDEX_CSV.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        local_rows.append(row)


# ------------------------------------------------------------
# Find files NOT represented exactly in Media Database
# ------------------------------------------------------------
non_db = [
    r
    for r in local_rows
    if identity(
        r.get("Year"),
        r.get("Photographer"),
        r.get("Filename"),
    ) not in db_ids
]


# ------------------------------------------------------------
# Write detailed report
# ------------------------------------------------------------
fields = list(local_rows[0].keys()) + ["Reason"] if local_rows else []

with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for row in non_db:
        out = dict(row)
        out["Reason"] = (
            "EXACT_YEAR_PHOTOGRAPHER_FILENAME_NOT_IN_MEDIA_DATABASE"
        )
        writer.writerow(out)


# ------------------------------------------------------------
# Determine years
# ------------------------------------------------------------
years = sorted(
    {
        norm(r.get("Year"))
        for r in local_rows
    },
    key=lambda x: (
        not x.isdigit(),
        int(x) if x.isdigit() else x,
    ),
)


# ------------------------------------------------------------
# Print results
# ------------------------------------------------------------
print()
print("=" * 72)
print("DEFINITE NON-DATABASE AUDIT — YEAR-SEPARATED")
print("=" * 72)
print()
print("Matching rule:")
print("  Year + Photographer + Filename")
print("  Case-insensitive and trimmed")
print()
print("IMPORTANT:")
print("  Year is a HARD boundary.")
print("  A Media Database record from one year cannot protect")
print("  a local file from another year, even if the filename")
print("  is identical.")
print()

print(f"Media Database rows:              {len(db_rows):,}")
print(f"Unique DB identities:             {len(db_ids):,}")
print(f"Local indexed images:             {len(local_rows):,}")
print(f"Exact DB matches:                 {len(local_rows) - len(non_db):,}")
print(f"Definitely NOT in Media Database: {len(non_db):,}")
print()

for year in years:
    local_y = [
        r for r in local_rows
        if norm(r.get("Year")) == year
    ]

    non_y = [
        r for r in non_db
        if norm(r.get("Year")) == year
    ]

    match_y = len(local_y) - len(non_y)

    print(year or "[BLANK]")
    print(f"    Local indexed:                {len(local_y):,}")
    print(f"    Exact DB matches:             {match_y:,}")
    print(f"    Definitely outside DB:        {len(non_y):,}")
    print(f"    Outside DB size:              {gb(size_bytes(non_y)):.2f} GB")
    print()

print(f"TOTAL outside-DB size:             {gb(size_bytes(non_db)):.2f} GB")
print()
print(f"Report: {OUT_CSV}")
print("=" * 72)
