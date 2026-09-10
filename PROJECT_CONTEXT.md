# XPS Tracker Updater project context

## Resume instructions

Repository: `painguin11/xps-tracker-updater-releases`

Current production version: **v99**.

Current development branch: **`v95-work`**.

The editable source and active regression suite are under `working_source/` on
`v95-work`. Start future work from that branch and preserve the v95 baseline plus
all documented unreleased `v95-work` safeguards. Do **not** publish another
version until the user explicitly says `PUBLISH`.


### Unreleased post-v99 faint vertical-grid safeguard

- Some image-only Phase 2 pair tables preserve clear horizontal rules while their interior vertical rules scan lighter than the established compact-grid threshold.
- The compact-grid parser now makes one guarded lighter vertical-rule retry only after both established dark-grid passes fail.
- The retry is accepted only when 5-20 long rules span at least 75% of the isolated table height and 70% of its width; normal row-rule, header-role, matching, and review safeguards remain unchanged.
- Permanent regression: `working_source/tests/regression_post_v99_faint_vertical_grid.py`.
- The supplied private fixture was used only for local diagnosis and was not committed or packaged.

Public v99 release:

- Tag: `v99`
- Release title: `XPS Tracker Updater v99`
- Release commit: `bd194969add8b762633d17859a3838712ec358d9`
- Asset: `XPS_Tracker_Updater_v99.zip`
- Asset size: `307138` bytes
- SHA-256: `71aadb56227a4b47290447b260b58bd6689b3c187715262f9cef85a3ecc0ce27`
- Very short Pipe and Cleaning pair tables use the narrow short-wide compact-grid path.
- Very short/one-row Manhole reports remain handled by the separate positioned-token parser.
- Permanent regression: `working_source/tests/regression_post_v98_short_wide_compact_table.py`.

Public v98 release:

- Tag: `v98`
- Release title: `XPS Tracker Updater v98`
- Release commit: `a9de8fc6a7edbb4e5b5eb6c38ba9faccbb40740f`
- Asset: `XPS_Tracker_Updater_v98.zip`
- Asset size: `306737` bytes
- SHA-256: `ce720bbaef5707b54da4ac99cd8170ba6da0c19aa9cbd64a3ea72aff7887675d`
- 8-26 Cleaning page 12 preserves 34 ft and 54 ft and totals 1700 ft.
- Permanent regression: `working_source/tests/regression_post_v97_cleaning_clipped_digits.py`.

Public v97 release:

- Tag: `v97`
- Release title: `XPS Tracker Updater v97`
- Release commit: `2e998a066abfe4b0026dd7e6046445ae9829abcf`
- Asset: `XPS_Tracker_Updater_v97.zip`
- Asset size: `305920` bytes
- SHA-256: `0853c74c082c05cf30f62fe86506a32a462dc4c7894ffe11eab272a37ec38494`
- `working_source/app/reno_scan_updater.py`: `APP_VERSION = '97'`
- `working_source/app/xps_update.py`: `CURRENT_VERSION = "97"`
- Public `update_manifest.json` points to that exact v97 asset/checksum.

### Current v97 release changes

- MSA review exposes editable Upstream ID, Downstream ID, and Length for both physical rows.
- Corrected IDs that diverge can be saved with `Save Changes & Cancel MSA`, preserving separate rows and normal re-matching.
- Manual MSA length corrections are protected from later OCR retries.
- The 8-26 page-2 fixture preserves 84.48 + 82.87 and totals 6720.58; page 4 remains 15 rows / 4198.37.
- OCR cache generation is v7 so stale v96 observations are not reused.
- Permanent regression: `working_source/tests/regression_post_v96_msa_editable_fields.py`.

### Unreleased post-v97 Cleaning clipped-digit safeguard

- 8-26 page 12 exposed two right-aligned Wheel Walk cells where the first pass
  retained clipped single digits and the whole-table audit could degrade both to 7.
- Printed `DN-1789 -> DN-2305` is **34 ft** and printed
  `DN-2306 -> DN-887` is **54 ft**; the page must finish at **8 rows / 1700**.
- Recovery is allowed only when the complete integer value was observed both in
  the earlier stacked-column OCR and an independent row-cell OCR pass, and the bad
  value is a strict leading substring of that longer observation.
- Master length may break a tie only among those independently PDF-observed
  candidates. It never supplies or manufactures a Cleaning measurement.
- Local real-PDF checks passed for 8-26 Cleaning page 10 = 16 / 4614 and page 12
  = 8 / 1700, plus the affected Cleaning regression matrix pages.
- Permanent regression: `working_source/tests/regression_post_v97_cleaning_clipped_digits.py`.

Public v96 release:

- Tag: `v96`
- Release title: `XPS Tracker Updater v96`
- Release commit: `e2212501d57f46105c05bde13cd8bb1e0b258ac5`
- Asset: `XPS_Tracker_Updater_v96.zip`
- Asset size: `303588` bytes
- SHA-256: `d8d65072fdcd902ccf736c112dcddc0bceffd9ab5d54451882cdc6b513ffa4dc`
- `working_source/app/reno_scan_updater.py`: `APP_VERSION = '96'`
- `working_source/app/xps_update.py`: `CURRENT_VERSION = "96"`
- Public `update_manifest.json` points to that exact v96 asset/checksum.

### Current v96 release changes

The following changes are included in public v96 and remain part of the required
baseline:

1. **MSA review previews and reversible decisions**
   - The MSA confirmation dialog shows both physical Pipe rows side by side.
   - Each part shows PDF previews for Upstream ID, Downstream ID, and Length,
     together with its PDF page.
   - The dialog also shows combined PDF length, master length, and difference.
   - Choosing `Not MSA` is a durable review decision instead of being silently
     cleared by a no-op Edit/Save.
   - A rejected/pending two-row MSA can be reopened from Edit Selected using
     `Review / Change MSA Decision`; confirming it later merges the two rows and
     revalidates totals without requiring the PDF to be analyzed again.
   - Live Summary explicitly marks rejected pairs with
     `NOT MSA — EDIT ROW TO CHANGE DECISION`.
2. **NEW PIPE suffix evidence outranks lossy endpoint fallbacks**
   - Once complete printed endpoint evidence resolves as `NEW PIPE`, the R2,
     numeric-body, and slow OCR fallbacks are not allowed to erase the suffix
     before the existing independent suffix-confirmation crop runs.
   - If the suffix does not survive that existing independent confirmation, the
     normal conservative fallback behavior may still resolve the unsuffixed
     existing master pair.
   - This protects real one-letter suffixes such as `DN-2243S` from being
     collapsed to a base asset merely because the numeric bodies match.
3. **Padded complete endpoint-ID recovery for damaged grid cells**
   - If the normal endpoint reads remain unresolved, each physical endpoint cell
     may be re-read with white padding before any lossy R2/numeric-body fallback.
   - A complete ID is accepted only when at least two independent OCR passes agree.
   - The selected master may filter impossible project prefixes, but it never
     supplies missing letters or digits.
   - Independently agreed complete IDs become authoritative evidence, so a real
     suffix such as `DN-2241A` / `DN-2242A` is not erased by numeric recovery.
   - The existing suffix/new-asset and ambiguity review rules still decide whether
     an observed ID is matched, NEW PIPE, or unresolved.
4. **Observed-value length reconciliation for new Phase 2 packets**
   - Cleaning mismatch recovery keeps batch and independent cell OCR as actual PDF
     observations; the master may break ties between observed values but never
     manufactures a measurement.
   - Targeted rereads remain limited to suspect/mismatch rows instead of rereading
     every Cleaning cell.
   - Pipe mismatch recovery includes the lower-scale alternate view that can
     recover values such as `323.72` when another view reads `393.72`.
   - A whole-table Pipe audit cannot replace an already-valid value with a different
     OCR observation unless the replacement reduces the printed-total mismatch and
     also improves master plausibility, unless it closes the printed total exactly.
5. **Digit-bearing R2 direction protection**
   - Explicit IDs such as `R2-491` retain the `R2` prefix instead of being parsed as
     prefix `R` plus numeric body `2491`.
   - Complete printed upstream/downstream direction is authoritative; a synthetic
     reverse-master alias cannot turn the opposite printed direction into an exact
     match.
6. **Compact partial-header review safety**
   - If table geometry/column boxes are detected but OCR maps only some required
     roles, the page enters the existing Layout Review instead of being skipped or
     raising a missing-role exception.
   - Only pages without usable table geometry are skipped as structurally unsafe.
7. **Faint compact row separators remain protected**
   - The v95 faint/interrupted separator recovery remains active and is covered by
     its permanent regression plus the new 8-25 real-PDF check.

Functional source commits for these changes:

- `4b11eb19824e6fc1d74840b8b75f6c27682ee21d` — reversible MSA review and suffix priority.
- `493ac60e249f7541014f8d61781b9bfa5ca64bc4` — padded complete endpoint-ID recovery.

Permanent regressions:

- `working_source/tests/regression_post_v95_msa_suffix_review.py`
- `working_source/tests/regression_post_v95_padded_endpoint_ids.py`
- `working_source/tests/regression_post_v95_new_packet_ocr.py`

The full active Linux regression suite passed after the padded-ID source commit.
The supplied private 8-24, 8-26, and 8-28 packets were also exercised locally
against the supplied Phase 2 Year 1 master with Trouble Tickets intentionally out
of scope. The key Pipe/Cleaning/Manhole counts, totals, MSA reconciliation,
continuation behavior, suffix IDs, and intentionally unresolved non-master pairs
matched the documented expectations below. The private R2 fixture remains
unavailable on Linux CI, so its structural safeguards passed while exact fixture
OCR was skipped.

Documentation-only and cleanup commits after a source change may advance the
`v95-work` branch head; they do not change the published v96 release commit above.

In a new conversation, begin with:

> Continue the XPS Tracker Updater project from the connected GitHub repository.
> Read AGENTS.md, PROJECT_CONTEXT.md, and RELEASE_CHECKLIST.md before changing
> anything. Start from v95-work, preserve the current v95 behavior and unreleased
> v95-work safeguards, and do not publish until I explicitly say PUBLISH.

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
through v90 and later review improvements.

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
- Complete printed `NEW PIPE` suffix evidence must be evaluated by the existing
  independent suffix-confirmation path **before** lossy numeric/R2/slow fallbacks
  may replace it with an unsuffixed master asset.

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
True ambiguities and fully printed non-master pairs remain unresolved. Numeric
body recovery must not override independently corroborated one-letter NEW PIPE
suffix evidence.

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

For MSA confirmation/review:

- show the actual PDF Upstream ID, Downstream ID, and Length crop for **both**
  physical rows;
- show combined PDF length, master length, and difference;
- `Not MSA` remains visible/durable and must not disappear merely because the row
  editor was opened and saved without changing identity;
- if the user changes their mind, Edit Selected must provide
  `Review / Change MSA Decision` for a reviewable two-row pair;
- confirming through that path combines the two records and revalidates total
  checks without requiring a fresh analysis.

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

## Review UI baseline

Unresolved Pipe/Cleaning rows show upstream/downstream PDF ID crops in the
Add-to-Master / Ignore flow; unresolved Manholes show the Manhole ID crop.
Editing a Live Summary row preserves the summary scroll position and selected /
focused row rather than jumping back to the top.

Manual edits to asset/node IDs are re-matched against the selected master and
update the row review state. Rejected/pending two-row MSA decisions are also
reviewable from Edit Selected as documented above.

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

Current unreleased regressions added on `v95-work`:

- `regression_post_v95_msa_suffix_review.py`
- `regression_post_v95_padded_endpoint_ids.py`

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
- 8-24 Pipe page 4: 7 rows, total 2034.58. This page includes legitimate
  letter-suffixed asset IDs and is a key real-PDF target for the unreleased
  suffix-priority fix; `DN-2243S -> DN-2243 = 52` must remain a valid NEW PIPE.
- 8-24 Pipe page 6: 9 rows, total 2402.95.
- 8-24 Cleaning page 8: 10 rows, total 1207.
- 8-24 Cleaning pages 10-11: 33 combined rows, total 4430; page 11 is a
  3-row headerless continuation and only the final-page total is used.
- 8-24 page 13: 16 physical rows, total 2868.
- 8-26: Manholes 10/10; Pipe page 2 = 27 physical rows / 6720.58 after
  two-part MSA reconciliation; Pipe page 4 = 15 rows / 4198.37 after targeted
  total reconciliation; Manholes page 6 = 10; Cleaning page 10 = 16 rows / 4614;
  Cleaning page 12 = 8 rows / 1700, including `DN-1789 -> DN-2305 = 34` and
  `DN-2306 -> DN-887 = 54`.
- 8-28 page 2: 18 Pipe rows, total 5006.09; this is the compact B&C faint/dashed
  row-grid failure specifically addressed by v95.
- 8-28 page 4: 21 physical Pipe rows, total 3095.53. Preserve complete printed
  suffix IDs including `DN-2241A` and `DN-2242A`; valid printed non-master pairs
  remain explicit review rows rather than being fuzzy-corrected.


Additional post-v95 Phase 2 packet expectations verified against the supplied
Phase 2 Year 1 master, with Trouble Tickets intentionally out of scope:

- 8-20 Manholes: 20/20.
- 8-20 Cleaning: 27 normal printed rows / 5690 exact; difficult printed values
  finish as 56, 171, and 47 from PDF-observed rereads.
- 8-21 Pipe page 2: 22 rows / 6408.66 exact. The difficult values include
  431.36, 300.95, 315.58, 168.86, 375.89, 323.72, and 325.89. An already-correct
  250 must remain 250 during the final whole-table audit rather than being
  replaced by a worse 260 observation.
- 8-21 Cleaning page 4: 23 normal printed rows / 3926. One known non-table anomaly
  in this private fixture is excluded from the fixture expectation only; it must
  not create a generic parser/filtering rule.
- 8-21 Cleaning page 6: 14 rows / 3724.
- 8-21 Cleaning page 8: 12 rows / 3180. Compact-header role detection/layout
  review must not crash or skip a detected table with usable column geometry.
- 8-21 Manholes page 10: 27/27.
- 8-25 Pipe page 2: 12 physical rows / 2803.46 exact. Printed
  `R2-491 -> R2-489 = 53.22` remains NOT MATCHED when the master only contains the
  opposite direction.
- 8-25 Cleaning page 4: 5 rows / 1220.
- 8-25 Cleaning page 6: 20 rows / 4821; `EC-1507 -> EC-1477` remains 110 rather
  than accepting the worse alternate OCR observation 1101.
- 8-27 first Pipe table: 34 rows / 5164.64.
- 8-27 Manholes: 3/3.
- 8-27 later Pipe table: 9 rows / 2698.20.
- 8-27 Cleaning table: 12 rows / 3475; production classification selects its 90°
  orientation and the total reconciliation corrects the observed 6 to the
  independently observed 96.

Exact customer documents remain private even when these expected counts/totals
are documented.

## Active regression expectations

Before publishing, the full active suite should pass, including
`regression_post_v95_new_packet_ocr.py`,
`regression_post_v95_msa_suffix_review.py`,
`regression_post_v95_padded_endpoint_ids.py`, and the current
v95/v94/v93/v92/v91/v90/v89/v88/v87/v86/v85/v84/v83/v82 and older active
regressions, plus compact-table fallback, length totals, split pipes, new assets,
master insertion, R2 structural safeguards, and other still-active tests in
`working_source/tests/`.

A known CI limitation is that private fixture PDFs may be unavailable on the
Linux runner. In that case exact fixture OCR is skipped, but structural safeguards
must still pass. Windows Excel COM and real Tkinter behavior also cannot be fully
exercised on the Linux runner. State those limitations instead of claiming full
platform validation.

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


## Released in v99: short-table safeguard

- Very short Brown & Caldwell pair tables can contain only a header, a few data
  rows, and a total, leaving the real table under the previous 12% page-height
  threshold after rotation even though it spans almost the full page width.
- The compact-grid candidate stage now admits that short shape only when the
  connected region spans at least 70% of page width and at least 5.5% of page
  height. Existing vertical-rule, horizontal-rule, column-count, header-role,
  matching, and review safeguards remain unchanged.
- Permanent synthetic regression:
  `working_source/tests/regression_post_v98_short_wide_compact_table.py`.
