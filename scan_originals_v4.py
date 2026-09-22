
"""
Enos Media Manager - Original Image Folder Scanner (v4)
----------------------------------------------------------

v4 changes from v3:
    - Expanded EXIF metadata in the CSV.
    - Uses exifread for EXIF extraction, including HEIC EXIF.
    - Uses Pillow + pillow-heif for actual image dimensions.
    - Adds detailed HEIC/dimension diagnostics.
    - Adds GPS information where available.
    - Keeps DateTimeOriginal as the trusted "Date Taken" field.
    - Keeps generic DateTime as an untrusted reference field.
    - Records EXIF and dimension errors instead of silently hiding them.

SOURCE FILES ARE READ-ONLY.

This script does NOT:
    - move files
    - rename files
    - delete files
    - modify files
    - resize files
    - compress files
    - rewrite metadata

Expected folder structure:

    C:\\Enos Desktop Manager\\
        2025\\
            Photographer Name\\
                image files...
        2026\\
            Photographer Name\\
                image files...

Creates:

    original_image_index.csv

Core fields:
    Year
    Photographer
    Filename
    Full Path
    Extension
    File Size (bytes)
    Width
    Height

EXIF fields:
    Date Taken
    Camera Make
    Camera Model
    Lens Make
    Lens Model
    ISO
    Exposure Time
    F-Number
    Focal Length
    Focal Length 35mm
    Exposure Program
    Exposure Mode
    Metering Mode
    White Balance
    Flash
    Orientation
    Color Space
    Software
    GPS Latitude
    GPS Longitude
    GPS Altitude
    GPS Direction
    GPS Date
    Fallback DateTime (untrusted)

Diagnostics:
    EXIF Status
    Dimension Status
    EXIF Error
    Dimension Error

Identity:
    Hash

Date Taken:
    ONLY DateTimeOriginal (EXIF tag 36867) is trusted as the
    actual capture date.

Generic DateTime:
    EXIF tag 306 is recorded separately as:
        Fallback DateTime (untrusted)

It is NEVER used as the trusted capture date.

EXIF extraction:
    exifread

Image dimensions:
    Pillow
    pillow-heif for HEIC/HEIF

Required packages:

    py -m pip install Pillow pillow-heif exifread
"""

import sys
import csv
import hashlib
from pathlib import Path

# ------------------------------------------------------------------
# Pillow
# ------------------------------------------------------------------

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ------------------------------------------------------------------
# HEIC / HEIF support
# ------------------------------------------------------------------

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False

# ------------------------------------------------------------------
# EXIFRead
# ------------------------------------------------------------------

try:
    import exifread
    HAS_EXIFREAD = True
except ImportError:
    HAS_EXIFREAD = False


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

ROOT_FOLDER = r"C:\Enos Desktop Manager"
OUTPUT_CSV = "original_image_index.csv"

SOURCE_YEARS = {"2025", "2026"}

VALID_EXTENSIONS = {
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
}

HASH_ALGORITHM = "sha256"


# ------------------------------------------------------------------
# EXIF tag names
# ------------------------------------------------------------------

DATETIME_ORIGINAL_TAG = "EXIF DateTimeOriginal"
DATETIME_TAG = "Image DateTime"

TAG_MAP = {
    "Camera Make": "Image Make",
    "Camera Model": "Image Model",
    "Lens Make": "EXIF LensMake",
    "Lens Model": "EXIF LensModel",
    "ISO": "EXIF ISOSpeedRatings",
    "Exposure Time": "EXIF ExposureTime",
    "F-Number": "EXIF FNumber",
    "Focal Length": "EXIF FocalLength",
    "Focal Length 35mm": "EXIF FocalLengthIn35mmFilm",
    "Exposure Program": "EXIF ExposureProgram",
    "Exposure Mode": "EXIF ExposureMode",
    "Metering Mode": "EXIF MeteringMode",
    "White Balance": "EXIF WhiteBalance",
    "Flash": "EXIF Flash",
    "Orientation": "Image Orientation",
    "Color Space": "EXIF ColorSpace",
    "Software": "Image Software",
    "GPS Latitude": "GPS GPSLatitude",
    "GPS Longitude": "GPS GPSLongitude",
    "GPS Altitude": "GPS GPSAltitude",
    "GPS Direction": "GPS GPSImgDirection",
    "GPS Date": "GPS GPSDate",
}


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def safe_text(value):
    """
    Convert an EXIFRead value to a clean string.

    EXIFRead can return Ratio, IfdTag, list, or other objects.
    str(value) gives us a useful human-readable representation.
    """
    if value is None:
        return ""

    try:
        return str(value)
    except Exception:
        return ""


def format_ratio(value):
    """
    Convert an EXIFRead Ratio or similar value into a useful number.

    Examples:
        89/50 -> 1.78
        1/310 -> 1/310

    For exposure time we generally keep the fraction.
    For aperture/focal length we prefer a decimal.
    """
    try:
        if hasattr(value, "num") and hasattr(value, "den"):
            if value.den == 0:
                return str(value)

            result = value.num / value.den

            if result == int(result):
                return str(int(result))

            return f"{result:.4f}".rstrip("0").rstrip(".")

    except Exception:
        pass

    return safe_text(value)


def format_numeric_exif(value, decimals=2):
    """
    Convert an EXIF ratio into a clean decimal string.
    """
    try:
        if hasattr(value, "num") and hasattr(value, "den"):
            if value.den == 0:
                return safe_text(value)

            result = value.num / value.den

            return f"{result:.{decimals}f}".rstrip("0").rstrip(".")

    except Exception:
        pass

    return safe_text(value)


def format_exposure_time(value):
    """
    Keep shutter speed in a photographer-friendly format.

    Example:
        1/310 remains 1/310
    """
    return safe_text(value)


def format_fnumber(value):
    """
    Convert FNumber ratio to a decimal.

    Example:
        89/50 -> 1.78
    """
    return format_numeric_exif(value, 2)


def format_focal_length(value):
    """
    Convert focal length to mm.

    Example:
        343/50 -> 6.86 mm
    """
    formatted = format_numeric_exif(value, 2)

    if formatted:
        return f"{formatted} mm"

    return ""


def format_focal_length_35mm(value):
    """
    Convert 35mm focal length to a simple mm value.
    """
    raw = safe_text(value)

    if not raw:
        return ""

    try:
        if hasattr(value, "num") and hasattr(value, "den"):
            if value.den != 0:
                result = value.num / value.den

                if result == int(result):
                    return f"{int(result)} mm"

                return f"{result:.1f} mm"

    except Exception:
        pass

    return f"{raw} mm"


def format_iso(value):
    """
    Clean ISO value.
    """
    raw = safe_text(value)

    if not raw:
        return ""

    try:
        if hasattr(value, "values"):
            values = value.values

            if values:
                return str(values[0])

    except Exception:
        pass

    return raw


def dms_to_decimal(degrees, minutes, seconds, reference):
    """
    Convert EXIF GPS degrees/minutes/seconds into decimal degrees.
    """
    try:
        def ratio_to_float(value):
            if hasattr(value, "num") and hasattr(value, "den"):
                if value.den == 0:
                    return 0.0

                return value.num / value.den

            return float(value)

        d = ratio_to_float(degrees)
        m = ratio_to_float(minutes)
        s = ratio_to_float(seconds)

        decimal = d + (m / 60.0) + (s / 3600.0)

        if reference.upper() in ("S", "W"):
            decimal *= -1

        return f"{decimal:.6f}"

    except Exception:
        return ""


def get_gps_coordinate(tags, coordinate_tag, reference_tag):
    """
    Convert EXIF GPS coordinate data into decimal degrees.
    """
    try:
        coordinate = tags.get(coordinate_tag)
        reference = tags.get(reference_tag)

        if not coordinate or not reference:
            return ""

        values = coordinate.values

        if len(values) < 3:
            return ""

        ref = str(reference)

        return dms_to_decimal(
            values[0],
            values[1],
            values[2],
            ref,
        )

    except Exception:
        return ""


def get_gps_altitude(tags):
    """
    Convert GPS altitude into metres.
    """
    try:
        altitude = tags.get("GPS GPSAltitude")

        if not altitude:
            return ""

        value = altitude.values[0]

        if hasattr(value, "num") and hasattr(value, "den"):
            if value.den == 0:
                return ""

            metres = value.num / value.den
        else:
            metres = float(value)

        altitude_ref = tags.get("GPS GPSAltitudeRef")

        if altitude_ref:
            ref = str(altitude_ref)

            if ref == "1":
                metres *= -1

        return f"{metres:.2f} m"

    except Exception:
        return ""


def get_exif_value(tags, tag_name):
    """
    Get a clean EXIF value from an EXIFRead tag dictionary.
    """
    try:
        value = tags.get(tag_name)

        if value is None:
            return ""

        return safe_text(value)

    except Exception:
        return ""


# ------------------------------------------------------------------
# EXIF extraction
# ------------------------------------------------------------------

def read_exif(path):
    """
    Read useful EXIF metadata using exifread.

    Returns a dictionary containing the fields used by the CSV.

    EXIFRead is deliberately used independently from Pillow because
    the two libraries have different strengths:
        - Pillow/pillow-heif -> image decoding and dimensions
        - exifread -> detailed EXIF metadata
    """

    result = {
        "Date Taken": "",
        "Camera Make": "",
        "Camera Model": "",
        "Lens Make": "",
        "Lens Model": "",
        "ISO": "",
        "Exposure Time": "",
        "F-Number": "",
        "Focal Length": "",
        "Focal Length 35mm": "",
        "Exposure Program": "",
        "Exposure Mode": "",
        "Metering Mode": "",
        "White Balance": "",
        "Flash": "",
        "Orientation": "",
        "Color Space": "",
        "Software": "",
        "GPS Latitude": "",
        "GPS Longitude": "",
        "GPS Altitude": "",
        "GPS Direction": "",
        "GPS Date": "",
        "Fallback DateTime (untrusted)": "",
        "EXIF Error": "",
    }

    if not HAS_EXIFREAD:
        result["EXIF Error"] = "exifread is not installed"
        return result

    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(
                f,
                details=False,
            )

        # ----------------------------------------------------------
        # Trusted capture date
        # ----------------------------------------------------------

        date_taken = tags.get(DATETIME_ORIGINAL_TAG)

        if date_taken:
            result["Date Taken"] = safe_text(date_taken)

        # ----------------------------------------------------------
        # Untrusted generic DateTime
        # ----------------------------------------------------------

        fallback_datetime = tags.get(DATETIME_TAG)

        if fallback_datetime:
            result["Fallback DateTime (untrusted)"] = safe_text(
                fallback_datetime
            )

        # ----------------------------------------------------------
        # Camera
        # ----------------------------------------------------------

        result["Camera Make"] = get_exif_value(
            tags,
            "Image Make",
        )

        result["Camera Model"] = get_exif_value(
            tags,
            "Image Model",
        )

        # ----------------------------------------------------------
        # Lens
        # ----------------------------------------------------------

        result["Lens Make"] = get_exif_value(
            tags,
            "EXIF LensMake",
        )

        result["Lens Model"] = get_exif_value(
            tags,
            "EXIF LensModel",
        )

        # ----------------------------------------------------------
        # Exposure
        # ----------------------------------------------------------

        iso = tags.get("EXIF ISOSpeedRatings")

        if iso:
            result["ISO"] = format_iso(iso)

        exposure = tags.get("EXIF ExposureTime")

        if exposure:
            result["Exposure Time"] = format_exposure_time(exposure)

        fnumber = tags.get("EXIF FNumber")

        if fnumber:
            result["F-Number"] = format_fnumber(fnumber)

        focal = tags.get("EXIF FocalLength")

        if focal:
            result["Focal Length"] = format_focal_length(focal)

        focal_35 = tags.get("EXIF FocalLengthIn35mmFilm")

        if focal_35:
            result["Focal Length 35mm"] = format_focal_length_35mm(
                focal_35
            )

        # ----------------------------------------------------------
        # Camera settings
        # ----------------------------------------------------------

        result["Exposure Program"] = get_exif_value(
            tags,
            "EXIF ExposureProgram",
        )

        result["Exposure Mode"] = get_exif_value(
            tags,
            "EXIF ExposureMode",
        )

        result["Metering Mode"] = get_exif_value(
            tags,
            "EXIF MeteringMode",
        )

        result["White Balance"] = get_exif_value(
            tags,
            "EXIF WhiteBalance",
        )

        result["Flash"] = get_exif_value(
            tags,
            "EXIF Flash",
        )

        result["Orientation"] = get_exif_value(
            tags,
            "Image Orientation",
        )

        result["Color Space"] = get_exif_value(
            tags,
            "EXIF ColorSpace",
        )

        result["Software"] = get_exif_value(
            tags,
            "Image Software",
        )

        # ----------------------------------------------------------
        # GPS
        # ----------------------------------------------------------

        result["GPS Latitude"] = get_gps_coordinate(
            tags,
            "GPS GPSLatitude",
            "GPS GPSLatitudeRef",
        )

        result["GPS Longitude"] = get_gps_coordinate(
            tags,
            "GPS GPSLongitude",
            "GPS GPSLongitudeRef",
        )

        result["GPS Altitude"] = get_gps_altitude(tags)

        gps_direction = tags.get("GPS GPSImgDirection")

        if gps_direction:
            result["GPS Direction"] = format_numeric_exif(
                gps_direction,
                2,
            )

        gps_date = tags.get("GPS GPSDate")

        if gps_date:
            result["GPS Date"] = safe_text(gps_date)

        return result

    except Exception as error:
        result["EXIF Error"] = (
            f"{type(error).__name__}: {error}"
        )

        return result


# ------------------------------------------------------------------
# Image dimensions
# ------------------------------------------------------------------

def get_dimensions(path):
    """
    Read actual decoded image dimensions using Pillow.

    HEIC/HEIF files use pillow-heif through the registered opener.

    Returns:

        width
        height
        dimension_status
        dimension_error
    """

    if not HAS_PIL:
        return (
            None,
            None,
            "PILLOW_NOT_INSTALLED",
            "Pillow is not installed",
        )

    extension = path.suffix.lower()

    if extension in {".heic", ".heif"} and not HAS_HEIF:
        return (
            None,
            None,
            "HEIC_PLUGIN_MISSING",
            "pillow-heif is not installed",
        )

    try:
        with Image.open(path) as img:
            width, height = img.size

            if width and height:
                return (
                    width,
                    height,
                    "OK",
                    "",
                )

            return (
                None,
                None,
                "NO_DIMENSIONS",
                "Image opened but returned no dimensions",
            )

    except Exception as error:
        return (
            None,
            None,
            "DECODE_FAILED",
            f"{type(error).__name__}: {error}",
        )


# ------------------------------------------------------------------
# Combined image information
# ------------------------------------------------------------------

def get_image_info(path):
    """
    Read dimensions and EXIF separately.

    This is deliberate:
        - a file may have readable EXIF but fail image decoding
        - a file may decode correctly but have no EXIF
        - a file may have dimensions but no DateTimeOriginal

    Returns a dictionary containing all image information.
    """

    dimensions = get_dimensions(path)
    exif = read_exif(path)

    width, height, dimension_status, dimension_error = dimensions

    date_taken = exif["Date Taken"]

    if dimension_status == "OK" and date_taken:
        exif_status = "OK"
    elif dimension_status == "OK":
        exif_status = "NO_EXIF"
    elif date_taken:
        exif_status = "EXIF_ONLY"
    else:
        exif_status = "UNREADABLE"

    return {
        "Width": width,
        "Height": height,
        "Date Taken": date_taken,
        "Fallback DateTime (untrusted)": exif[
            "Fallback DateTime (untrusted)"
        ],
        "Camera Make": exif["Camera Make"],
        "Camera Model": exif["Camera Model"],
        "Lens Make": exif["Lens Make"],
        "Lens Model": exif["Lens Model"],
        "ISO": exif["ISO"],
        "Exposure Time": exif["Exposure Time"],
        "F-Number": exif["F-Number"],
        "Focal Length": exif["Focal Length"],
        "Focal Length 35mm": exif["Focal Length 35mm"],
        "Exposure Program": exif["Exposure Program"],
        "Exposure Mode": exif["Exposure Mode"],
        "Metering Mode": exif["Metering Mode"],
        "White Balance": exif["White Balance"],
        "Flash": exif["Flash"],
        "Orientation": exif["Orientation"],
        "Color Space": exif["Color Space"],
        "Software": exif["Software"],
        "GPS Latitude": exif["GPS Latitude"],
        "GPS Longitude": exif["GPS Longitude"],
        "GPS Altitude": exif["GPS Altitude"],
        "GPS Direction": exif["GPS Direction"],
        "GPS Date": exif["GPS Date"],
        "EXIF Status": exif_status,
        "Dimension Status": dimension_status,
        "EXIF Error": exif["EXIF Error"],
        "Dimension Error": dimension_error,
    }


# ------------------------------------------------------------------
# Hashing
# ------------------------------------------------------------------

def compute_hash(
    path,
    algorithm=HASH_ALGORITHM,
    chunk_size=1024 * 1024,
):
    """
    Compute a SHA-256 hash without modifying the source file.
    """

    if not algorithm:
        return ""

    hasher = hashlib.new(algorithm)

    try:
        with open(path, "rb") as f:
            for chunk in iter(
                lambda: f.read(chunk_size),
                b"",
            ):
                hasher.update(chunk)

        return hasher.hexdigest()

    except Exception as error:
        print(
            f"WARNING: Could not hash {path}\n"
            f"         {error}"
        )

        return ""


# ------------------------------------------------------------------
# Scanner
# ------------------------------------------------------------------

def scan_originals(root_folder):

    root = Path(root_folder)

    if not root.exists() or not root.is_dir():
        print(
            f"\nERROR: Root folder not found or not a folder:\n"
            f"{root}"
        )
        sys.exit(1)

    records = []

    skipped_files = 0
    scanned_files = 0

    status_counts = {
        "OK": 0,
        "NO_EXIF": 0,
        "EXIF_ONLY": 0,
        "UNREADABLE": 0,
    }

    dimension_counts = {}

    heic_total = 0
    heic_missing_dimensions = 0

    missing_years = []

    print()
    print("=" * 70)
    print("ENOS MEDIA MANAGER - ORIGINAL IMAGE SCANNER (v4)")
    print("=" * 70)
    print()

    print(
        f"Pillow support: "
        f"{'ENABLED' if HAS_PIL else 'NOT INSTALLED'}"
    )

    print(
        f"HEIC support: "
        f"{'ENABLED' if HAS_HEIF else 'NOT INSTALLED'}"
    )

    print(
        f"EXIFRead support: "
        f"{'ENABLED' if HAS_EXIFREAD else 'NOT INSTALLED'}"
    )

    print()
    print(f"Source folder:\n  {root}")
    print()

    for year in sorted(SOURCE_YEARS):

        year_folder = root / year

        if not year_folder.exists():

            print(
                f"WARNING: Year folder not found: "
                f"{year_folder}"
            )

            missing_years.append(year)

            continue

        print(f"Scanning {year}...")

        photographer_folders = sorted(
            p
            for p in year_folder.iterdir()
            if p.is_dir()
        )

        print(
            f"  Found "
            f"{len(photographer_folders)} "
            f"photographer folders."
        )

        for photographer_folder in photographer_folders:

            photographer = photographer_folder.name

            print(
                f"    {photographer}"
            )

            for file_path in photographer_folder.rglob("*"):

                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()

                if ext not in VALID_EXTENSIONS:
                    skipped_files += 1
                    continue

                scanned_files += 1

                if ext in {".heic", ".heif"}:
                    heic_total += 1

                info = get_image_info(file_path)

                exif_status = info["EXIF Status"]
                dimension_status = info[
                    "Dimension Status"
                ]

                status_counts[exif_status] = (
                    status_counts.get(
                        exif_status,
                        0,
                    )
                    + 1
                )

                dimension_counts[dimension_status] = (
                    dimension_counts.get(
                        dimension_status,
                        0,
                    )
                    + 1
                )

                if (
                    ext in {".heic", ".heif"}
                    and (
                        info["Width"] is None
                        or info["Height"] is None
                    )
                ):
                    heic_missing_dimensions += 1

                    print(
                        "      HEIC DIMENSION WARNING:"
                    )
                    print(
                        f"        {file_path.name}"
                    )
                    print(
                        f"        Status: "
                        f"{dimension_status}"
                    )

                    if info["Dimension Error"]:
                        print(
                            f"        Error: "
                            f"{info['Dimension Error']}"
                        )

                try:
                    file_size = file_path.stat().st_size

                except Exception as error:

                    print(
                        "WARNING: Could not read "
                        "file size:"
                    )

                    print(
                        f"         {file_path}"
                    )

                    print(
                        f"         {error}"
                    )

                    file_size = ""

                file_hash = compute_hash(
                    file_path
                )

                records.append(
                    {
                        "Year": year,
                        "Photographer": photographer,
                        "Filename": file_path.name,
                        "Full Path": str(file_path),
                        "Extension": ext,
                        "File Size (bytes)": file_size,

                        "Width": (
                            info["Width"]
                            if info["Width"] is not None
                            else ""
                        ),

                        "Height": (
                            info["Height"]
                            if info["Height"] is not None
                            else ""
                        ),

                        "Date Taken": info[
                            "Date Taken"
                        ],

                        "Camera Make": info[
                            "Camera Make"
                        ],

                        "Camera Model": info[
                            "Camera Model"
                        ],

                        "Lens Make": info[
                            "Lens Make"
                        ],

                        "Lens Model": info[
                            "Lens Model"
                        ],

                        "ISO": info["ISO"],

                        "Exposure Time": info[
                            "Exposure Time"
                        ],

                        "F-Number": info[
                            "F-Number"
                        ],

                        "Focal Length": info[
                            "Focal Length"
                        ],

                        "Focal Length 35mm": info[
                            "Focal Length 35mm"
                        ],

                        "Exposure Program": info[
                            "Exposure Program"
                        ],

                        "Exposure Mode": info[
                            "Exposure Mode"
                        ],

                        "Metering Mode": info[
                            "Metering Mode"
                        ],

                        "White Balance": info[
                            "White Balance"
                        ],

                        "Flash": info["Flash"],

                        "Orientation": info[
                            "Orientation"
                        ],

                        "Color Space": info[
                            "Color Space"
                        ],

                        "Software": info[
                            "Software"
                        ],

                        "GPS Latitude": info[
                            "GPS Latitude"
                        ],

                        "GPS Longitude": info[
                            "GPS Longitude"
                        ],

                        "GPS Altitude": info[
                            "GPS Altitude"
                        ],

                        "GPS Direction": info[
                            "GPS Direction"
                        ],

                        "GPS Date": info[
                            "GPS Date"
                        ],

                        "Fallback DateTime (untrusted)": info[
                            "Fallback DateTime (untrusted)"
                        ],

                        "EXIF Status": info[
                            "EXIF Status"
                        ],

                        "Dimension Status": info[
                            "Dimension Status"
                        ],

                        "EXIF Error": info[
                            "EXIF Error"
                        ],

                        "Dimension Error": info[
                            "Dimension Error"
                        ],

                        "Hash": file_hash,
                    }
                )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("SCAN COMPLETE")
    print("=" * 70)
    print()

    print(
        f"Images indexed:          {len(records)}"
    )

    print(
        f"Files skipped:           {skipped_files}"
    )

    print()

    print("EXIF status:")

    for status, count in sorted(
        status_counts.items()
    ):
        print(
            f"  {status:<18} {count}"
        )

    print()

    print("Dimension status:")

    for status, count in sorted(
        dimension_counts.items()
    ):
        print(
            f"  {status:<24} {count}"
        )

    print()

    print(
        f"HEIC/HEIF files:          "
        f"{heic_total}"
    )

    print(
        f"HEIC/HEIF missing dims:   "
        f"{heic_missing_dimensions}"
    )

    if missing_years:

        print()
        print("Missing year folders:")

        for year in missing_years:
            print(
                f"  {year}"
            )

    print()

    return records


# ------------------------------------------------------------------
# CSV writer
# ------------------------------------------------------------------

def write_csv(records, output_path):

    if not records:

        print(
            "No records to write."
        )

        return

    fieldnames = [
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
        "GPS Direction",
        "GPS Date",

        "Fallback DateTime (untrusted)",

        "EXIF Status",
        "Dimension Status",
        "EXIF Error",
        "Dimension Error",

        "Hash",
    ]

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(records)

    print(
        f"Index CSV created:\n"
        f"  {output_path}"
    )


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = ROOT_FOLDER

    # --------------------------------------------------------------
    # Dependency check
    # --------------------------------------------------------------

    missing_packages = []

    if not HAS_PIL:
        missing_packages.append(
            "Pillow"
        )

    if not HAS_HEIF:
        missing_packages.append(
            "pillow-heif"
        )

    if not HAS_EXIFREAD:
        missing_packages.append(
            "exifread"
        )

    if missing_packages:

        print()
        print("=" * 70)
        print("WARNING: MISSING PYTHON PACKAGES")
        print("=" * 70)
        print()

        print(
            "Missing:"
        )

        for package in missing_packages:
            print(
                f"  - {package}"
            )

        print()
        print(
            "Install them with:"
        )

        print()
        print(
            "  py -m pip install "
            "Pillow pillow-heif exifread"
        )

        print()

        if not HAS_PIL or not HAS_HEIF:

            print(
                "The scanner cannot reliably "
                "process HEIC dimensions without "
                "Pillow + pillow-heif."
            )

            sys.exit(1)

    # --------------------------------------------------------------
    # Scan
    # --------------------------------------------------------------

    records = scan_originals(
        root
    )

    # --------------------------------------------------------------
    # Write CSV
    # --------------------------------------------------------------

    output_path = (
        Path(__file__).parent
        / OUTPUT_CSV
    )

    write_csv(
        records,
        output_path,
    )

    # --------------------------------------------------------------
    # Final message
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print()

    print(
        "The original files were NOT modified."
    )

    print()

    print(
        f"Index saved to:\n"
        f"  {output_path}"
    )

    print()

    print(
        "The CSV now contains expanded EXIF "
        "metadata and detailed dimension diagnostics."
    )

    print()

