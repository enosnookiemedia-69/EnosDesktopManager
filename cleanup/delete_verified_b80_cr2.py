from pathlib import Path
import csv
import sys

BASE_DIR = Path(r"C:\Enos Desktop Manager")
APP_DIR = BASE_DIR / "Python App"

REPORT = APP_DIR / "cleanup" / "reports" / "2025_B80_CR2_reconciliation.csv"
B80_DIR = BASE_DIR / "2025" / "B80"

DELETE_CLASSIFICATION = "NO_MATCHING_DB_FILENAME_STEM"

print("=" * 70)
print("B80 VERIFIED CR2 DELETION")
print("=" * 70)

# Safety checks
if not REPORT.exists():
    print(f"ERROR: Reconciliation report not found:")
    print(REPORT)
    sys.exit(1)

if not B80_DIR.exists():
    print(f"ERROR: B80 folder not found:")
    print(B80_DIR)
    sys.exit(1)

# Read reconciliation report
candidates = []

with REPORT.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    required = {"Local Filename", "Local Full Path", "Classification"}
    missing = required - set(reader.fieldnames or [])

    if missing:
        print(f"ERROR: Report is missing columns: {sorted(missing)}")
        print("Columns found:")
        print(reader.fieldnames)
        sys.exit(1)

    for row in reader:
        if row["Classification"].strip() == DELETE_CLASSIFICATION:
            candidates.append(row)

print(f"Verified deletion candidates: {len(candidates)}")

# HARD SAFETY CHECK
if len(candidates) != 611:
    print()
    print("STOPPED.")
    print("Expected exactly 611 verified B80 deletion candidates.")
    print(f"Found: {len(candidates)}")
    print()
    print("No files were deleted.")
    sys.exit(1)

b80_resolved = B80_DIR.resolve()
paths = []

# Verify every candidate
for row in candidates:
    path = Path(row["Local Full Path"]).resolve()

    # Must be inside B80
    try:
        path.relative_to(b80_resolved)
    except ValueError:
        print()
        print("STOPPED.")
        print("A candidate is outside the B80 folder:")
        print(path)
        print()
        print("No files were deleted.")
        sys.exit(1)

    # Must be CR2
    if path.suffix.lower() != ".cr2":
        print()
        print("STOPPED.")
        print("A candidate is not a CR2 file:")
        print(path)
        print()
        print("No files were deleted.")
        sys.exit(1)

    paths.append(path)

# Verify all still exist
missing_files = [p for p in paths if not p.exists()]

if missing_files:
    print()
    print("STOPPED.")
    print(f"{len(missing_files)} candidate files no longer exist.")
    print("No files were deleted.")
    print()

    for p in missing_files[:20]:
        print(p)

    if len(missing_files) > 20:
        print(f"... and {len(missing_files) - 20} more.")

    sys.exit(1)

# Calculate size
total_bytes = sum(p.stat().st_size for p in paths)
total_gb = total_bytes / (1024 ** 3)

print()
print("Deletion set verified:")
print(f"  Files : {len(paths)}")
print(f"  Size  : {total_gb:.2f} GB")
print(f"  Folder: {B80_DIR}")
print()
print("The 158 matched B80 CR2 files will NOT be touched.")
print()

answer = input("Type DELETE B80 to continue: ").strip()

if answer != "DELETE B80":
    print()
    print("Cancelled. No files were deleted.")
    sys.exit(0)

# Delete
deleted = 0
deleted_bytes = 0
failed = []

for path in paths:
    try:
        size = path.stat().st_size
        path.unlink()
        deleted += 1
        deleted_bytes += size
    except Exception as e:
        failed.append((path, str(e)))

# Final report
print()
print("=" * 70)
print("B80 DELETION COMPLETE")
print("=" * 70)

print(f"Successfully deleted : {deleted}")
print(f"Failed                : {len(failed)}")
print(f"Space released        : {deleted_bytes / (1024 ** 3):.2f} GB")

if failed:
    print()
    print("FAILED FILES:")
    for path, error in failed:
        print(f"  {path}")
        print(f"    {error}")

print()
print("The 158 verified B80 CR2 files were protected.")
print("=" * 70)
