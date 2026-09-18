from pathlib import Path
import csv
from collections import Counter, defaultdict
from datetime import datetime

# ============================================================
# ENOS MEDIA MANAGER - SAFE DELETION AUDIT
# ============================================================
# IMPORTANT:
# This script is READ-ONLY.
# It NEVER deletes, moves, renames, or modifies image files.
#
# Rule:
#   Keep a local image when its filename exists in the Media
#   Database for the same year + photographer.
#   A deletion candidate is a local image that is NOT in the
#   Media Database for that same year + photographer.
#
# Start with 2025. Review the report before any delete script
# is created or run.
# ============================================================

YEAR = "2025"

ROOT = Path(r"C:\Enos Desktop Manager")
IMAGE_ROOT = ROOT / YEAR
CSV_PATH = (
    ROOT
    / "Python App"
    / "data"
    / "Enos_Media_Manager_v1 - Media Database (1).csv"
)
REPORT_DIR = ROOT / "Python App" / "cleanup" / "reports"

# Only folders that have been deliberately downloaded/validated
# for this first 2025 test. Add others only after confirming them.
TARGET_PHOTOGRAPHERS = {
    "Unicorn",
    "Dustman",
    "Fiona",
    "Flora",
    "Chrissi",
    "Lara and Chris",
    "NinaMeana",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic", ".webp",
    ".tif", ".tiff", ".cr2", ".cr3", ".nef",
    ".arw", ".dng", ".raf", ".rw2", ".orf",
}

# ============================================================
# HELPERS
# ============================================================

def clean(value):
    return str(value or "").strip()


def find_column(fieldnames, wanted):
    for field in fieldnames:
        if clean(field).lower() == wanted.lower():
            return field
    return None


def filename_key(value):
    # Windows filenames are case-insensitive.
    return clean(value).casefold()


# ============================================================
# PREFLIGHT
# ============================================================

print("\n" + "=" * 78)
print(" ENOS MEDIA MANAGER - SAFE DELETION AUDIT")
print("=" * 78)
print(f"\nYear:           {YEAR}")
print(f"Image root:     {IMAGE_ROOT}")
print(f"Media Database: {CSV_PATH}")
print(f"Report folder:  {REPORT_DIR}")

if not IMAGE_ROOT.is_dir():
    raise SystemExit(f"\nERROR: Image root does not exist:\n{IMAGE_ROOT}")

if not CSV_PATH.is_file():
    raise SystemExit(f"\nERROR: Media Database CSV not found:\n{CSV_PATH}")

for photographer in sorted(TARGET_PHOTOGRAPHERS):
    folder = IMAGE_ROOT / photographer
    if not folder.is_dir():
        print(f"\nWARNING: Target folder not found: {folder}")

# ============================================================
# LOAD MEDIA DATABASE
# ============================================================

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames or []
    rows = list(reader)

year_col = find_column(fieldnames, "Year")
photographer_col = find_column(fieldnames, "Photographer")
filename_col = find_column(fieldnames, "File Name")

if not year_col:
    raise SystemExit("\nERROR: Could not find the 'Year' column.")

if not photographer_col:
    raise SystemExit("\nERROR: Could not find the 'Photographer' column.")

if not filename_col:
    raise SystemExit(
        "\nERROR: Could not find the 'File Name' column.\n"
        f"Available columns: {fieldnames}"
    )

# Database filenames by photographer.
db_files = defaultdict(set)
db_counts = Counter()
db_blank_filenames = []

for row in rows:
    year = clean(row.get(year_col))
    photographer = clean(row.get(photographer_col))
    filename = clean(row.get(filename_col))

    if year != YEAR:
        continue

    if photographer not in TARGET_PHOTOGRAPHERS:
        continue

    if not filename:
        db_blank_filenames.append((photographer, row))
        continue

    key = filename_key(filename)
    db_files[photographer].add(key)
    db_counts[photographer] += 1

# ============================================================
# SCAN LOCAL FILES
# ============================================================

local_files = defaultdict(list)
local_counts = Counter()

for photographer in sorted(TARGET_PHOTOGRAPHERS):
    folder = IMAGE_ROOT / photographer

    if not folder.is_dir():
        continue

    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS:
            local_files[photographer].append(path)
            local_counts[photographer] += 1

# ============================================================
# COMPARE
# ============================================================

kept = []
candidates = []
duplicates_in_db = []
missing_local = []

for photographer in sorted(TARGET_PHOTOGRAPHERS):
    db_set = db_files[photographer]
    local_set = set()

    for path in local_files[photographer]:
        key = filename_key(path.name)
        local_set.add(key)

        record = {
            "Year": YEAR,
            "Photographer": photographer,
            "Filename": path.name,
            "Full Path": str(path),
            "Reason": "",
        }

        if key in db_set:
            record["Reason"] = "MATCHED_IN_MEDIA_DATABASE"
            kept.append(record)
        else:
            record["Reason"] = "NOT_IN_MEDIA_DATABASE"
            candidates.append(record)

    for key in sorted(db_set - local_set):
        missing_local.append({
            "Year": YEAR,
            "Photographer": photographer,
            "Filename": key,
            "Reason": "IN_DATABASE_BUT_NOT_FOUND_LOCALLY",
        })

# Detect duplicate database filenames within each photographer.
for photographer in sorted(TARGET_PHOTOGRAPHERS):
    seen = Counter()
    for row in rows:
        if (
            clean(row.get(year_col)) == YEAR
            and clean(row.get(photographer_col)) == photographer
        ):
            filename = clean(row.get(filename_col))
            if filename:
                seen[filename_key(filename)] += 1

    for key, count in seen.items():
        if count > 1:
            duplicates_in_db.append({
                "Year": YEAR,
                "Photographer": photographer,
                "Filename": key,
                "Occurrences": count,
            })

# ============================================================
# REPORT
# ============================================================

REPORT_DIR.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

summary_path = REPORT_DIR / f"deletion_audit_{YEAR}_{stamp}.txt"
candidates_path = REPORT_DIR / f"deletion_candidates_{YEAR}_{stamp}.csv"
kept_path = REPORT_DIR / f"deletion_kept_{YEAR}_{stamp}.csv"
missing_path = REPORT_DIR / f"database_missing_locally_{YEAR}_{stamp}.csv"

with candidates_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["Year", "Photographer", "Filename", "Full Path", "Reason"],
    )
    writer.writeheader()
    writer.writerows(candidates)

with kept_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["Year", "Photographer", "Filename", "Full Path", "Reason"],
    )
    writer.writeheader()
    writer.writerows(kept)

with missing_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["Year", "Photographer", "Filename", "Reason"],
    )
    writer.writeheader()
    writer.writerows(missing_local)

lines = []
lines.append("=" * 78)
lines.append(" ENOS MEDIA MANAGER - DELETION AUDIT REPORT")
lines.append("=" * 78)
lines.append(f"Year: {YEAR}")
lines.append(f"Run:  {datetime.now().isoformat(timespec='seconds')}")
lines.append("")
lines.append("READ-ONLY AUDIT: NO FILES WERE DELETED OR MODIFIED.")
lines.append("")
lines.append("-" * 78)
lines.append("PHOTOGRAPHER COUNTS")
lines.append("-" * 78)
lines.append(
    f"{'Photographer':<30} {'DB':>8} {'LOCAL':>8} {'KEEP':>8} {'CANDIDATE':>11}"
)

for photographer in sorted(TARGET_PHOTOGRAPHERS):
    keep_count = sum(
        1 for r in kept if r["Photographer"] == photographer
    )
    candidate_count = sum(
        1 for r in candidates if r["Photographer"] == photographer
    )
    lines.append(
        f"{photographer:<30} "
        f"{db_counts[photographer]:>8} "
        f"{local_counts[photographer]:>8} "
        f"{keep_count:>8} "
        f"{candidate_count:>11}"
    )

lines.append("")
lines.append("-" * 78)
lines.append("TOTALS")
lines.append("-" * 78)
lines.append(f"Database records:                 {sum(db_counts.values()):,}")
lines.append(f"Local image files:                {sum(local_counts.values()):,}")
lines.append(f"Matched / KEEP:                   {len(kept):,}")
lines.append(f"Deletion candidates:              {len(candidates):,}")
lines.append(f"Database files missing locally:   {len(missing_local):,}")
lines.append(f"Blank database filenames:         {len(db_blank_filenames):,}")
lines.append(f"Duplicate DB filename groups:     {len(duplicates_in_db):,}")

lines.append("")
lines.append("-" * 78)
lines.append("SAFETY NOTES")
lines.append("-" * 78)
lines.append("1. This report is READ-ONLY.")
lines.append("2. Only the explicitly listed 2025 photographer folders were scanned.")
lines.append("3. A local file is a candidate only when its filename is absent from")
lines.append("   the Media Database for the same Year + Photographer.")
lines.append("4. No RAW/JPG/HEIC substitutions or fuzzy filename matching are used.")
lines.append("5. Missing database files and duplicate database names must be reviewed")
lines.append("   before any deletion is considered.")
lines.append("")
lines.append("Reports:")
lines.append(f"  Candidates: {candidates_path}")
lines.append(f"  Kept:       {kept_path}")
lines.append(f"  Missing:    {missing_path}")
lines.append("")

summary_path.write_text("\n".join(lines), encoding="utf-8")

# ============================================================
# CONSOLE OUTPUT
# ============================================================

print("\n" + "\n".join(lines))

if candidates:
    print("\n" + "-" * 78)
    print("DELETION CANDIDATES")
    print("-" * 78)

    for photographer in sorted(TARGET_PHOTOGRAPHERS):
        items = [
            r for r in candidates
            if r["Photographer"] == photographer
        ]

        if not items:
            continue

        print(f"\n{photographer} ({len(items)} candidates)")

        for item in items[:25]:
            print(f"  {item['Filename']}")

        if len(items) > 25:
            print(f"  ... plus {len(items) - 25} more; see CSV report.")

else:
    print("\nNO DELETION CANDIDATES FOUND.")

print("\n" + "=" * 78)
print(" AUDIT COMPLETE - NOTHING WAS DELETED")
print("=" * 78)
print(f"\nSummary report: {summary_path}")
print(f"Candidate CSV:  {candidates_path}")
print(f"Kept CSV:       {kept_path}")
print(f"Missing CSV:    {missing_path}")
