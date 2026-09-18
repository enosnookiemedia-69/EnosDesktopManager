from pathlib import Path
import csv
from collections import Counter


# ============================================================
# CONFIG
# ============================================================

CSV_PATH = Path(
    r"C:\Enos Desktop Manager\Python App\data"
    r"\Enos_Media_Manager_v1 - Media Database (1).csv"
)

DOWNLOADED_2025 = {
    "Unicorn",
    "Dustman",
    "Fiona",
    "Flora",
    "Chrissi",
    "Lara and Chris",
    "NinaMeana",
}


# ============================================================
# LOAD CSV
# ============================================================

if not CSV_PATH.exists():
    print(f"\nERROR: CSV not found:")
    print(CSV_PATH)
    input("\nPress Enter to exit...")
    raise SystemExit(1)


with CSV_PATH.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    fieldnames = reader.fieldnames or []
    rows = list(reader)


# ============================================================
# REPORT
# ============================================================

print("\n")
print("=" * 70)
print(" ENOS MEDIA DATABASE INSPECTION")
print("=" * 70)

print(f"\nCSV:")
print(CSV_PATH)

print(f"\nTotal data rows: {len(rows):,}")


# ------------------------------------------------------------
# COLUMNS
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("COLUMNS")
print("-" * 70)

for number, field in enumerate(fieldnames, 1):
    print(f"{number:3}: {field}")


# ------------------------------------------------------------
# FIND YEAR COLUMN
# ------------------------------------------------------------

year_column = None

for field in fieldnames:
    if field.strip().lower() == "year":
        year_column = field
        break

if not year_column:
    print("\nERROR: Could not find a 'Year' column.")
    input("\nPress Enter to exit...")
    raise SystemExit(1)


# ------------------------------------------------------------
# FIND PHOTOGRAPHER COLUMN
# ------------------------------------------------------------

photographer_column = None

for field in fieldnames:
    if field.strip().lower() == "photographer":
        photographer_column = field
        break

if not photographer_column:
    print("\nERROR: Could not find a 'Photographer' column.")
    input("\nPress Enter to exit...")
    raise SystemExit(1)


# ------------------------------------------------------------
# FILTER 2025
# ------------------------------------------------------------

rows_2025 = []

for row in rows:

    year = str(row.get(year_column, "")).strip()

    if year == "2025":
        rows_2025.append(row)


print("\n" + "-" * 70)
print("2025 SUMMARY")
print("-" * 70)

print(f"2025 records: {len(rows_2025):,}")


# ------------------------------------------------------------
# PHOTOGRAPHERS
# ------------------------------------------------------------

photographers = Counter()

for row in rows_2025:

    photographer = str(
        row.get(photographer_column, "")
    ).strip()

    if photographer:
        photographers[photographer] += 1


print("\n2025 photographers:\n")

for photographer, count in sorted(
    photographers.items(),
    key=lambda x: (-x[1], x[0].lower())
):
    print(f"  {photographer:<35} {count:>5}")


# ------------------------------------------------------------
# DOWNLOADED PHOTOGRAPHERS
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("DOWNLOADED 2025 PHOTOGRAPHERS")
print("-" * 70)

for photographer in sorted(DOWNLOADED_2025):

    count = photographers.get(photographer, 0)

    if count:
        print(f"  FOUND     {photographer:<30} {count:>5} records")
    else:
        print(f"  NOT FOUND {photographer:<30}")


# ------------------------------------------------------------
# EXAMPLE RECORDS
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("EXAMPLE 2025 RECORDS")
print("-" * 70)

shown = 0

for row in rows_2025:

    photographer = str(
        row.get(photographer_column, "")
    ).strip()

    if photographer in DOWNLOADED_2025:

        print("\nPhotographer:", photographer)

        for field, value in row.items():

            value = str(value).strip()

            if value:
                print(f"  {field}: {value}")

        shown += 1

        if shown >= 5:
            break


print("\n" + "=" * 70)
print(" INSPECTION COMPLETE")
print("=" * 70)

input("\nPress Enter to exit...")
