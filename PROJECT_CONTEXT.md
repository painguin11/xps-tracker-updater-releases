# XPS Tracker Updater project context

## Resume instructions

Repository: `painguin11/xps-tracker-updater-releases`

Current production version: **v68**. The repository's v68 source bundle contains
the complete app directory and regression scripts and must match the v68 release
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

## Current v68 fixes

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
