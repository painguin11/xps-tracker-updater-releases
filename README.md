# XPS Tracker Updater Releases

This repository hosts official release packages and the automatic-update manifest for XPS Tracker Updater.

The updater checks `update_manifest.json` over HTTPS, downloads a newer ZIP only after user approval, verifies its SHA-256 checksum, backs up the installed program files, installs the update after the application closes, and restores the prior version if installation fails.

No master spreadsheets, scanned customer PDFs, trouble tickets, OCR caches, logs, or other company data are stored here.

## Current production release: v96

- Tag: `v96`
- Release: `XPS Tracker Updater v96`
- Release commit: `e2212501d57f46105c05bde13cd8bb1e0b258ac5`
- Asset: `XPS_Tracker_Updater_v96.zip`
- Size: `303588` bytes
- SHA-256: `d8d65072fdcd902ccf736c112dcddc0bceffd9ab5d54451882cdc6b513ffa4dc`

The public updater manifest points to this verified v96 asset.

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
- An unreadable page no longer aborts the whole PDF: readable rows are kept, later pages continue processing, and Live Summary shows the affected work order/page warning at the top.
- Fixes continuation value-cell clipping while preserving exact printed values.

## v89

- Verifies Manhole work orders against a user-confirmed count shown in the Description of Work crop.
- Uses only the final continuation page total for multi-page Pipe/Cleaning total verification.
- Adds Add to Master / Ignore / Back to Summary decisions for unresolved Pipe and Manhole rows.
- Limits automatic MSA combination to exactly two duplicate Pipe rows; three or more remain blocked for review.
- Adds PDF field previews to Trouble Ticket editing.
- Preserves complete printed endpoint pairs that are absent from the master instead of fuzzy-mapping them to nearby assets.
- Recovers narrow left-grid OCR artifacts and recognizes common OCR variants of Length Surveyed headers.

## v90

- Adds upstream/downstream PDF ID crops directly to unresolved Pipe/Cleaning Add-to-Master / Ignore review.
- Adds the Manhole ID crop to unresolved Manhole review.
- Preserves Live Summary scroll position and the selected/focused row after editing instead of jumping back to the top.
- Preserves v89 printed-pair identity, continuation, total, MSA, and review safeguards.

## v91

- Adds PDF ID crops to the suffixed NEW PIPE / NEW MANHOLE approval flow.
- Adds conservative damaged-endpoint recovery only when both OCR-observed numeric bodies uniquely identify one directional master pipe.
- Redesigns Work Order OCR around the real form: machine-typed pink/magenta text is isolated before OCR instead of discarding the color signal.
- Keeps the editable confirmation popup and existing review safeguards.

## v92

- Allows the color-aware Work Order OCR path to recognize either 4- or 5-digit machine-typed pink/magenta Work Order numbers.
- Keeps color isolation primary while retaining editable confirmation and conservative grayscale fallback behavior.
- Preserves v91 new-asset preview and endpoint-recovery safeguards.

## v93

- Makes Work Order prefilling fail closed: faded/low-confidence color OCR opens the confirmation field blank instead of showing a weak guess.
- Keeps clean 4- and 5-digit Work Orders auto-filling.
- Writes `NEW PIPE` or `NEW MANHOLE` into the master Notes column for approved new rows, including Add-to-Master rows.
- Preserves v92 and earlier parsing/matching safeguards.

## v94

- Adds a lazy padded-stack digit OCR fallback for pair-table endpoint cells when whole-column OCR skips an otherwise clean row.
- Uses the stacked observations only through the existing conservative numeric-body recovery path.
- Recovery still requires observed numbers from both endpoint cells and exactly one existing directional master pair.
- Fully printed non-master pairs remain unresolved for Add/Ignore review.
- Preserves v93 and earlier W/O, new-asset, continuation, total, R2, split-pipe, and review safeguards.

## v95

- Recovers faint/dashed horizontal row rules in the affected compact Brown & Caldwell table style instead of skipping the page.
- Keeps normal solid compact tables on the unchanged first parsing pass.
- Gives exact endpoint numeric-body matches priority over tolerated leading-junk OCR matches, preventing valid exact pairs from becoming falsely ambiguous.
- Preserves true ambiguity as unresolved and does not manufacture IDs from master data.
- Preserves v94 stacked endpoint recovery, v93 low-confidence Work Order behavior and NEW PIPE / NEW MANHOLE notes, plus all earlier continuation, matching, total, review, R2, and split-pipe safeguards.

## v96

- Hardens Phase 2 Pipe/Cleaning OCR reconciliation while keeping corrections grounded in PDF-observed values.
- Prevents a whole-table Pipe reread from replacing an already-correct measurement with a worse OCR alternative.
- Preserves digit-bearing R2 IDs and printed direction, leaving opposite-direction master pairs unresolved.
- Sends compact tables with usable geometry but incomplete automatic role mapping into Layout Review instead of skipping or crashing.
- Includes the post-v95 MSA review/reversal, NEW PIPE suffix-priority, padded complete endpoint-ID, and faint-row safeguards.
- Verified against the 8-20, 8-21, 8-25, and 8-27 private Phase 2 matrix plus the full active regression suite.

## Development baseline

Current development continues on `v95-work`. Read `AGENTS.md`, `PROJECT_CONTEXT.md`, and `RELEASE_CHECKLIST.md` before changing behavior. Do not publish a new release until explicitly instructed to do so.
