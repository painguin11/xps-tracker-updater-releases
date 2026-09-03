# XPS Tracker Updater Releases

This repository hosts official release packages and the automatic-update manifest for XPS Tracker Updater.

The updater checks `update_manifest.json` over HTTPS, downloads a newer ZIP only after user approval, verifies its SHA-256 checksum, backs up the installed program files, installs the update after the application closes, and restores the prior version if installation fails.

No master spreadsheets, scanned PDFs, trouble tickets, OCR caches, logs, or company data are stored here.


## v85

- Keeps every confirmed physical table row between the detected header and total, even when endpoint/date OCR needs review.
- Improves failed-total OCR recovery, including subtle decimal/grid-line misreads, without rounding or manufacturing PDF values.
- Keeps duplicate-looking Cleaning rows visible for total validation while preventing duplicate master writes.
- Adds PDF image previews beside every editable extracted-row field, with a PDF page fallback when a crop is unavailable.

## v86

- Adds a whole-column endpoint OCR pass so grid strokes no longer erase valid EC-, DN-, or R2- prefixes from otherwise readable rows.
- Allows Pipe/Cleaning upstream and downstream nodes to be edited directly in Edit Selected, with a PDF preview beside each field.
- Allows Manhole asset IDs to be edited directly in Edit Selected, with a PDF preview beside the field.
- Re-matches manually corrected asset/node IDs against the selected master immediately and updates the row review state.
- Preserves v85 physical-row retention, exact total reconciliation, split/MSA handling, and exact PDF-number safeguards.
