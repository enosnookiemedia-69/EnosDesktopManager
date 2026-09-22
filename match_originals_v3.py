"""
Enos Media Manager - Original vs Database Matcher / Deletion Audit (v3)
-------------------------------------------------------------------------
Replaces the old filename-matching audit (unsafe: the Media Database
holds Drive-exported filenames, not the original camera filenames)
with a DATE TAKEN based matcher.

Why Date Taken and not dimensions:
    The Media Database's Width/Height/Megapixels columns are the
    RESIZED Drive-export dimensions (e.g. 2048x1536), not the
    original camera resolution, so pixel dimensions can't be
    compared directly between the two files.

    Date Taken (EXIF DateTimeOriginal), however, survives the
    Drive export unchanged and matches the original to the exact
    second, e.g.:
        original IMG_0157.heic   -> 2025:04:27 15:26:46
        DB       IMG_0157.jpg    -> 2025:04:27 15:26:46

How matching works:
    1. Scoped to the same Year + Photographer (filenames alone are
       not unique across photographers).
    2. Within that scope, an original file is matched to a Database
       row if their Date Taken values are within TOLERANCE_SECONDS
       of each other (default 2 seconds, to allow for tiny rounding
       differences while still being effectively an exact match).
    3. Matching is one-to-one (a multiset match): once a DB
       timestamp is "claimed" by one original file, it can't also
       claim a second original file. This avoids one Database row
       falsely clearing multiple near-duplicate burst-shot originals.
    5. FALLBACK PASS: any original that still didn't match, and any DB row
       that's still unclaimed, are compared within the same group by exact
       FILENAME (ignoring extension, case-insensitive). This rescues cases
       where a camera's clock was wrong (confirmed for Mo's Fuji XT4 shots
       at Afrikaburn 2026 - DB Date Taken is the trustworthy one there) but
       the original camera filename survived the Drive export unchanged.
       These matches are flagged distinctly in the report ("Matched by
       FILENAME only") along with both dates, so they can be sanity-checked.
    6. Any original file whose EXIF Status is NOT "OK" (i.e. NO_EXIF
       or UNREADABLE - no trustworthy capture date) is automatically
       KEPT and never considered a deletion candidate, regardless of
       anything else. No date = no ability to verify = never touched.
    7. Any Database row that could not be matched to a local file by
       either date or filename is reported separately ("DB record not
       found locally") for manual review - it is NOT a signal to delete
       anything.

READ-ONLY: this script never deletes, moves, renames, or modifies
any file. It only writes report CSVs/TXT summarizing the findings.
"""

import sys
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# ------------------------------------------------------------------
# Configuration - adjust paths here if your layout differs
# ------------------------------------------------------------------
ORIGINAL_INDEX_CSV = r"C:\Enos Desktop Manager\Python App\original_image_index.csv"
MEDIA_DATABASE_CSV = r"C:\Enos Desktop Manager\Python App\data\Enos_Media_Manager_v1 - Media Database (1).csv"
REPORT_FOLDER = r"C:\Enos Desktop Manager\Python App\cleanup\reports"

TOLERANCE_SECONDS = 2  # how close two Date Taken values must be to count as a match

DATE_FORMAT = "%Y:%m:%d %H:%M:%S"

# Known cases where the Media Database's Photographer name differs from the
# local folder name for the same person/shoot. Keys and values are matched
# case-insensitively. The VALUE is the canonical name used for grouping and
# for display in the report.
PHOTOGRAPHER_ALIASES = {
    "herman": "Unicorn",
    "phil dustman": "Dustman",
}


def photographer_group_key(name):
    """Lowercase grouping key, after applying known aliases."""
    if not name:
        return ""
    lower = name.strip().lower()
    return PHOTOGRAPHER_ALIASES.get(lower, lower).lower()


def photographer_display_name(name):
    """Preferred display name for a grouping key: alias canonical value if
    aliased, otherwise the name as it appears in the local folder listing
    (Title Case if it was all-lowercase, e.g. 'dine' -> 'Dine')."""
    if not name:
        return name
    lower = name.strip().lower()
    if lower in PHOTOGRAPHER_ALIASES:
        return PHOTOGRAPHER_ALIASES[lower]
    stripped = name.strip()
    if stripped.islower():
        return stripped.title()
    return stripped


def parse_dt(value):
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        return None


def load_original_index(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["_dt"] = parse_dt(row.get("Date Taken", ""))
    return rows


def load_media_database(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["_dt"] = parse_dt(row.get("Date Taken", ""))
    return rows


def find_match(target_dt, available_counter, tolerance_seconds):
    """
    Find a DB timestamp within tolerance of target_dt that still has
    unused copies in available_counter. Returns the matched timestamp
    key, or None.
    """
    if target_dt is None:
        return None
    if available_counter.get(target_dt, 0) > 0:
        return target_dt
    if tolerance_seconds <= 0:
        return None
    best = None
    best_diff = None
    for dt, count in available_counter.items():
        if count <= 0:
            continue
        diff = abs((dt - target_dt).total_seconds())
        if diff <= tolerance_seconds and (best_diff is None or diff < best_diff):
            best = dt
            best_diff = diff
    return best


def filename_stem(filename):
    """Filename without extension, case-insensitive, for fallback matching
    across format conversions (e.g. IMG_0157.heic <-> IMG_0157.jpg) and
    for same-extension files whose EXIF date can't be trusted (e.g. a
    camera whose clock was wrong)."""
    if not filename:
        return ""
    stem = Path(filename).stem
    return stem.strip().lower()


def run_audit(original_rows, db_rows, tolerance_seconds):
    orig_groups = defaultdict(list)
    display_names = {}
    for row in original_rows:
        gkey = (row["Year"], photographer_group_key(row["Photographer"]))
        orig_groups[gkey].append(row)
        display_names.setdefault(gkey, photographer_display_name(row["Photographer"]))

    db_groups = defaultdict(list)
    for row in db_rows:
        gkey = (row["Year"], photographer_group_key(row["Photographer"]))
        db_groups[gkey].append(row)
        display_names.setdefault(gkey, photographer_display_name(row["Photographer"]))

    all_keys = sorted(set(orig_groups) | set(db_groups))

    kept_rows = []
    candidate_rows = []
    missing_db_rows = []
    per_photographer_stats = []

    for key in all_keys:
        year, _group_key = key
        photographer = display_names.get(key, _group_key)
        originals = orig_groups.get(key, [])
        db_items = db_groups.get(key, [])

        db_with_date = [r for r in db_items if r["_dt"] is not None]
        db_no_date = [r for r in db_items if r["_dt"] is None]

        available = Counter(r["_dt"] for r in db_with_date)

        matched_count = 0
        candidate_count = 0
        kept_no_exif_count = 0
        filename_fallback_count = 0

        pending_originals = []  # originals whose date didn't match - try filename next

        for orig in originals:
            if orig.get("EXIF Status") != "OK" or orig["_dt"] is None:
                kept_no_exif_count += 1
                kept_rows.append({**orig, "Photographer": photographer,
                                   "Match Reason": "No reliable EXIF date - always kept"})
                continue

            match_dt = find_match(orig["_dt"], available, tolerance_seconds)
            if match_dt is not None:
                available[match_dt] -= 1
                matched_count += 1
                kept_rows.append({**orig, "Photographer": photographer,
                                   "Match Reason": f"Matched DB Date Taken {match_dt}"})
            else:
                pending_originals.append(orig)

        # Collect DB rows still unclaimed by date, for the filename fallback pass
        remaining_by_dt = Counter(available)
        pending_db_rows = []
        for dt, count in remaining_by_dt.items():
            if count > 0:
                matches_for_dt = [r for r in db_with_date if r["_dt"] == dt]
                pending_db_rows.extend(matches_for_dt[:count])
        pending_db_rows.extend(db_no_date)

        # ---- Filename fallback pass ----
        # For originals whose date didn't match anything, try an exact
        # filename-stem match (case-insensitive, extension ignored) against
        # DB rows that are also still unmatched. This rescues cases like a
        # camera with a wrong/drifted clock, where the filename is still the
        # original camera-assigned name preserved through the Drive export.
        db_by_stem = defaultdict(list)
        for r in pending_db_rows:
            db_by_stem[filename_stem(r["File Name"])].append(r)

        still_pending_originals = []
        for orig in pending_originals:
            stem = filename_stem(orig["Filename"])
            candidates_for_stem = db_by_stem.get(stem)
            if candidates_for_stem:
                db_row = candidates_for_stem.pop(0)
                if not candidates_for_stem:
                    del db_by_stem[stem]
                pending_db_rows.remove(db_row)
                filename_fallback_count += 1
                matched_count += 1
                db_date = db_row.get("Date Taken", "") or "(none)"
                kept_rows.append({
                    **orig, "Photographer": photographer,
                    "Match Reason": (
                        f"Matched by FILENAME only - Date Taken disagrees "
                        f"(local: {orig.get('Date Taken', '')}, DB: {db_date}) "
                        f"- verify camera clock"
                    ),
                })
            else:
                still_pending_originals.append(orig)

        for orig in still_pending_originals:
            candidate_count += 1
            candidate_rows.append({**orig, "Photographer": photographer,
                                    "Match Reason": "No DB record with matching Date Taken or Filename"})

        group_missing_count = 0
        for r in pending_db_rows:
            issue = ("No local original with matching Date Taken or Filename"
                     if r["_dt"] is not None else
                     "DB record has no Date Taken, and no Filename match found")
            missing_db_rows.append({**r, "Photographer": photographer, "Issue": issue})
            group_missing_count += 1

        per_photographer_stats.append({
            "Year": year,
            "Photographer": photographer,
            "Local Originals": len(originals),
            "DB Records": len(db_items),
            "Matched (Keep)": matched_count,
            "  of which by filename fallback": filename_fallback_count,
            "No-EXIF (Keep)": kept_no_exif_count,
            "Deletion Candidates": candidate_count,
            "DB Not Found Locally": group_missing_count,
        })

    return kept_rows, candidate_rows, missing_db_rows, per_photographer_stats


def write_csv(rows, path, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    Path(REPORT_FOLDER).mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 78)
    print(" ENOS MEDIA MANAGER - DATE-BASED DELETION AUDIT (v3)")
    print("=" * 78)
    print(f"Tolerance:        {TOLERANCE_SECONDS} second(s)")
    print(f"Original index:   {ORIGINAL_INDEX_CSV}")
    print(f"Media Database:   {MEDIA_DATABASE_CSV}")
    print(f"Report folder:    {REPORT_FOLDER}")
    print()
    print("READ-ONLY: no files are deleted or modified by this script.")
    print()

    original_rows = load_original_index(ORIGINAL_INDEX_CSV)
    db_rows = load_media_database(MEDIA_DATABASE_CSV)

    kept_rows, candidate_rows, missing_db_rows, stats = run_audit(
        original_rows, db_rows, TOLERANCE_SECONDS
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    candidates_path = Path(REPORT_FOLDER) / f"v3_deletion_candidates_{timestamp}.csv"
    kept_path = Path(REPORT_FOLDER) / f"v3_kept_{timestamp}.csv"
    missing_path = Path(REPORT_FOLDER) / f"v3_db_not_found_locally_{timestamp}.csv"
    summary_path = Path(REPORT_FOLDER) / f"v3_summary_{timestamp}.txt"

    orig_fieldnames = ["Year", "Photographer", "Filename", "Full Path", "Extension",
                        "File Size (bytes)", "Width", "Height", "Date Taken",
                        "Fallback DateTime (untrusted)", "EXIF Status", "Hash", "Match Reason"]
    write_csv(candidate_rows, candidates_path, orig_fieldnames)
    write_csv(kept_rows, kept_path, orig_fieldnames)

    db_fieldnames = ["File Name", "Folder Path", "Year", "Photographer", "Date Taken",
                      "Grade", "Selection Stage", "Review Status", "Issue"]
    write_csv(missing_db_rows, missing_path, db_fieldnames)

    # ---- Console + text summary ----
    lines = []
    lines.append("=" * 78)
    lines.append(" ENOS MEDIA MANAGER - DATE-BASED DELETION AUDIT (v3)")
    lines.append("=" * 78)
    lines.append(f"Run: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Tolerance: {TOLERANCE_SECONDS} second(s)")
    lines.append("READ-ONLY AUDIT: NO FILES WERE DELETED OR MODIFIED.")
    lines.append("")
    lines.append("-" * 78)
    header = f"{'Photographer':<20}{'Year':<6}{'Local':>8}{'DB':>6}{'Match':>8}{'ByName':>8}{'NoExif':>8}{'Candidt':>9}{'DBmiss':>8}"
    lines.append(header)
    lines.append("-" * 78)

    totals = Counter()
    for s in sorted(stats, key=lambda x: (x["Year"], x["Photographer"])):
        lines.append(
            f"{s['Photographer']:<20}{s['Year']:<6}{s['Local Originals']:>8}"
            f"{s['DB Records']:>6}{s['Matched (Keep)']:>8}"
            f"{s['  of which by filename fallback']:>8}{s['No-EXIF (Keep)']:>8}"
            f"{s['Deletion Candidates']:>9}{s['DB Not Found Locally']:>8}"
        )
        totals["local"] += s["Local Originals"]
        totals["db"] += s["DB Records"]
        totals["matched"] += s["Matched (Keep)"]
        totals["by_name"] += s["  of which by filename fallback"]
        totals["no_exif"] += s["No-EXIF (Keep)"]
        totals["candidates"] += s["Deletion Candidates"]
        totals["db_missing"] += s["DB Not Found Locally"]

    lines.append("-" * 78)
    lines.append(
        f"{'TOTAL':<20}{'':<6}{totals['local']:>8}{totals['db']:>6}"
        f"{totals['matched']:>8}{totals['by_name']:>8}{totals['no_exif']:>8}"
        f"{totals['candidates']:>9}{totals['db_missing']:>8}"
    )
    lines.append("")
    lines.append("Columns: Local=local original files, DB=Media Database rows,")
    lines.append("Match=matched by Date Taken or filename fallback (KEEP), ByName=of Match,")
    lines.append("how many were rescued by the filename fallback specifically (date")
    lines.append("disagreed - worth spot-checking), NoExif=no reliable EXIF date (KEEP),")
    lines.append("Candidt=no matching DB record by date or filename (deletion candidate),")
    lines.append("DBmiss=DB rows with no matching local file (needs manual review, NOT a")
    lines.append("delete signal).")
    lines.append("")
    lines.append(f"Candidates CSV: {candidates_path}")
    lines.append(f"Kept CSV:       {kept_path}")
    lines.append(f"DB-not-found:   {missing_path}")
    lines.append("")
    lines.append("NEXT STEP: review the candidates CSV before deleting anything.")
    lines.append("This script does not delete files - a separate, explicitly")
    lines.append("confirmed deletion step would be needed after review.")

    summary_text = "\n".join(lines)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(summary_text)
    print()
    print(f"Summary report: {summary_path}")


if __name__ == "__main__":
    main()
