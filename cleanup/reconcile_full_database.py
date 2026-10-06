
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import csv


# ============================================================================
# ENOS MEDIA MANAGER - FULL DATABASE RECONCILIATION
# ============================================================================
#
# READ-ONLY
#
# This script:
#   1. Reads the Media Database CSV
#   2. Reads the local original-image index
#   3. Matches local originals against Media Database records
#   4. Adds Pixieset totals as a THIRD reference dataset
#   5. Produces detailed reconciliation reports
#
# IMPORTANT:
#   Pixieset totals are REFERENCE COUNTS ONLY.
#   They are NOT used to decide whether an individual file is non-DB.
#   They are NOT used to delete files.
#
# NOTHING IS MODIFIED, MOVED, RENAMED OR DELETED.
#
# ============================================================================


# ============================================================================
# CONFIGURATION
# ============================================================================

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


# ============================================================================
# PIXIESET REFERENCE TOTALS
# ============================================================================
#
# These totals are supplied reference counts.
#
# IMPORTANT:
#   They do NOT participate in individual-file matching.
#
# Use normalized photographer names here.
#
# "tom" / "thomas" is deliberately omitted for 2025 because the Pixieset
# total is unknown.
#
# ============================================================================

PIXIESET_TOTALS = {

    2025: {
        "lara and chris": 72,
        "unicorn": 17,
        "flora": 13,
        "fiona": 14,
        "ninameana": 48,
        "pacome": 196,
        "chrissi": 141,
        "b80": 158,
        "dustman": 26,
        # Tom/Thomas = UNKNOWN
    },

    2026: {
        "polaroids": 28,
        "jason": 143,
        "dani": 25,
        "sla": 13,
        "thomas": 46,
        "dd": 47,
        "unicorn": 54,
        "diana": 24,
        "nina": 38,
        "mo": 50,
        "dustman": 17,
        "pacome": 203,
        "sam": 12,
        "peter": 26,
    },
}


# ============================================================================
# PHOTOGRAPHER ALIASES
# ============================================================================
#
# These are used only for matching the same photographer when the naming
# convention differs between datasets.
#
# The original folder / database values are retained in the reports.
#
# IMPORTANT:
#   "photos b80" -> "b80" is included because the current reconciliation
#   clearly shows:
#
#       Local 2025 b80       = 158
#       Media DB photos b80  = 158
#       Pixieset B80         = 158
#
# This means those 158 records should be treated as a NAME MISMATCH to
# investigate, not simply as ordinary non-DB files.
#
# ============================================================================

PHOTOGRAPHER_ALIASES = {

    # 2025 B80 naming discrepancy
    "photos b80": "b80",

    # Existing known aliases
    "herman": "unicorn",
    "phil dustman": "dustman",
}


# ============================================================================
# SUPPORTED IMAGE EXTENSIONS
# ============================================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
    ".cr2",
    ".cr3",
    ".nef",
    ".arw",
    ".dng",
    ".tif",
    ".tiff",
}


# ============================================================================
# BASIC HELPERS
# ============================================================================

def clean(value):
    """Convert None to blank and strip surrounding whitespace."""
    if value is None:
        return ""

    return str(value).strip()


def normalize_text(value):
    """Case-insensitive normalized text."""
    return clean(value).casefold()


def normalize_year(value):
    """Normalize year values such as 2025 or 2025.0."""
    value = clean(value)

    if not value:
        return ""

    try:
        return str(int(float(value)))
    except ValueError:
        return value.casefold()


def normalize_photographer(value):
    """
    Normalize photographer names and apply explicit aliases.
    """
    value = normalize_text(value)

    return PHOTOGRAPHER_ALIASES.get(value, value)


def filename_stem(value):
    """
    Return filename stem without extension.

    Example:
        IMG_1234.CR2 -> img_1234
    """
    value = clean(value)

    if not value:
        return ""

    return Path(value).stem.casefold()


def filename_extension(value):
    """
    Return lowercase extension.
    """
    value = clean(value)

    if not value:
        return ""

    return Path(value).suffix.casefold()


def normalize_filename(value):
    """
    Normalize filename for exact matching.
    """
    return clean(value).casefold()


def normalize_date(value):
    """
    Normalize Date Taken text.

    This intentionally does not try to guess or alter timestamps.
    """
    return clean(value).casefold()


def make_identity_key(year, photographer, filename):
    return (
        normalize_year(year),
        normalize_photographer(photographer),
        normalize_filename(filename),
    )


def make_group_key(year, photographer):
    return (
        normalize_year(year),
        normalize_photographer(photographer),
    )


def make_date_key(year, photographer, date_taken):
    return (
        normalize_year(year),
        normalize_photographer(photographer),
        normalize_date(date_taken),
    )


def make_stem_key(year, photographer, filename):
    return (
        normalize_year(year),
        normalize_photographer(photographer),
        filename_stem(filename),
    )


def find_column(fieldnames, desired_names):
    """
    Find a column by case-insensitive name.

    desired_names can be a string or a list/tuple.
    """
    if isinstance(desired_names, str):
        desired_names = [desired_names]

    normalized = {
        clean(name).casefold(): name
        for name in fieldnames
    }

    for desired in desired_names:
        key = clean(desired).casefold()

        if key in normalized:
            return normalized[key]

    return None


# ============================================================================
# PIXIESET HELPERS
# ============================================================================

def get_pixieset_total(year, photographer):
    """
    Return the Pixieset reference total for a year/photographer.

    Returns None when the Pixieset total is unknown/not supplied.
    """
    try:
        year_int = int(normalize_year(year))
    except ValueError:
        return None

    photographer_key = normalize_photographer(photographer)

    return PIXIESET_TOTALS.get(year_int, {}).get(
        photographer_key
    )


def pixieset_status(local_count, db_count, pixieset_count):
    """
    Compare the three datasets.

    Pixieset is reference information only.
    """

    if pixieset_count is None:
        return "PIXIESET_UNKNOWN"

    if db_count == pixieset_count:
        if local_count == pixieset_count:
            return "ALL_THREE_COUNTS_MATCH"

        return "DB_MATCHES_PIXIESET"

    if local_count == pixieset_count:
        return "LOCAL_MATCHES_PIXIESET"

    return "COUNTS_DIFFER"


# ============================================================================
# PRE-FLIGHT
# ============================================================================

def preflight():
    print()
    print("=" * 78)
    print("ENOS MEDIA MANAGER - FULL DATABASE RECONCILIATION")
    print("=" * 78)
    print()
    print("READ-ONLY — NO FILES WILL BE MODIFIED OR DELETED")
    print()

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Media Database CSV not found:\n{CSV_PATH}"
        )

    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Original image index not found:\n{INDEX_PATH}"
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("SOURCE FILES")
    print("-" * 78)
    print(f"Media Database:")
    print(f"  {CSV_PATH}")
    print()
    print(f"Original Image Index:")
    print(f"  {INDEX_PATH}")
    print()


# ============================================================================
# LOAD MEDIA DATABASE
# ============================================================================

def load_media_database():

    with CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise RuntimeError(
                "Media Database CSV has no header row."
            )

        fieldnames = reader.fieldnames

        year_col = find_column(
            fieldnames,
            ["Year"]
        )

        photographer_col = find_column(
            fieldnames,
            ["Photographer"]
        )

        filename_col = find_column(
            fieldnames,
            ["File Name", "Filename", "FileName"]
        )

        date_col = find_column(
            fieldnames,
            ["Date Taken", "DateTaken"]
        )

        file_id_col = find_column(
            fieldnames,
            ["File ID", "FileID", "ID"]
        )

        if not year_col:
            raise RuntimeError(
                "Media Database is missing a Year column."
            )

        if not photographer_col:
            raise RuntimeError(
                "Media Database is missing a Photographer column."
            )

        if not filename_col:
            raise RuntimeError(
                "Media Database is missing a File Name/Filename column."
            )

        rows = []

        for row in reader:

            row["_year_col"] = clean(row.get(year_col))
            row["_photographer_col"] = clean(
                row.get(photographer_col)
            )
            row["_filename_col"] = clean(
                row.get(filename_col)
            )

            row["_date_col"] = (
                clean(row.get(date_col))
                if date_col
                else ""
            )

            row["_file_id_col"] = (
                clean(row.get(file_id_col))
                if file_id_col
                else ""
            )

            rows.append(row)

    return rows, {
        "year": year_col,
        "photographer": photographer_col,
        "filename": filename_col,
        "date": date_col,
        "file_id": file_id_col,
    }


# ============================================================================
# LOAD ORIGINAL IMAGE INDEX
# ============================================================================

def load_original_index():

    with INDEX_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise RuntimeError(
                "Original Image Index has no header row."
            )

        fieldnames = reader.fieldnames

        year_col = find_column(
            fieldnames,
            ["Year"]
        )

        photographer_col = find_column(
            fieldnames,
            ["Photographer"]
        )

        filename_col = find_column(
            fieldnames,
            ["Filename", "File Name", "FileName"]
        )

        date_col = find_column(
            fieldnames,
            ["Date Taken", "DateTaken"]
        )

        if not year_col:
            raise RuntimeError(
                "Original Image Index is missing Year."
            )

        if not photographer_col:
            raise RuntimeError(
                "Original Image Index is missing Photographer."
            )

        if not filename_col:
            raise RuntimeError(
                "Original Image Index is missing Filename."
            )

        rows = []

        for row in reader:

            row["_year_col"] = clean(row.get(year_col))

            row["_photographer_col"] = clean(
                row.get(photographer_col)
            )

            row["_filename_col"] = clean(
                row.get(filename_col)
            )

            row["_date_col"] = (
                clean(row.get(date_col))
                if date_col
                else ""
            )

            rows.append(row)

    return rows, {
        "year": year_col,
        "photographer": photographer_col,
        "filename": filename_col,
        "date": date_col,
    }


# ============================================================================
# BUILD DATABASE INDEXES
# ============================================================================

def build_database_indexes(db_rows):

    exact = defaultdict(list)
    dates = defaultdict(list)
    stems = defaultdict(list)

    blank_filename_count = 0
    blank_date_count = 0

    for index, row in enumerate(db_rows):

        year = row["_year_col"]
        photographer = row["_photographer_col"]
        filename = row["_filename_col"]
        date_taken = row["_date_col"]

        if not filename:
            blank_filename_count += 1

        if not date_taken:
            blank_date_count += 1

        exact[
            make_identity_key(
                year,
                photographer,
                filename
            )
        ].append(index)

        if date_taken:

            dates[
                make_date_key(
                    year,
                    photographer,
                    date_taken
                )
            ].append(index)

        if filename:

            stems[
                make_stem_key(
                    year,
                    photographer,
                    filename
                )
            ].append(index)

    return {
        "exact": exact,
        "dates": dates,
        "stems": stems,
        "blank_filename_count": blank_filename_count,
        "blank_date_count": blank_date_count,
    }


# ============================================================================
# EXTENSION COMPATIBILITY
# ============================================================================

def extensions_are_compatible(local_filename, db_filename):

    local_ext = filename_extension(local_filename)
    db_ext = filename_extension(db_filename)

    if not local_ext or not db_ext:
        return True

    if local_ext == db_ext:
        return True

    return (
        local_ext in IMAGE_EXTENSIONS
        and db_ext in IMAGE_EXTENSIONS
    )


# ============================================================================
# CHOOSE UNUSED DATABASE RECORD
# ============================================================================

def choose_unused(candidates, used_db_indices):

    for db_index in candidates:

        if db_index not in used_db_indices:
            return db_index

    return None


# ============================================================================
# MATCH ONE LOCAL FILE
# ============================================================================

def match_local_row(
    local_row,
    db_rows,
    db_indexes,
    used_db_indices,
):

    year = local_row["_year_col"]
    photographer = local_row["_photographer_col"]
    filename = local_row["_filename_col"]
    date_taken = local_row["_date_col"]

    # ------------------------------------------------------------------------
    # 1. EXACT FILENAME
    # ------------------------------------------------------------------------

    exact_key = make_identity_key(
        year,
        photographer,
        filename
    )

    exact_candidates = db_indexes["exact"].get(
        exact_key,
        []
    )

    db_index = choose_unused(
        exact_candidates,
        used_db_indices
    )

    if db_index is not None:

        return (
            "MATCHED",
            "EXACT_FILENAME",
            db_index,
            ""
        )

    # ------------------------------------------------------------------------
    # 2. DATE TAKEN
    # ------------------------------------------------------------------------

    if date_taken:

        date_key = make_date_key(
            year,
            photographer,
            date_taken
        )

        date_candidates = [
            index
            for index in db_indexes["dates"].get(
                date_key,
                []
            )
            if index not in used_db_indices
        ]

        if len(date_candidates) == 1:

            return (
                "MATCHED",
                "DATE_TAKEN",
                date_candidates[0],
                ""
            )

        if len(date_candidates) > 1:

            return (
                "UNCERTAIN",
                "AMBIGUOUS_DATE",
                None,
                "Multiple unused Media Database records have the same "
                "Year + Photographer + Date Taken."
            )

    # ------------------------------------------------------------------------
    # 3. FILENAME STEM FALLBACK
    # ------------------------------------------------------------------------

    if filename:

        stem_key = make_stem_key(
            year,
            photographer,
            filename
        )

        stem_candidates = []

        for index in db_indexes["stems"].get(
            stem_key,
            []
        ):

            if index in used_db_indices:
                continue

            db_filename = db_rows[index]["_filename_col"]

            if extensions_are_compatible(
                filename,
                db_filename
            ):
                stem_candidates.append(index)

        if len(stem_candidates) == 1:

            return (
                "MATCHED",
                "FILENAME_STEM",
                stem_candidates[0],
                ""
            )

        if len(stem_candidates) > 1:

            return (
                "UNCERTAIN",
                "AMBIGUOUS_FILENAME_STEM",
                None,
                "Multiple unused Media Database records share "
                "the same Year + Photographer + filename stem."
            )

    # ------------------------------------------------------------------------
    # 4. NO RELIABLE EXIF
    # ------------------------------------------------------------------------

    if not date_taken:

        return (
            "UNCERTAIN",
            "NO_RELIABLE_EXIF",
            None,
            "No usable Date Taken value was available and no "
            "filename relationship was found."
        )

    # ------------------------------------------------------------------------
    # 5. NO MATCH
    # ------------------------------------------------------------------------

    return (
        "DEFINITE_NON_DB",
        "NO_MATCH",
        None,
        "No approved matching method found a relationship to "
        "an unused Media Database record."
    )


# ============================================================================
# RECONCILE LOCAL COLLECTION
# ============================================================================

def reconcile(local_rows, db_rows, db_indexes):

    used_db_indices = set()

    output_rows = []

    counters = Counter()

    group_summary = defaultdict(
        lambda: {
            "local": 0,
            "matched": 0,
            "uncertain": 0,
            "non_db": 0,
            "match_types": Counter(),
        }
    )

    for local_row in local_rows:

        status, match_type, db_index, reason = match_local_row(
            local_row,
            db_rows,
            db_indexes,
            used_db_indices,
        )

        result = dict(local_row)

        result["Reconciliation Status"] = status
        result["Match Type"] = match_type
        result["Match Reason"] = reason

        result["DB Photographer"] = ""
        result["DB Filename"] = ""
        result["DB Date Taken"] = ""
        result["DB File ID"] = ""

        result["Photographer Alias Applied"] = ""

        local_photographer = local_row[
            "_photographer_col"
        ]

        normalized_original = normalize_text(
            local_photographer
        )

        normalized_result = normalize_photographer(
            local_photographer
        )

        if normalized_original != normalized_result:

            result["Photographer Alias Applied"] = (
                f"{local_photographer} -> "
                f"{normalized_result}"
            )

        if db_index is not None:

            used_db_indices.add(db_index)

            db_row = db_rows[db_index]

            result["DB Photographer"] = db_row[
                "_photographer_col"
            ]

            result["DB Filename"] = db_row[
                "_filename_col"
            ]

            result["DB Date Taken"] = db_row[
                "_date_col"
            ]

            result["DB File ID"] = db_row[
                "_file_id_col"
            ]

        counters[status] += 1
        counters[match_type] += 1

        group_key = make_group_key(
            local_row["_year_col"],
            local_row["_photographer_col"]
        )

        group = group_summary[group_key]

        group["local"] += 1
        group["match_types"][match_type] += 1

        if status == "MATCHED":
            group["matched"] += 1

        elif status == "UNCERTAIN":
            group["uncertain"] += 1

        elif status == "DEFINITE_NON_DB":
            group["non_db"] += 1

        output_rows.append(result)

    return (
        output_rows,
        used_db_indices,
        counters,
        group_summary,
    )


# ============================================================================
# DATABASE RECORDS NOT FOUND LOCALLY
# ============================================================================

def build_db_not_found(
    db_rows,
    used_db_indices
):

    rows = []

    for index, row in enumerate(db_rows):

        if index in used_db_indices:
            continue

        result = dict(row)

        result["Reconciliation Status"] = (
            "DB_NOT_FOUND_LOCALLY"
        )

        result["Match Type"] = ""
        result["Match Reason"] = (
            "Media Database record was not matched to "
            "a local indexed original."
        )

        result["Potential Pixieset Photographer"] = (
            normalize_photographer(
                row["_photographer_col"]
            )
        )

        rows.append(result)

    return rows


# ============================================================================
# BUILD THREE-WAY SUMMARY
# ============================================================================

def build_three_way_summary(
    local_rows,
    db_rows,
    reconciliation_rows
):

    # ------------------------------------------------------------------------
    # LOCAL COUNTS
    # ------------------------------------------------------------------------

    local_counts = Counter()

    for row in local_rows:

        key = make_group_key(
            row["_year_col"],
            row["_photographer_col"]
        )

        local_counts[key] += 1

    # ------------------------------------------------------------------------
    # DATABASE COUNTS
    # ------------------------------------------------------------------------

    db_counts = Counter()

    for row in db_rows:

        key = make_group_key(
            row["_year_col"],
            row["_photographer_col"]
        )

        db_counts[key] += 1

    # ------------------------------------------------------------------------
    # RECONCILIATION COUNTS
    # ------------------------------------------------------------------------

    matched_counts = Counter()
    uncertain_counts = Counter()
    non_db_counts = Counter()

    for row in reconciliation_rows:

        key = make_group_key(
            row["_year_col"],
            row["_photographer_col"]
        )

        status = row["Reconciliation Status"]

        if status == "MATCHED":
            matched_counts[key] += 1

        elif status == "UNCERTAIN":
            uncertain_counts[key] += 1

        elif status == "DEFINITE_NON_DB":
            non_db_counts[key] += 1

    # ------------------------------------------------------------------------
    # UNION OF ALL KNOWN GROUPS
    # ------------------------------------------------------------------------

    all_keys = (
        set(local_counts)
        | set(db_counts)
        | {
            (
                normalize_year(year),
                normalize_photographer(photographer)
            )
            for year, photographers in PIXIESET_TOTALS.items()
            for photographer in photographers
        }
    )

    rows = []

    for key in sorted(all_keys):

        year, photographer = key

        local_count = local_counts.get(
            key,
            0
        )

        db_count = db_counts.get(
            key,
            0
        )

        pixieset_count = get_pixieset_total(
            year,
            photographer
        )

        matched = matched_counts.get(
            key,
            0
        )

        uncertain = uncertain_counts.get(
            key,
            0
        )

        non_db = non_db_counts.get(
            key,
            0
        )

        if pixieset_count is None:

            db_vs_pixieset = ""

            local_vs_pixieset = ""

        else:

            db_vs_pixieset = (
                db_count - pixieset_count
            )

            local_vs_pixieset = (
                local_count - pixieset_count
            )

        status = pixieset_status(
            local_count,
            db_count,
            pixieset_count
        )

        rows.append({
            "Year": year,
            "Photographer": photographer,
            "Local Originals": local_count,
            "Media Database": db_count,
            "Pixieset": (
                pixieset_count
                if pixieset_count is not None
                else "UNKNOWN"
            ),
            "DB vs Pixieset": db_vs_pixieset,
            "Local vs Pixieset": local_vs_pixieset,
            "Matched": matched,
            "Uncertain / Protected": uncertain,
            "Definite Non-DB": non_db,
            "Three-Way Status": status,
        })

    return rows


# ============================================================================
# WRITE CSV
# ============================================================================

def write_csv(path, rows):

    if not rows:
        return

    # Preserve useful source columns first.
    preferred = [
        "Year",
        "Photographer",
        "Filename",
        "Full Path",
        "Extension",
        "File Size (bytes)",
        "Width",
        "Height",
        "Date Taken",
        "Camera Make",
        "Camera Model",
        "Lens Make",
        "Lens Model",
        "ISO",
        "Exposure Time",
        "F-Number",
        "Focal Length",
        "Focal Length 35mm",
        "Exposure Program",
        "Exposure Mode",
        "Metering Mode",
        "White Balance",
        "Flash",
        "Orientation",
        "Color Space",
        "Software",
        "GPS Latitude",
        "GPS Longitude",
        "GPS Altitude",
        "SHA-256 hash",
        "Reconciliation Status",
        "Match Type",
        "Match Reason",
        "Photographer Alias Applied",
        "DB Photographer",
        "DB Filename",
        "DB Date Taken",
        "DB File ID",
    ]

    all_fields = set()

    for row in rows:
        all_fields.update(row.keys())

    fields = []

    for field in preferred:

        if field in all_fields:
            fields.append(field)

    for field in sorted(all_fields):

        if field not in fields:
            fields.append(field)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )

        writer.writeheader()

        writer.writerows(rows)


# ============================================================================
# WRITE THREE-WAY SUMMARY CSV
# ============================================================================

def write_summary_csv(path, rows):

    fields = [
        "Year",
        "Photographer",
        "Local Originals",
        "Media Database",
        "Pixieset",
        "DB vs Pixieset",
        "Local vs Pixieset",
        "Matched",
        "Uncertain / Protected",
        "Definite Non-DB",
        "Three-Way Status",
    ]

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        writer.writerows(rows)


# ============================================================================
# WRITE TEXT SUMMARY
# ============================================================================

def write_text_summary(
    path,
    local_rows,
    db_rows,
    reconciliation_rows,
    db_not_found,
    counters,
    three_way_rows,
):

    total_local = len(local_rows)
    total_db = len(db_rows)

    matched = counters["MATCHED"]
    uncertain = counters["UNCERTAIN"]
    non_db = counters["DEFINITE_NON_DB"]

    exact_count = counters["EXACT_FILENAME"]
    date_count = counters["DATE_TAKEN"]
    fallback_count = counters["FILENAME_FALLBACK"]
    stem_count = counters["FILENAME_STEM"]
    no_exif_count = counters["NO_RELIABLE_EXIF"]
    ambiguous_date_count = counters["AMBIGUOUS_DATE"]
    ambiguous_stem_count = counters[
        "AMBIGUOUS_FILENAME_STEM"
    ]
    no_match_count = counters["NO_MATCH"]

    lines = []

    lines.append("=" * 78)
    lines.append(
        "ENOS MEDIA MANAGER - FULL DATABASE RECONCILIATION"
    )
    lines.append("=" * 78)
    lines.append("")
    lines.append(
        "READ-ONLY — NO FILES WERE MODIFIED OR DELETED"
    )
    lines.append("")

    lines.append("SOURCE FILES")
    lines.append("-" * 78)
    lines.append(f"Media Database:")
    lines.append(f"  {CSV_PATH}")
    lines.append("")
    lines.append("Original Image Index:")
    lines.append(f"  {INDEX_PATH}")
    lines.append("")

    lines.append("OVERALL TOTALS")
    lines.append("-" * 78)
    lines.append(
        f"Media Database records:       {total_db:,}"
    )

    unique_db_identities = len({
        make_identity_key(
            row["_year_col"],
            row["_photographer_col"],
            row["_filename_col"]
        )
        for row in db_rows
    })

    lines.append(
        f"Unique DB exact identities:   "
        f"{unique_db_identities:,}"
    )

    lines.append(
        f"Local indexed originals:      {total_local:,}"
    )

    lines.append(
        f"Matched:                      {matched:,}"
    )

    lines.append(
        f"Uncertain / protected:        {uncertain:,}"
    )

    lines.append(
        f"DEFINITE NON-DB:              {non_db:,}"
    )

    lines.append(
        f"DB records not found locally: {len(db_not_found):,}"
    )

    lines.append("")

    lines.append("MATCH TYPES")
    lines.append("-" * 78)

    lines.append(
        f"EXACT_FILENAME                 {exact_count:5,}"
    )

    lines.append(
        f"DATE_TAKEN                     {date_count:5,}"
    )

    lines.append(
        f"FILENAME_FALLBACK              {fallback_count:5,}"
    )

    lines.append(
        f"FILENAME_STEM                  {stem_count:5,}"
    )

    lines.append(
        f"NO_RELIABLE_EXIF               {no_exif_count:5,}"
    )

    lines.append(
        f"AMBIGUOUS_DATE                 {ambiguous_date_count:5,}"
    )

    lines.append(
        f"AMBIGUOUS_FILENAME_STEM        {ambiguous_stem_count:5,}"
    )

    lines.append(
        f"NO_MATCH                       {no_match_count:5,}"
    )

    lines.append("")

    lines.append(
        "THREE-WAY LOCAL / DATABASE / PIXIESET SUMMARY"
    )

    lines.append("-" * 78)

    header = (
        f"{'YEAR':<7}"
        f"{'PHOTOGRAPHER':<22}"
        f"{'LOCAL':>8}"
        f"{'DB':>7}"
        f"{'PIXIESET':>10}"
        f"{'DB-PIX':>8}"
        f"{'LOC-PIX':>8}"
        f"{'MATCHED':>9}"
        f"{'UNCERT':>9}"
        f"{'NON-DB':>9}"
    )

    lines.append(header)
    lines.append("-" * 78)

    for row in three_way_rows:

        pixieset = row["Pixieset"]

        if pixieset == "UNKNOWN":
            pixieset_text = "UNKNOWN"
            db_pix_text = ""
            local_pix_text = ""

        else:
            pixieset_text = f"{pixieset:,}"
            db_pix_text = f"{row['DB vs Pixieset']:+,}"
            local_pix_text = f"{row['Local vs Pixieset']:+,}"

        lines.append(
            f"{row['Year']:<7}"
            f"{row['Photographer']:<22}"
            f"{row['Local Originals']:>8,}"
            f"{row['Media Database']:>7,}"
            f"{pixieset_text:>10}"
            f"{db_pix_text:>8}"
            f"{local_pix_text:>8}"
            f"{row['Matched']:>9,}"
            f"{row['Uncertain / Protected']:>9,}"
            f"{row['Definite Non-DB']:>9,}"
        )

    lines.append("")
    lines.append("THREE-WAY STATUS")
    lines.append("-" * 78)

    status_counts = Counter(
        row["Three-Way Status"]
        for row in three_way_rows
    )

    for status, count in sorted(
        status_counts.items()
    ):
        lines.append(
            f"{status:<35} {count:>5}"
        )

    lines.append("")

    lines.append("PIXIESET INTERPRETATION")
    lines.append("-" * 78)
    lines.append(
        "Pixieset totals are reference counts only."
    )
    lines.append(
        "They are NOT used to classify individual files."
    )
    lines.append(
        "They are NOT used as deletion authority."
    )
    lines.append("")

    lines.append(
        "A DB count matching a Pixieset count does NOT prove "
        "that every local non-DB file can be deleted."
    )

    lines.append(
        "A local count differing from Pixieset does NOT prove "
        "that the additional local files are unwanted."
    )

    lines.append("")

    lines.append(
        "PHOTOGRAPHER NAME ALIASES"
    )
    lines.append("-" * 78)

    for source, target in sorted(
        PHOTOGRAPHER_ALIASES.items()
    ):
        lines.append(
            f"{source}  ->  {target}"
        )

    lines.append("")

    lines.append(
        "IMPORTANT 2025 B80 NOTE"
    )
    lines.append("-" * 78)
    lines.append(
        "Local 2025 b80:          158"
    )
    lines.append(
        "Media DB 2025 photos b80: 158"
    )
    lines.append(
        "Pixieset B80:             158"
    )
    lines.append("")
    lines.append(
        "These matching counts indicate a photographer-name "
        "difference rather than evidence that the 158 local "
        "B80 files are non-DB."
    )
    lines.append(
        "The alias is therefore handled before matching."
    )

    lines.append("")

    lines.append("DEFINITION OF DEFINITE NON-DB")
    lines.append("-" * 78)
    lines.append(
        "A local image is classified as DEFINITE_NON_DB only "
        "when the approved matching methods found no relationship "
        "to an unused Media Database record."
    )

    lines.append(
        "Pixieset totals do not override this classification."
    )

    lines.append("")
    lines.append(
        "The script does NOT delete these files."
    )

    lines.append(
        "They require review before any future deletion operation."
    )

    lines.append("")

    lines.append("SAFETY")
    lines.append("-" * 78)
    lines.append(
        "No image files were opened for writing."
    )
    lines.append(
        "No image files were moved."
    )
    lines.append(
        "No image files were renamed."
    )
    lines.append(
        "No image files were deleted."
    )
    lines.append(
        "No Media Database records were modified."
    )
    lines.append(
        "No original index records were modified."
    )

    path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    preflight()

    print("Loading Media Database...")
    db_rows, db_columns = load_media_database()

    print(
        f"  Loaded {len(db_rows):,} Media Database records."
    )

    print()

    print("Loading Original Image Index...")
    local_rows, local_columns = load_original_index()

    print(
        f"  Loaded {len(local_rows):,} local originals."
    )

    print()

    print("Building Media Database indexes...")

    db_indexes = build_database_indexes(
        db_rows
    )

    print(
        "  Database indexes built."
    )

    print()

    print("Reconciling local originals...")

    (
        reconciliation_rows,
        used_db_indices,
        counters,
        group_summary,
    ) = reconcile(
        local_rows,
        db_rows,
        db_indexes
    )

    print(
        f"  Reconciled {len(reconciliation_rows):,} "
        "local originals."
    )

    print()

    print(
        "Building Media Database 'not found locally' report..."
    )

    db_not_found = build_db_not_found(
        db_rows,
        used_db_indices
    )

    print(
        f"  {len(db_not_found):,} DB records not found locally."
    )

    print()

    print(
        "Building three-way Local / DB / Pixieset summary..."
    )

    three_way_rows = build_three_way_summary(
        local_rows,
        db_rows,
        reconciliation_rows
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    full_report_path = (
        REPORT_DIR
        / f"full_reconciliation_{timestamp}.csv"
    )

    candidates_report_path = (
        REPORT_DIR
        / f"full_reconciliation_candidates_{timestamp}.csv"
    )

    db_not_found_path = (
        REPORT_DIR
        / f"full_reconciliation_db_not_found_{timestamp}.csv"
    )

    summary_csv_path = (
        REPORT_DIR
        / f"full_reconciliation_three_way_summary_{timestamp}.csv"
    )

    summary_txt_path = (
        REPORT_DIR
        / f"full_reconciliation_summary_{timestamp}.txt"
    )

    # ------------------------------------------------------------------------
    # FULL REPORT
    # ------------------------------------------------------------------------

    write_csv(
        full_report_path,
        reconciliation_rows
    )

    # ------------------------------------------------------------------------
    # CANDIDATES / UNCERTAIN REPORT
    #
    # This intentionally includes UNCERTAIN and DEFINITE_NON_DB.
    # Nothing is considered safe to delete merely because it appears here.
    # ------------------------------------------------------------------------

    candidates_rows = [
        row
        for row in reconciliation_rows
        if row["Reconciliation Status"]
        in {
            "UNCERTAIN",
            "DEFINITE_NON_DB",
        }
    ]

    write_csv(
        candidates_report_path,
        candidates_rows
    )

    # ------------------------------------------------------------------------
    # DB NOT FOUND LOCALLY
    # ------------------------------------------------------------------------

    write_csv(
        db_not_found_path,
        db_not_found
    )

    # ------------------------------------------------------------------------
    # THREE-WAY SUMMARY
    # ------------------------------------------------------------------------

    write_summary_csv(
        summary_csv_path,
        three_way_rows
    )

    write_text_summary(
        summary_txt_path,
        local_rows,
        db_rows,
        reconciliation_rows,
        db_not_found,
        counters,
        three_way_rows,
    )

    # =========================================================================
    # CONSOLE OUTPUT
    # =========================================================================

    print()
    print("=" * 78)
    print(
        "RECONCILIATION COMPLETE"
    )
    print("=" * 78)
    print()

    print("OVERALL TOTALS")
    print("-" * 78)

    print(
        f"Media Database records:       {len(db_rows):,}"
    )

    unique_db_identities = len({
        make_identity_key(
            row["_year_col"],
            row["_photographer_col"],
            row["_filename_col"]
        )
        for row in db_rows
    })

    print(
        f"Unique DB exact identities:   "
        f"{unique_db_identities:,}"
    )

    print(
        f"Local indexed originals:      {len(local_rows):,}"
    )

    print(
        f"Matched:                      "
        f"{counters['MATCHED']:,}"
    )

    print(
        f"Uncertain / protected:        "
        f"{counters['UNCERTAIN']:,}"
    )

    print(
        f"DEFINITE NON-DB:              "
        f"{counters['DEFINITE_NON_DB']:,}"
    )

    print(
        f"DB records not found locally: "
        f"{len(db_not_found):,}"
    )

    print()

    print("MATCH TYPES")
    print("-" * 78)

    for key in [
        "EXACT_FILENAME",
        "DATE_TAKEN",
        "FILENAME_FALLBACK",
        "FILENAME_STEM",
        "NO_RELIABLE_EXIF",
        "AMBIGUOUS_DATE",
        "AMBIGUOUS_FILENAME_STEM",
        "NO_MATCH",
    ]:

        print(
            f"{key:<32} "
            f"{counters[key]:>7,}"
        )

    print()

    print("THREE-WAY SUMMARY")
    print("-" * 78)

    print(
        f"{'YEAR':<7}"
        f"{'PHOTOGRAPHER':<22}"
        f"{'LOCAL':>8}"
        f"{'DB':>7}"
        f"{'PIXIESET':>10}"
        f"{'STATUS'}"
    )

    print("-" * 78)

    for row in three_way_rows:

        print(
            f"{row['Year']:<7}"
            f"{row['Photographer']:<22}"
            f"{row['Local Originals']:>8,}"
            f"{row['Media Database']:>7,}"
            f"{str(row['Pixieset']):>10}"
            f"  {row['Three-Way Status']}"
        )

    print()

    print("REPORT FILES")
    print("-" * 78)

    print(
        f"Full reconciliation:"
    )
    print(
        f"  {full_report_path}"
    )

    print()

    print(
        f"Uncertain + non-DB review report:"
    )
    print(
        f"  {candidates_report_path}"
    )

    print()

    print(
        f"DB records not found locally:"
    )
    print(
        f"  {db_not_found_path}"
    )

    print()

    print(
        f"Three-way Local / DB / Pixieset summary:"
    )
    print(
        f"  {summary_csv_path}"
    )

    print()

    print(
        f"Full text summary:"
    )
    print(
        f"  {summary_txt_path}"
    )

    print()
    print("=" * 78)
    print(
        "SAFETY: NOTHING WAS DELETED."
    )
    print(
        "Pixieset totals were used as reference counts only."
    )
    print("=" * 78)


if __name__ == "__main__":
    main()
