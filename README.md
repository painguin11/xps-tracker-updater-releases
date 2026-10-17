# XPS Tracker Updater Releases

This repository hosts official release packages and the automatic-update manifest for XPS Tracker Updater.

The updater checks `update_manifest.json` over HTTPS, downloads a newer ZIP only after user approval, verifies its SHA-256 checksum, backs up the installed program files, installs the update after the application closes, and restores the prior version if installation fails.

No master spreadsheets, scanned customer PDFs, trouble tickets, OCR caches, logs, or other company data are stored here.

## Current production release: v111

- Release: [XPS Tracker Updater v111](https://github.com/painguin11/xps-tracker-updater-releases/releases/tag/v111)
- Release commit: `f2bd0cf4406c90299d2673877ed46953f34b52fa`
- Asset: `XPS_Tracker_Updater_v111.zip`
- Size: `332998` bytes
- SHA-256: `c33d76c1fcb4e1071f0502f59300628f434892f2258bf92636f95e527801c725`

The production updater reads the verified v111 asset through `update_manifest.json` on `main`.
Development remains on `v95-work` under `working_source/`.

## v111

- Reject dates later than the current local calendar date from report text, sheet-table OCR and Trouble Tickets.
- Keep date cells visible for review when OCR sees future dates rather than automatically writing a potentially wrong date.
- Prevent future manual dates and block workbook updates until rejected future dates are corrected.
- All 59 historical regressions and 4 supplemental regression tests passed on Linux.
- The public v111 ZIP was re-downloaded and checked for exact size, SHA-256 and ZIP integrity before the manifest advanced.
- Windows Excel COM, interactive Tkinter and private-fixture OCR were not exercised by the public Linux runner.

## v110

- Improved Pipe/Cleaning OCR for border-clipped numeric cells with corroborated PDF evidence; uncertainty remains review-only.
- Conservative compact table row/column geometry and full-date disagreement checks.
- Live Summary shows plain rows with empty Comments during extraction; final warnings and colors appear after completion.
- 59/59 historical regressions and additional OCR/geometry/GUI-model tests passed on Linux.
- Three selected private scanned pages achieved 47/47 physical rows, 94/94 IDs, 47/47 lengths, and 47/47 dates.
- Windows Excel COM, interactive Tkinter and inaccessible private fixture validation remain unverified.

## v109

- Recovers missing physical Pipe rows when rotated compact Brown & Caldwell tables have a small residual scan skew.
- Uses a guarded long-rule skew estimate and accepts a corrected grid only when it restores multiple row bands while preserving the column structure.
- Leaves normally aligned tables on their existing path; no weakening of matching, totals or review safeguards.
- Passed all **59/59 active Linux regression scripts**; the published v109 ZIP was independently re-downloaded and verified before the auto-update manifest advanced.

## v108

- Adds contextual whole-table numeric OCR for compact Pipe length cells only when independent OCR passes agree on the same physical row.
- Keeps isolated-cell OCR as the fallback and never invents length values from the master or printed total.
- Tolerates bounded grid damage around the Manhole Date header so the physical Manhole column is still located correctly.
- Requires corroborating PDF evidence before a damaged Manhole crop can override another complete existing ID.
- Passed all **58 active Linux regression scripts** before publishing; the public ZIP was re-downloaded and its exact size/SHA-256 verified before the auto-update manifest advanced.

## v107

- Keeps the normal fast classification path for clear/high-confidence pages.
- Uses the existing 2.5x structured-header retry only for ambiguous B&C table pages.
- If that header is still inconclusive, OCRs a copy with long table rules suppressed while retaining the original ruled image for geometry.
- Keeps Pipe classification tolerant only when `Surveyed`, endpoint evidence, and normal table context agree.
- Passed all **57 active Linux regression scripts** before publishing; the public ZIP was re-downloaded and its exact size/SHA-256 verified before the auto-update manifest advanced.

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

## v97

- Makes all six MSA row fields editable beside the PDF crops.
- Saves corrected non-matching rows without merging them into an MSA.
- Fixes the 8-26 82.87-to-2.87 split-pipe OCR failure and refreshes the OCR cache generation.
- Preserves the full v96 safeguard baseline.

## v102

- Adds multi-select **Discard Work Order(s)** during review.
- When Update Master finds W/Os that are not fully green/ready, allows whole problem W/Os to be ignored while clean W/Os continue.
- Removes discarded/ignored W/Os from pending rows, Trouble Tickets, total/count validations, unprocessed-page blockers, and group state.
- Enlarges the Manhole expected-count Description of Work preview for small handwriting.
- Keeps the established v101 OCR/table parsing behavior unchanged.
- Passed all 50 active Linux regression scripts before publishing; public ZIP checksum/size were verified after re-download before the auto-update manifest advanced.

## v103

- Compares positioned-token B&C Manhole OCR with physical ruled-row parsing so clipped or partially read reports can recover missing rows.
- Automatically performs slower Manhole OCR rereads when the first-pass count differs from the user-confirmed expected Manhole count.
- Keeps recovery conservative: only PDF-observed IDs that pass existing matching/new-suffix safeguards may be added; rows are never fabricated, deleted, or arbitrarily selected to force the count.
- Preserves all v102 review controls plus earlier Pipe, Cleaning, Manhole, Trouble Ticket, MSA, continuation, total, and master-write safeguards.
- Passed all **52 active Linux regression scripts** before publishing; the public ZIP size/SHA-256 were verified after re-download before the auto-update manifest advanced.

## v105

- Preserves independently confirmed one-letter NEW MANHOLE suffixes instead of collapsing them to an existing base Manhole.
- Applies the same confirmation rule during expected-count retry.
- Prefers tied ruled-row OCR when it carries an independently confirmed new suffix.
- Keeps generic unmatched IDs and unconfirmed suffixes conservative and review-only.
- Passed all **53 active Linux regression scripts** before publishing; the public ZIP size/SHA-256 were verified after re-download before the auto-update manifest advanced.

## v106

- Keeps structurally detected Pipe, Cleaning, and Manhole rows visible when OCR/master matching fails.
- Adds a structured-header retry for rotated Pipe tables whose fast orientation OCR misses the Pipe headers.
- Adds **Remove Selected Row** so a reviewer can remove one false extra extracted row without discarding the rest of the work order.
- Recalculates Manhole counts, Pipe/Cleaning totals, and duplicate/MSA review state after explicit row removal without auto-removing another row.
- Passed all **56 active Linux regression scripts** before publishing; the public ZIP size/SHA-256 were verified after re-download before the auto-update manifest advanced.

## Development baseline

Current development continues on `v95-work`. Read `AGENTS.md`, `PROJECT_CONTEXT.md`, and `RELEASE_CHECKLIST.md` before changing behavior. Do not publish a new release until explicitly instructed to do so.

## v98

- Fixes the 8-26 Cleaning rows whose printed Wheel Walk values 34 ft and 54 ft could be reduced to 7 ft during total reconciliation.
- Restores a clipped leading digit only when the complete value was independently observed by both stacked-column and row-cell OCR.
- Preserves v97 editable MSA review and all earlier safeguards.

## v99

- Recognizes very short, wide B&C Pipe/Cleaning tables with guarded geometry.
- Preserves the separate short/one-row Manhole parser.

## v100

- Recovers faint interior vertical rules in compact B&C pair tables with a
  guarded retry after normal detection fails.

## v101

- Detects labeled ruled Trouble Ticket cells across Consor and B&C forms.
- Preserves complete IDs, wrapped descriptions, dates, field previews, and review
  safeguards; accommodates bounded scan skew observed in the 8-26 packet.
- Retains ticket history, duplicate-page identity, and existing table behavior.
