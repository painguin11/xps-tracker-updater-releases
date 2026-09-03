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


## v88

- Fixes Brown & Caldwell table geometry when faint or interrupted grid lines caused multiple printed columns to be merged.
- Supports headerless continuation pages for Pipe, Cleaning, and Manhole tables within the same work order.
- Pipe/Cleaning continuations reuse the preceding confirmed column layout and orientation; Manhole continuations inherit the confirmed table type/orientation without borrowing pair-table geometry.
- An unreadable page no longer aborts the whole PDF: readable rows are kept, later pages continue processing, and the live summary shows the affected work order and page numbers at the top.
- Fixes continuation value-cell clipping, including the 8-24-2026 Cleaning continuation where pages 10-11 reconcile to the printed 4430-ft total.
- Preserves v86 endpoint OCR, editable asset/node fields, split/MSA handling, and exact PDF-number safeguards.
