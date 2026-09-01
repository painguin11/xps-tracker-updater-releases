# XPS Tracker Updater release checklist

## Required checks

1. Compile `app/reno_scan_updater.py` and `app/xps_update.py`.
2. Confirm the displayed/app/updater versions all match the release number.
3. Run applicable scripts in `tests/` with their local fixtures.
4. Confirm the ZIP contains the complete `app/` directory and passes ZIP
   integrity testing.
5. Confirm unrelated Reno/Year 15/Phase 2 parsing code was not removed.

## Regression expectations

- Tall cleaning fixture: page classified as cleaning, rotation 270 degrees,
  ten columns, roles `up=1`, `down=2`, `value=8`, `date=9`, exactly 17 data rows,
  exact R2 IDs, and the v68 length sequence documented in PROJECT_CONTEXT.md.
- Work-order preview: known W/O is fully visible and OCR still reads `11976`.
- Split pipes: lengths combine once, MSA feedback is present, and no normal
  duplicate suppression removes a part.
- New assets: single-letter suffix detection, approval path, insertion beneath
  the base row, and full-row green highlight.
- Trouble tickets: pages parse, repeated asset history remains separate and
  adjacent, true page duplicates are skipped, workbook migration/layout/status
  dropdown and backups remain correct.
- R2 canonicalization: `R2-280` and `R2 280` both become `R2-280`, while
  `DE-1234A` remains unchanged.

Some Excel COM and Windows GUI checks cannot run in Linux. State that limitation
explicitly; do not imply those paths were executed.

## Packaging and publishing

1. Package as `XPS_Tracker_Updater_vNN.zip` with one top-level
   `XPS_Tracker_Updater/` directory.
2. Calculate the local SHA-256.
3. Publish GitHub release tag `vNN` and upload the ZIP.
4. Verify the public asset name, size, and GitHub-reported SHA-256.
5. Update `update_manifest.json` only after verification, using the exact public
   download URL and checksum.
6. Fetch the manifest again to verify the committed version, URL, and checksum.

Never publish customer fixture PDFs or master workbooks.
