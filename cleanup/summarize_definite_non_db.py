from pathlib import Path
import csv
from collections import defaultdict

APP = Path(r"C:\Enos Desktop Manager\Python App")
REPORT = APP / "cleanup" / "reports" / "definite_non_database_files_by_year.csv"

def norm(v):
    return str(v or "").strip().casefold()

def gb(n):
    return n / (1024 ** 3)

with REPORT.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

by_year = defaultdict(lambda: {"count": 0, "bytes": 0, "photographers": defaultdict(lambda: {"count": 0, "bytes": 0}), "extensions": defaultdict(lambda: {"count": 0, "bytes": 0})})

for r in rows:
    year = str(r.get("Year") or "").strip() or "[BLANK]"
    photographer = str(r.get("Photographer") or "").strip() or "[BLANK]"
    ext = str(r.get("Extension") or "").strip().lower() or "[NO EXT]"
    try:
        size = int(str(r.get("File Size (bytes)", "0")).replace(",", "").strip() or 0)
    except ValueError:
        size = 0

    y = by_year[year]
    y["count"] += 1
    y["bytes"] += size
    y["photographers"][photographer]["count"] += 1
    y["photographers"][photographer]["bytes"] += size
    y["extensions"][ext]["count"] += 1
    y["extensions"][ext]["bytes"] += size

print()
print("=" * 72)
print("DEFINITE NON-DATABASE SUMMARY")
print("=" * 72)
print(f"Candidate files: {len(rows):,}")
print()

for year in sorted(by_year):
    y = by_year[year]
    print(f"{year}: {y['count']:,} files | {gb(y['bytes']):.2f} GB")
    print("  By photographer:")
    for name, d in sorted(y["photographers"].items(), key=lambda x: (-x[1]["bytes"], x[0])):
        print(f"    {name}: {d['count']:,} files | {gb(d['bytes']):.2f} GB")
    print("  By extension:")
    for ext, d in sorted(y["extensions"].items(), key=lambda x: (-x[1]["bytes"], x[0])):
        print(f"    {ext}: {d['count']:,} files | {gb(d['bytes']):.2f} GB")
    print()

total_bytes = sum(y["bytes"] for y in by_year.values())
print(f"TOTAL: {len(rows):,} files | {gb(total_bytes):.2f} GB")
print("=" * 72)
