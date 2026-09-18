"""
Enos Media Manager - Deferred Work Folder Setup
--------------------------------------------------
Creates a "Deferred" folder to hold reference material for the two
photographer folders that are not yet downloaded to this PC:

    2025 Pacome        (196 expected images, per Media Database)
    2025 Photos B80     (158 expected images, per Media Database - mostly
                          Canon 700D RAW/.CR2 files)

This does NOT touch C:\\Enos Desktop Manager\\2025 or \\2026 - it only
creates a separate reference area under:

    C:\\Enos Desktop Manager\\Deferred\\

Re-run this any time to refresh the reference files (it overwrites
its own output, never anything in the year/photographer folders).
"""

from pathlib import Path

DEFERRED_ROOT = Path(r"C:\Enos Desktop Manager\Deferred")

PACOME_2025_FILENAMES = ['PXL_20250425_093624604.jpg', 'PXL_20250425_095911226.jpg', 'PXL_20250425_154354576.jpg', 'PXL_20250425_154426567.PORTRAIT.jpg', 'PXL_20250425_205754503.jpg', 'PXL_20250426_135530917.jpg', 'PXL_20250426_140734456.PORTRAIT.jpg', 'PXL_20250426_141157706.jpg', 'PXL_20250426_151217759.jpg', 'PXL_20250426_151451318.PORTRAIT.jpg', 'PXL_20250426_151508392.jpg', 'PXL_20250426_151548794.jpg', 'PXL_20250426_151602758.jpg', 'PXL_20250426_151736629.PORTRAIT.jpg', 'PXL_20250426_155654348.PORTRAIT.ORIGINAL.jpg', 'PXL_20250426_155716482.PORTRAIT.jpg', 'PXL_20250426_155717879.PORTRAIT.jpg', 'PXL_20250426_155723475.jpg', 'PXL_20250426_162449132.jpg', 'PXL_20250426_225425173.jpg', 'PXL_20250426_225446892.jpg', 'PXL_20250426_231356214.jpg', 'PXL_20250426_232544465.jpg', 'PXL_20250426_233128354.jpg', 'PXL_20250427_011831651.PORTRAIT.jpg', 'PXL_20250427_011951320.PORTRAIT.jpg', 'PXL_20250427_012004296.PORTRAIT.jpg', 'PXL_20250427_012057339.PORTRAIT.jpg', 'PXL_20250427_150932848.jpg', 'PXL_20250427_151717481.PORTRAIT.jpg', 'PXL_20250427_163032931.jpg', 'PXL_20250427_174208349.jpg', 'PXL_20250427_175218828.NIGHT.jpg', 'PXL_20250427_175247498.NIGHT.jpg', 'PXL_20250427_182824244.jpg', 'PXL_20250427_193019506.jpg', 'PXL_20250427_194411754.jpg', 'PXL_20250427_234900389.jpg', 'PXL_20250428_103621910.jpg', 'PXL_20250428_110921280.jpg', 'PXL_20250428_113759902.jpg', 'PXL_20250428_125249030.PORTRAIT.jpg', 'PXL_20250428_125255591.PORTRAIT.ORIGINAL.jpg', 'PXL_20250428_125333239.jpg', 'PXL_20250428_125426442.jpg', 'PXL_20250428_153707190.jpg', 'PXL_20250428_153723500.jpg', 'PXL_20250428_160919827.jpg', 'PXL_20250428_183851768.jpg', 'PXL_20250428_183909933.jpg', 'PXL_20250428_193440415.NIGHT.jpg', 'PXL_20250428_200829826.PORTRAIT.jpg', 'PXL_20250428_203357580.jpg', 'PXL_20250428_203404469.jpg', 'PXL_20250428_204347259.jpg', 'PXL_20250428_204350604.jpg', 'PXL_20250428_212041086.jpg', 'PXL_20250428_235216630.PORTRAIT.jpg', 'PXL_20250428_235317273.jpg', 'PXL_20250428_235342605.jpg', 'PXL_20250429_000104058.NIGHT.jpg', 'PXL_20250429_001737517.jpg', 'PXL_20250429_024935947.PORTRAIT.jpg', 'PXL_20250429_031318548.PORTRAIT.jpg', 'PXL_20250429_043714700.jpg', 'PXL_20250429_043730522.jpg', 'PXL_20250429_044224985.jpg', 'PXL_20250429_111446397.jpg', 'PXL_20250429_111451360.jpg', 'PXL_20250429_132736934.jpg', 'PXL_20250429_140816578.jpg', 'PXL_20250429_152040583.jpg', 'PXL_20250429_152400985.jpg', 'PXL_20250429_152442742.PORTRAIT.jpg', 'PXL_20250429_152443641.PORTRAIT.jpg', 'PXL_20250429_155420845.PORTRAIT.jpg', 'PXL_20250429_155429138.jpg', 'PXL_20250429_160157707.PORTRAIT.jpg', 'PXL_20250429_160201145.PORTRAIT.jpg', 'PXL_20250429_160209489.PORTRAIT.jpg', 'PXL_20250429_161554156.jpg', 'PXL_20250429_161558609.jpg', 'PXL_20250429_173832221.jpg', 'PXL_20250429_173837910.jpg', 'PXL_20250429_173843963.jpg', 'PXL_20250429_173849395.jpg', 'PXL_20250429_180655016.jpg', 'PXL_20250429_180720440.PORTRAIT.jpg', 'PXL_20250429_193229993.jpg', 'PXL_20250429_193232380.NIGHT.jpg', 'PXL_20250429_202050680.NIGHT.jpg', 'PXL_20250429_202121458.NIGHT.jpg', 'PXL_20250429_223951132.jpg', 'PXL_20250429_223957275.jpg', 'PXL_20250429_224055099.jpg', 'PXL_20250429_230900707.NIGHT.jpg', 'PXL_20250429_232513237.PORTRAIT.jpg', 'PXL_20250429_233032345.jpg', 'PXL_20250429_233105949.jpg', 'PXL_20250430_135026660.jpg', 'PXL_20250430_135227868.jpg', 'PXL_20250430_135231044.jpg', 'PXL_20250430_150557982.jpg', 'PXL_20250430_150603935.jpg', 'PXL_20250430_150758950.jpg', 'PXL_20250430_150813117.jpg', 'PXL_20250430_151708836.jpg', 'PXL_20250430_151714004.jpg', 'PXL_20250430_151716606.jpg', 'PXL_20250430_153611572.jpg', 'PXL_20250430_153621045.jpg', 'PXL_20250430_161539681.jpg', 'PXL_20250430_161640048.PORTRAIT.jpg', 'PXL_20250430_161645425.PORTRAIT.jpg', 'PXL_20250430_161730768.jpg', 'PXL_20250430_162208412.jpg', 'PXL_20250430_162802272.PORTRAIT.jpg', 'PXL_20250430_162808368.PORTRAIT.jpg', 'PXL_20250430_162846283.jpg', 'PXL_20250430_163025618.jpg', 'PXL_20250430_163129674.PORTRAIT.jpg', 'PXL_20250430_170151807.PORTRAIT.jpg', 'PXL_20250430_172601530.jpg', 'PXL_20250430_224442432.jpg', 'PXL_20250430_224828827.jpg', 'PXL_20250501_121357801.jpg', 'PXL_20250501_151736441.jpg', 'PXL_20250501_154514342.jpg', 'PXL_20250501_155642638.jpg', 'PXL_20250501_155647601.jpg', 'PXL_20250501_160426972.jpg', 'PXL_20250501_161004662.jpg', 'PXL_20250501_161024891.jpg', 'PXL_20250501_161536184.jpg', 'PXL_20250501_203047669.PORTRAIT.jpg', 'PXL_20250501_203230818.PORTRAIT.jpg', 'PXL_20250501_224124286.PORTRAIT.jpg', 'PXL_20250502_000345611.jpg', 'PXL_20250502_065359373.jpg', 'PXL_20250502_075702480.jpg', 'PXL_20250502_080114604.jpg', 'PXL_20250502_081508791.jpg', 'PXL_20250502_084446023.jpg', 'PXL_20250502_084717634.jpg', 'PXL_20250502_084926182.jpg', 'PXL_20250502_084929279.jpg', 'PXL_20250502_084935642.jpg', 'PXL_20250502_084938776.jpg', 'PXL_20250502_085333457.jpg', 'PXL_20250502_085434035.jpg', 'PXL_20250502_090029086.jpg', 'PXL_20250502_090242396.jpg', 'PXL_20250502_090408763.jpg', 'PXL_20250502_090813159.jpg', 'PXL_20250502_090904916.jpg', 'PXL_20250502_090923839.NIGHT.jpg', 'PXL_20250502_090945828.jpg', 'PXL_20250502_091034577.jpg', 'PXL_20250502_091038988.jpg', 'PXL_20250502_091336783.jpg', 'PXL_20250502_091444239.jpg', 'PXL_20250502_091455572.jpg', 'PXL_20250502_091513005.jpg', 'PXL_20250502_091651169.jpg', 'PXL_20250502_094452082.jpg', 'PXL_20250502_094559408.jpg', 'PXL_20250502_094606667.jpg', 'PXL_20250502_095822895.jpg', 'PXL_20250502_101318605.jpg', 'PXL_20250502_101346397.jpg', 'PXL_20250502_101738328.jpg', 'PXL_20250502_105049220.jpg', 'PXL_20250502_105317805.jpg', 'PXL_20250502_105723952.PORTRAIT.jpg', 'PXL_20250502_105729646.PORTRAIT.jpg', 'PXL_20250502_114012521.jpg', 'PXL_20250502_140412830.jpg', 'PXL_20250502_141715469.jpg', 'PXL_20250502_142306895.PORTRAIT.jpg', 'PXL_20250502_142311285.PORTRAIT.jpg', 'PXL_20250502_144939365.PORTRAIT.jpg', 'PXL_20250502_145959067.jpg', 'PXL_20250502_150018192.jpg', 'PXL_20250502_151601412.jpg', 'PXL_20250502_152720737.jpg', 'PXL_20250502_152731102.PORTRAIT.jpg', 'PXL_20250502_152748239.PORTRAIT.jpg', 'PXL_20250502_153921115.PORTRAIT.jpg', 'PXL_20250502_153927081.PORTRAIT.jpg', 'PXL_20250502_154110170.PORTRAIT.jpg', 'PXL_20250502_154113338.PORTRAIT.jpg', 'PXL_20250502_154855251.PORTRAIT.jpg', 'PXL_20250502_154856410.PORTRAIT.jpg', 'PXL_20250502_154912344.jpg', 'PXL_20250502_154931364.jpg', 'PXL_20250502_154943410.jpg']

B80_2025_FILENAMES = ['IMG_3404.jpg', 'IMG_3407.jpg', 'IMG_3409.jpg', 'IMG_3418.jpg', 'IMG_3424.jpg', 'IMG_3425.jpg', 'IMG_3426.jpg', 'IMG_3427.jpg', 'IMG_3428.jpg', 'IMG_3433.jpg', 'IMG_3435.jpg', 'IMG_3436.jpg', 'IMG_3441.jpg', 'IMG_3443.jpg', 'IMG_3444.jpg', 'IMG_3459.jpg', 'IMG_3461.jpg', 'IMG_3468.jpg', 'IMG_3471.jpg', 'IMG_3477.jpg', 'IMG_3480.jpg', 'IMG_3481.jpg', 'IMG_3482.jpg', 'IMG_3489.jpg', 'IMG_3490.jpg', 'IMG_3494.jpg', 'IMG_3496.jpg', 'IMG_3499.jpg', 'IMG_3505.jpg', 'IMG_3509.jpg', 'IMG_3541.jpg', 'IMG_3545.jpg', 'IMG_3563.jpg', 'IMG_3566.jpg', 'IMG_3568.jpg', 'IMG_3574.jpg', 'IMG_3575.jpg', 'IMG_3580.jpg', 'IMG_3581.jpg', 'IMG_3582.jpg', 'IMG_3586.jpg', 'IMG_3591.jpg', 'IMG_3593.jpg', 'IMG_3599.jpg', 'IMG_3603.jpg', 'IMG_3606.jpg', 'IMG_3607.jpg', 'IMG_3608.jpg', 'IMG_3609.jpg', 'IMG_3616.jpg', 'IMG_3626.jpg', 'IMG_3637.jpg', 'IMG_3662.jpg', 'IMG_3663.jpg', 'IMG_3664.jpg', 'IMG_3665.jpg', 'IMG_3667.jpg', 'IMG_3669.jpg', 'IMG_3673.jpg', 'IMG_3675.jpg', 'IMG_3680.jpg', 'IMG_3684.jpg', 'IMG_3685.jpg', 'IMG_3697.jpg', 'IMG_3698.jpg', 'IMG_3700.jpg', 'IMG_3701.jpg', 'IMG_3703.jpg', 'IMG_3706.jpg', 'IMG_3713.jpg', 'IMG_3718.jpg', 'IMG_3723.jpg', 'IMG_3727.jpg', 'IMG_3728.jpg', 'IMG_3732.jpg', 'IMG_3735.jpg', 'IMG_3736.jpg', 'IMG_3739.jpg', 'IMG_3740.jpg', 'IMG_3745.jpg', 'IMG_3760.jpg', 'IMG_3762.jpg', 'IMG_3763.jpg', 'IMG_3767.jpg', 'IMG_3770.jpg', 'IMG_3771.jpg', 'IMG_3776.jpg', 'IMG_3781.jpg', 'IMG_3782.jpg', 'IMG_3785.jpg', 'IMG_3789.jpg', 'IMG_3791.jpg', 'IMG_3793.jpg', 'IMG_3795.jpg', 'IMG_3796.jpg', 'IMG_3798.jpg', 'IMG_3801.jpg', 'IMG_3804.jpg', 'IMG_3805.jpg', 'IMG_3806.jpg', 'IMG_3811.jpg', 'IMG_3813.jpg', 'IMG_3816.jpg', 'IMG_3817.jpg', 'IMG_3820.jpg', 'IMG_3822.jpg', 'IMG_3823.jpg', 'IMG_3826.jpg', 'IMG_3829.jpg', 'IMG_3830.jpg', 'IMG_3837.jpg', 'IMG_3842.jpg', 'IMG_3843.jpg', 'IMG_3849.jpg', 'IMG_3851.jpg', 'IMG_3857.jpg', 'IMG_3859.jpg', 'IMG_3860.jpg', 'IMG_3862.jpg', 'IMG_3865.jpg', 'IMG_3866.jpg', 'IMG_3868.jpg', 'IMG_3874.jpg', 'IMG_3877.jpg', 'IMG_3881.jpg', 'IMG_3887.jpg', 'IMG_3913.jpg', 'IMG_3915.jpg', 'IMG_3925.jpg', 'IMG_3932.jpg', 'IMG_3933.jpg', 'IMG_3938.jpg', 'IMG_3942.jpg', 'IMG_3964.jpg', 'IMG_3984.jpg', 'IMG_3985.jpg', 'IMG_3986.jpg', 'IMG_3989.jpg', 'IMG_3990.jpg', 'IMG_4017.jpg', 'IMG_4018.jpg', 'IMG_4023.jpg', 'IMG_4026.jpg', 'IMG_4031.jpg', 'IMG_4053.jpg', 'IMG_4055.jpg', 'IMG_4056.jpg', 'IMG_4059.jpg', 'IMG_4062.jpg', 'IMG_4111.jpg', 'IMG_4112.jpg', 'IMG_4114.jpg', 'IMG_4122.jpg', 'IMG_4127.jpg', 'IMG_4130.jpg', 'IMG_4131.jpg', 'IMG_4133.jpg', 'IMG_4150.jpg']

README_TEXT = """Deferred Work - Reference Notes
===================================

This folder holds reference material for photographer folders that
are NOT yet downloaded to this PC. Nothing in here is a source image -
these are just checklists and notes to use once each folder exists.

2025 Pacome/
    expected_filenames.txt - the 196 filenames the Media Database
    expects for this photographer/year. Once the folder is downloaded,
    these can be cross-checked against what actually landed on disk.

2025 Photos B80/
    expected_filenames.txt - the 158 filenames the Media Database
    expects for this photographer/year.
    NOTES.txt - important: this folder is mostly Canon 700D RAW
    (.CR2) files. The current scanner (scan_originals_v2.py) cannot
    read EXIF data or dimensions from .CR2 files - it will flag them
    all as UNREADABLE. That's safe (nothing gets wrongly deleted),
    but it means date+dimension matching won't help distinguish
    files within this folder until RAW/EXIF support is added to the
    scanner (deferred - ask to add it once this folder is ready to
    work on).

Last generated: 2026-09-17
"""

B80_NOTES_TEXT = """Photos B80 (2025) - Special Note
====================================

This folder is mostly Canon 700D RAW (.CR2) files.

The scanner (scan_originals_v2.py) uses Pillow, which CANNOT open
.CR2 files. Every RAW file in this folder will come back as
EXIF Status = UNREADABLE (no date, no dimensions) until RAW support
is added.

Per the deletion-safety rules already in place, UNREADABLE files are
automatically excluded from any deletion pass and kept - so this is
safe, but it means the date+dimension matching approach gives no
real help sorting this folder out on its own.

Before doing any cleanup pass on this folder specifically, the
scanner needs a RAW-EXIF library added (e.g. exifread), which reads
embedded EXIF metadata - including capture date and dimensions -
directly out of .CR2 files without needing a full RAW decoder.

Ask to add this whenever B80 is actually downloaded and ready to
work on.
"""


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Expected filenames — {len(lines)} files\n")
        f.write("Source: Media Database sheet\n\n")
        for line in lines:
            f.write(line + "\n")


def main():
    print("Enos Media Manager - Deferred Work Folder Setup")
    print("=" * 50)

    DEFERRED_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Created: {DEFERRED_ROOT}")

    (DEFERRED_ROOT / "README.txt").write_text(README_TEXT, encoding="utf-8")
    print(f"Created: {DEFERRED_ROOT / 'README.txt'}")

    pacome_folder = DEFERRED_ROOT / "2025 Pacome"
    pacome_folder.mkdir(exist_ok=True)
    write_lines(pacome_folder / "expected_filenames.txt", PACOME_2025_FILENAMES)
    print(f"Created: {pacome_folder / 'expected_filenames.txt'}  "
          f"({len(PACOME_2025_FILENAMES)} filenames)")

    b80_folder = DEFERRED_ROOT / "2025 Photos B80"
    b80_folder.mkdir(exist_ok=True)
    write_lines(b80_folder / "expected_filenames.txt", B80_2025_FILENAMES)
    print(f"Created: {b80_folder / 'expected_filenames.txt'}  "
          f"({len(B80_2025_FILENAMES)} filenames)")
    (b80_folder / "NOTES.txt").write_text(B80_NOTES_TEXT, encoding="utf-8")
    print(f"Created: {b80_folder / 'NOTES.txt'}")

    print()
    print("Done. Nothing under 2025/ or 2026/ was touched.")


if __name__ == "__main__":
    main()
