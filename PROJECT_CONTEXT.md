## Current Production Release
- **v78**
- Cleaning Wheel Walk values use aligned column OCR; v75 cell OCR is fallback-only.
- The PDF total is validation-only and never rewrites row lengths.
- OCR cache namespace is v5.

# XPS Tracker Updater project context

## Resume instructions

Repository: `painguin11/xps-tracker-updater-releases`

Current production version: **v75**. The repository's v75 source bundle contains
the complete app directory and regression scripts and must match the v75 release
ZIP. In a new conversation, begin with:

> Continue the XPS Tracker Updater project from the connected GitHub repository.
> Read AGENTS.md, PROJECT_CONTEXT.md, and RELEASE_CHECKLIST.md before changing
> anything. Use the current app source and keep all existing behavior.

Ask the user to attach a specific PDF or workbook only when it is needed for a
new fixture-based regression. Do not request the old conversation transcript.

## Purpose and workflow

The Windows/Tkinter application reads scanned Xpert Pipe Services PDF packets,
matches pipe, cleaning, and manhole rows against a selected Excel master, shows
the extracted rows for review/editing, backs up the workbook, and writes approved
updates. Trouble-ticket pages are written to `Trouble Tickets.xlsx` beside the
selected master.

Normal workflow:

1. Select PDF and master workbook. Selecting a new PDF clears old results.
2. Analyze PDF. Confirm each work order's W/O, truck, and operator.
3. Review rows. Double-clicking a row opens the same editor as Edit Selected.
4. Cancel Current Process may stop analysis; incomplete rows are cleared.
5. Update Master creates backups and logs before saving.

The title bar contains the version. Analyze uses a stationary label with a
left-to-right progress fill. The interface uses the green header style and
native-size DPI-aware icons.

## Supported master profiles

- **Consor/Reno:** `Pipes` and `Manholes`. Preserve the proven Reno parsing path.
- **Brown & Caldwell Year 15:** `Year15Pipes` and `Year15Manholes`.
- **B&C Small Diameter Phase 2 Year 1:** `Pipes` and
  `Phase 2 Year 1 Manholes`.

Pair-based tables dynamically map upstream node, downstream node, activity
length, and activity date. The layout confirmation must show the actual printed
columns and may use master-pair scoring when header OCR is incomplete.

## Core data rules

- Dates are stored/displayed as month/day/year with no time component.
- Truck codes follow two letters plus two digits, such as `CT01`.
- Operator is stored as first name plus last initial and written in uppercase.
- W/O, truck, operator, and new notes are written in uppercase.
- Existing populated master values are not overwritten without confirmation.
- Master backups go in `Backups`; logs and processed-PDF records go in `Logs`.
- A PDF is considered previously processed only when the same W/O is already in
  the master.
- Rows stream into the summary one at a time across all project parsers.
- Ignored/unrecognized pages are reported with page number and reason.
- Persistent OCR caching stays enabled but cache counters are hidden from users.

## Matching and validation

- Preserve complete IDs, including prefixes, hyphens, digit-bearing prefixes,
  and letter suffixes. Examples: `DE-1234`, `DE-1234A`, `R2-280`.
- Pair rows match the complete upstream/downstream IDs, not number-only forms.
- Video and Wheel Walk differences greater than 4.5 feet are review warnings,
  highlighted red in the UI and applicable master cell, with an uppercase note.
- Consor/Reno pipe count comes only from the integer beside
  `Number of surveys in this`.
- Consor/Reno manhole count comes only from `Report Survey Count`.
- Cleaning and all Brown & Caldwell profiles have no printed-count validation.
- Keep duplicate, match-rate, grid, zero-row, structural, and length validations.
- Header rows and final total rows must never become summary/master rows.

## Split pipe surveys

The same pipe may appear on two or more video lines in one work order. Add the
part lengths and compare the combined total with the master. Write one combined
update, retain missing-part warnings, and include `MSA DETECTED` plus the number
of combined parts in feedback. This behavior applies to pipe video, not cleaning,
manholes, or rows from separate work orders.

## New suffixed assets

A new manhole is valid only when it is an existing master manhole ID plus one
trailing letter, for example `DE-1234A` based on `DE-1234`. A new pipe may have
the suffix on its upstream endpoint, downstream endpoint, or both.

Do not correct these back to the base asset. Show `NEW MANHOLE` or `NEW PIPE`,
request approval, and if approved insert the new row directly below the base
asset and highlight the entire row green. Declined rows remain skipped and say
`NOT APPROVED`.

## Trouble Tickets.xlsx

- Create it beside the selected master or append to the existing workbook.
- Back it up before modifying an existing file.
- Never collapse separate tickets merely because they share an asset. New issues
  and updates remain separate rows, adjacent to that asset's history.
- Prevent only true duplicate page imports using the hidden stable source key.
- Primary column order:
  `Pipe/MH ID`, `Description`, `Date`, `Work Order`, `Truck`, `Operator`,
  `Panel`, `Street`, `Area / Major Intersection`, followed by remaining fields.
- Operator also represents Reported By; there is no separate Reported By field.
- New rows default Status to `Open`; dropdown values are Open, In Progress,
  Resolved, and No Action Needed.
- Keep Resolution / Follow-up Notes and the green workbook header.

## Current v75 fixes

- OCR cache namespace advances from v2 to v3. Old cache files remain on disk but
  v75 does not reuse stale OCR strings from earlier parser/OCR behavior.
- Cleaning rows that enter the existing uncertainty consensus also receive the
  grid-rule-removal OCR pass already used for printed totals. This targets
  digit loss/substitution such as 275 -> 75 and 224 -> 274 without inventing a
  value from the master workbook.
- Sheet-date OCR compacts a digit split between printed date separators before
  token candidate voting, so text such as 8/1 1/2026 is treated as 8/11/2026
  rather than creating a shifted 1/1/2026 candidate.
- On the supplied 8/11/2026 page, fresh local OCR reads the two disputed cleaning
  values as 275 and 224; grid-rule-removed OCR also favors those printed values.
  The customer PDF itself is not stored in this repository.

## Current v74 fixes

- Pair-table printed totals that occupy a detected grid band are identified before
  row parsing and excluded from the live summary/master rows. The total remains
  available only as independent total-length validation evidence.
- Header/footer OCR noise is filtered before table-date repair, preventing labels
  such as header text from becoming unmatched asset rows.
- When a repeated table date agrees with the confirmed work-order date, a
  different row date must have at least three independent strong full-date OCR
  reads to be preserved; weaker outliers are corrected to the dominant date.
- The 8/11/2026 cleaning fixture has one header band, 17 real data rows, and one
  final 4476 total band; the customer PDF itself is not stored in this repository.

## Current v73 fixes

- Pair-table totals may be inside the final detected grid row or below the grid; table rules are removed before total OCR.
- Implausible single-digit totals on multi-row tables fail closed. The local 8/11/2026 fixture reads 4476 rather than 4.
- B&C pair-table dates use repeated table evidence to correct weak OCR while clearly read full YYYY dates are preserved.

## Current v72 fixes

- Normal Year 15 / Phase 2 pair tables still use the existing strict full-page
  grid detector.
- If that detector fails, a compact-table fallback isolates the largest connected
  table region and measures grid continuity relative to the table itself.
- This handles small/light B&C tables without hard-coding column positions. The
  8/26/2026 packet was locally checked at 7 columns on page 4 and 9 columns on
  pages 10 and 12; the customer PDF itself is not stored in this repository.

## Current v71 fixes

- Pipe/cleaning activity tables can independently read the printed PDF total and
  reconcile it against the sum of extracted summary lengths for the same work
  order and activity.
- A total mismatch is fail-closed: affected rows are dark red and Update Master
  is blocked until the values reconcile.
- The user may correct the OCRed printed total after visually verifying the PDF;
  doing so changes only the validation target, never individual row lengths.
- Editing an extracted length automatically recalculates total validation.
- Cleaning length OCR now performs the focused border-free reread when the first
  pass is blank or contains only invalid values, including the 114 -> 6114/36114
  failure mode found during the 8-20-2026 regression review.

## Current v70 fixes

- A table-layout confirmation popup is skipped only when native detection is
  100% confident and all four required roles are already mapped.
- Main-window fixed pixel dimensions are scaled using the current Windows DPI;
  summary rows/columns and the Analyze button remain readable across display
  scaling settings, and Asset / Nodes plus Status can expand with the window.
- Pair-table header detection preserves recognized partial roles instead of
  discarding them when one role is missing.
- B&C cleaning tables can recover a narrow final Wheel Walk / Cleaning Date pair
  when OCR recognizes the last column as Date and the immediately preceding
  column as Length.

## Current v69 fixes

- Unresolved R2 endpoint cells receive a focused, border-free OCR pass.
- OCR artifacts such as `32-427`, `2-417`, and a grid-rule character after
  `R2-414` recover only when the exact endpoint already exists in the master and
  the complete upstream/downstream pair identifies one master pipe.
- Joined one-letter suffixes such as `R2-414A` and `R2-414S` remain possible new
  assets and are never reduced to the base ID by this recovery.
- The supplied `8-17-2026(1).pdf` regression resolves `R2-427 -> R2-414` and
  `R2-417 -> R2-427`.

## v68 baseline fixes

- `R2-280` remains `R2-280`; it must never normalize to `R-2280`.
- Tall wrapped cleaning headers are recognized.
- The header and final total row are excluded.
- Fallback layout options have no false blank Column 1 and expose Cleaning Date
  as the final column.
- Work-order confirmation previews display the complete handwritten number.
- Questionable Wheel Walk cells are re-read with multiple border-free crops.
  OCR consensus chooses the printed length; the master value may only break an
  equal OCR vote and may never supply a value OCR did not read.
- The supplied `8-11-2026.pdf` regression has 17 cleaning rows and lengths:
  `369, 369, 314, 2, 313, 72, 268, 400, 78, 345, 320, 291, 366, 350, 275, 224, 120`.

## Automatic updates

At startup, the app reads the public `update_manifest.json`, offers a newer
release, downloads its ZIP, verifies SHA-256 and package contents, closes,
installs, rolls back on failure, and restarts. It preserves `.venv`, LocalAppData
settings, OCR caches, history, and layout profiles. Network failure must never
prevent the installed version from opening.
