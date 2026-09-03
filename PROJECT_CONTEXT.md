# XPS Tracker Updater project context

## Resume instructions

Repository: `painguin11/xps-tracker-updater-releases`

Current production version: **v95**.

Current development branch: **`v95-work`**.

The editable source and active regression suite are under `working_source/` on
`v95-work`. Start future work from that branch and preserve the v95 baseline.
Do **not** publish another version until the user explicitly says `PUBLISH`.

Public v95 release:

- Tag: `v95`
- Release title: `XPS Tracker Updater v95`
- Release commit: `427bf94939484ed7aa19d05a6a9166893d190b75`
- Asset: `XPS_Tracker_Updater_v95.zip`
- Asset size: `298928` bytes
- SHA-256: `eb4e816b010d7cf8730e97ad83acc40bc502f6f175085d49c13fce891999be41`
- `working_source/app/reno_scan_updater.py`: `APP_VERSION = '95'`
- `working_source/app/xps_update.py`: `CURRENT_VERSION = "95"`
- Public `update_manifest.json` points to that exact v95 asset/checksum.

Documentation-only commits after release may advance the `v95-work` branch head;
they do not change the published v95 release commit above.

In a new conversation, begin with:

> Continue the XPS Tracker Updater project from the connected GitHub repository.
> Read AGENTS.md, PROJECT_CONTEXT.md, and RELEASE_CHECKLIST.md before changing
> anything. Start from v95-work, preserve the current v95 behavior, and do not
> publish until I explicitly say PUBLISH.

Ask for a private PDF/workbook only when a new real-fixture regression actually
requires it. Customer fixtures must never be committed to this public repository.

## Purpose and workflow

The Windows/Tkinter application reads scanned Xpert Pipe Services PDF packets,
matches Pipe, Cleaning, and Manhole rows against a selected Excel master, shows
extracted rows for review/editing, backs up the workbook, and writes approved
updates. Trouble-ticket pages are written to `Trouble Tickets.xlsx` beside the
selected master.

Normal workflow:

1. Select PDF and master workbook. Selecting a new PDF clears old extracted rows.
2. Analyze PDF. Confirm each work order's W/O, Truck, and Operator.
3. Review live summary rows. Double-click opens the same editor as Edit Selected.
4. Unresolved/new rows retain explicit review paths instead of being silently
   guessed.
5. Cancel Current Process may stop analysis; incomplete rows are cleared.
6. Update Master creates backups/logs and writes approved updates.

Readable rows should stream into Live Summary as they are found. A single
unreadable page must not abort the whole packet: later readable pages continue,
and skipped-page warnings appear at the top of Live Summary with work order/page
information.

The title bar contains the version. The interface retains the green header style,
DPI-aware/native-size icons, field preview crops, and review/edit behavior added
through v90 and earlier.

## Supported master profiles

- **Consor/Reno:** `Pipes` and `Manholes`. Preserve the proven Reno path.
- **Brown & Caldwell Year 15:** `Year15Pipes` and `Year15Manholes`.
- **B&C Small Diameter Phase 2 Year 1:** `Pipes` and
  `Phase 2 Year 1 Manholes`.

Pair-based tables dynamically map upstream node, downstream node, activity
length, and activity date. Layout confirmation must reflect the printed columns.
Compact B&C tables and continuation pages have dedicated safeguards documented
below.

## Core data rules

- Dates are stored/displayed as month/day/year with no time component.
- Truck codes follow two letters plus two digits, such as `CT01`.
- Operator is stored as first name plus last initial and written in uppercase.
- W/O, Truck, Operator, and generated Notes are written in uppercase.
- Existing populated master values are not overwritten without confirmation.
- Master backups go in `Backups`; logs and processed-PDF records go in `Logs`.
- A PDF is considered previously processed only when the same W/O already exists
  in the master.
- Persistent OCR caching stays enabled; cache counters remain hidden from users.
- Header rows and printed final-total rows must never become summary/master rows.
- Video/Wheel Walk difference threshold remains **4.5 ft**. Differences greater
  than that are highlighted red and produce an uppercase master note.

## Work Order OCR baseline (v91-v93)

Work Order numbers on these forms are machine-typed pink/magenta text, not
handwriting. Valid numbers may be **4 or 5 digits**.

The primary OCR path isolates the pink/magenta ink so green form rules and black
labels do not interfere. A conservative grayscale fallback remains for genuinely
desaturated scans.

The confirmation popup remains editable. If color-aware OCR evidence is visibly
weak or OCR passes do not agree strongly enough, leave the W/O field **blank**
rather than confidently prefilling a bad number.

Do not alter Operator/Truck OCR unless the user specifically requests it.

## Matching safeguards

Preserve complete asset IDs, including prefixes, hyphens, digit-bearing prefixes,
and suffixes. Examples include `DE-1234`, `DE-1234A`, and `R2-280`.

Important rules:

- Pair rows match the complete directional upstream/downstream identity, not only
  number bodies.
- `R2-280` must never normalize to `R-2280`.
- Joined suffixes such as `R2-414A` / `R2-414S` must remain structurally possible.
- Fully printed valid IDs absent from the master remain unresolved for explicit
  Add/Ignore review rather than being fuzzy-corrected to nearby master assets.
- Master data must never invent an endpoint that OCR did not actually observe.
- Prefix ambiguity must fail closed.

### Conservative endpoint recovery (v91-v95)

Damaged Pipe/Cleaning endpoint recovery may use numeric-body evidence only when:

1. OCR/PDF evidence supplies numeric information from **both** endpoint cells;
2. those observations resolve to exactly one existing directional master pair;
3. there is no true prefix ambiguity.

v94 added a lazy padded-stack digit OCR fallback for endpoint cells when normal
whole-column OCR misses an otherwise clean row. It still feeds the same
conservative both-endpoint/unique-directional-pair resolver.

v95 gives **exact numeric-body matches priority** over tolerated leading-junk
matches. This prevents a valid exact pair such as `DN-1911 -> DN-1912` from being
made ambiguous by smaller IDs that only match after tolerated OCR junk is
removed.

The tolerated leading-junk fallback still works when an exact body was not read.
True ambiguities and fully printed non-master pairs remain unresolved.

## NEW PIPE / NEW MANHOLE

A new Manhole is valid when it is an existing master manhole plus one trailing
letter, for example `DE-1234A` based on `DE-1234`. A new Pipe may have the suffix
on its upstream endpoint, downstream endpoint, or both.

Do not correct these back to the base asset.

Suffixed new assets use crop-capable confirmation/review UI. If approved:

- insert the new row directly below its base asset when possible;
- highlight the entire inserted row green;
- write `NEW PIPE` or `NEW MANHOLE` in the master Notes field.

Generic unmatched fully printed IDs are not treated as suffix-new assets unless
they meet the structural rule. They retain Add / Ignore / Back review and must
not be silently fuzzy-corrected.

## Continuation pages and partial-page safety (v88+)

Pipe, Cleaning, and Manhole tables may continue onto headerless continuation
pages within the same work order.

- Pipe/Cleaning continuation pages reuse the preceding confirmed table geometry
  and orientation.
- Manhole continuations inherit the preceding Manhole table type/orientation and
  do not borrow Pipe/Cleaning column geometry.
- Faint/interrupted grid lines must not merge real columns.
- If one PDF page cannot be processed safely, analysis continues through later
  pages and keeps all readable rows.
- Skipped pages are reported as warning rows at the top of Live Summary.

For multi-page Pipe/Cleaning tables, only the **last continuation page** should
show/use the printed total-length crop. Do not ask for or validate one printed
total per page.

## Compact B&C faint/dashed row recovery (v95)

Some compact Brown & Caldwell tables use faint/interrupted horizontal row rules.
v95 adds a narrow recovery path when the normal compact-grid pass sees too few
horizontal rules to represent the physical rows.

The recovery reconnects/re-detects faint row separators, then reuses the existing
compact-table geometry/column recovery. Normal solid compact grids continue to
use the unchanged first pass.

Do not broaden this into a general table-parser rewrite.

## Manhole count verification

For Manhole work orders, the program asks the user to confirm the expected
Manhole count using the Description of Work crop and compares that expected
count against the parsed Manhole rows.

This is a user-confirmed count safeguard, separate from pair-table printed total
length validation.

## Split Pipe / MSA behavior

If exactly two Pipe rows in one work order represent the same Pipe as separate
parts:

- sum the two lengths;
- compare the combined length against the master expected length;
- make one combined update;
- preserve missing-part warnings;
- include `MSA DETECTED` in feedback.

Exactly two duplicate Pipe rows may be auto-combined. **Three or more duplicates
must not automatically be assumed to be an MSA split.** This applies to Pipe
video only, not Cleaning, Manholes, or rows from separate work orders.

## Physical-row and total safeguards

Preserve the row-retention and exact-number logic developed in v83-v89:

- confirmed physical data rows between header and total remain represented even
  when an endpoint/date requires review;
- Cleaning duplicate-looking rows remain available for total reconciliation while
  duplicate master writes are prevented;
- total OCR recovery may use OCR consensus/retries but must not manufacture or
  round a PDF value to match the master;
- header/title/printed-total rows never enter Live Summary or the master;
- compact-table fallback, length-total, zero-row, structural, duplicate,
  match-rate, and grid validations remain active.

## Review UI baseline (v90)

Unresolved Pipe/Cleaning rows show upstream/downstream PDF ID crops in the
Add-to-Master / Ignore flow; unresolved Manholes show the Manhole ID crop.
Editing a Live Summary row preserves the summary scroll position and selected /
focused row rather than jumping back to the top.

Manual edits to asset/node IDs are re-matched against the selected master and
update the row review state.

## Trouble Tickets.xlsx

Trouble Tickets are not part of the current PDF regression focus unless the user
specifically asks about them, but existing behavior must remain preserved.

- Create beside the selected master or append to the existing workbook.
- Back up an existing Trouble Tickets workbook before modifying it.
- Do not collapse separate tickets merely because they share an asset.
- Keep new issues/updates as separate adjacent history rows.
- Prevent only true duplicate page imports using the hidden stable source key.
- Primary column order begins with `Pipe/MH ID`, `Description`, `Status`,
  `Resolution / Follow-up Notes`, `Date`, `Work Order`, `Truck`, `Operator`,
  `Panel`, `Street`, `Area / Major Intersection`, followed by remaining fields.
- Operator also represents Reported By; there is no separate Reported By field.
- New rows default Status to `Open`; allowed values are Open, In Progress,
  Resolved, and No Action Needed.
- Keep the green workbook header and edit-field PDF previews.

## Current v95 fixes

1. **Faint/dashed compact-table row detection**
   - Recovers faint/interrupted horizontal row rules on the affected compact B&C
     table style instead of skipping the page.
   - Preserves normal compact-table behavior.
2. **Exact endpoint numeric-body priority**
   - Exact numeric-body matches outrank tolerated leading-junk matches.
   - Keeps both-endpoint evidence, unique directional pair, non-master, suffix,
     and ambiguity safeguards intact.

Current v95 regression scripts include:

- `regression_v95_faint_compact_rows.py`
- `regression_v95_exact_endpoint_priority.py`

They sit on top of the v94 stacked endpoint-digit recovery, v93 low-confidence
W/O and new-asset-note behavior, v92 4/5-digit W/O behavior, v91 color-aware W/O /
new-asset preview / conservative endpoint recovery, v90 review UI, v89 review /
count / final-total safeguards, v88 continuation handling, and the older active
regression baseline.

## Real-fixture expectations

Private customer PDFs/workbooks are local test fixtures and must never be
committed. Important known validation targets include packets from 8-19, 8-24,
8-26, and 8-28.

High-level expectations to preserve:

- 8-19 Cleaning: 11/11 rows, printed total 2296.
- 8-24 Manholes: 24/24.
- 8-24 Pipe page 4: 7 rows, total 2034.58.
- 8-24 Pipe page 6: 9 rows, total 2402.95.
- 8-24 Cleaning page 8: 10 rows, total 1207.
- 8-24 Cleaning pages 10-11: 33 combined rows, total 4430; page 11 is a
  3-row headerless continuation and only the final-page total is used.
- 8-24 page 13: 16 physical rows, total 2868.
- 8-26: Manholes 10/10; Pipe page 2 = 27 rows / 6720.58; Pipe page 4 =
  15 rows / 4198.37; Manholes page 6 = 10; Cleaning page 10 = 16 rows /
  4614; Pipe page 12 = 8 rows / 1700.
- 8-28 page 2 is the compact B&C faint/dashed-row failure specifically addressed
  by v95.

Exact customer documents remain private even when these expected counts/totals
are documented.

## Active regression expectations

Before publishing, the full active suite should pass, including the current
v95/v94/v93/v92/v91/v90/v89/v88/v87/v86/v85/v84/v83/v82 and older active
regressions, plus compact-table fallback, length totals, split pipes, new assets,
master insertion, R2 structural safeguards, and other still-active tests in
`working_source/tests/`.

A known CI limitation is that the private R2 fixture PDF may be unavailable on
the Linux runner. In that case exact fixture OCR is skipped, but structural R2
safeguards must still pass. Windows Excel COM and real Tkinter behavior also
cannot be fully exercised on the Linux runner. State those limitations instead
of claiming full platform validation.

## Automatic updates

At startup, the app reads the public `update_manifest.json`, offers a newer
release, downloads its ZIP, verifies SHA-256 and package contents, closes,
installs, rolls back on failure, and restarts. It preserves `.venv`, LocalAppData
settings, OCR caches, history, and layout profiles. Network failure must never
prevent the installed version from opening.

The manifest is changed only **after** a newly published release asset has been
re-downloaded and its public size/SHA verified.

## Development style

- Keep fixes narrow and targeted.
- Explain intended changes before modifying an important parsing/matching/write
  system.
- Preserve unrelated behavior, comments, review flows, and safeguards.
- Do not broadly refactor for cleanup alone.
- Do not weaken matching safeguards to make one fixture pass.
- Do not claim real PDF/OCR behavior is validated solely because code compiles or
  a static source assertion passes.
- Never commit private customer PDF/workbook fixtures.
