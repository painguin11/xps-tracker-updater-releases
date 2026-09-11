# XPS Tracker Updater release checklist

This checklist applies to the current **v102 production baseline**, the retained
`v95-work` safeguards, and all future releases. Do not publish unless
the user explicitly says `PUBLISH`.

Never overwrite an existing release/tag. If a published version needs a fix,
create the next version.

## Before changing release state

1. Confirm development is on the intended work branch (currently `v95-work`).
2. Read `AGENTS.md` and `PROJECT_CONTEXT.md`.
3. Confirm the requested code changes are complete and narrowly scoped.
4. Confirm no private customer PDF/workbook fixture has been added to Git.
5. Do not change the public `update_manifest.json` yet.

## Required build/version checks

1. Increment `APP_VERSION` in
   `working_source/app/reno_scan_updater.py`.
2. Increment `CURRENT_VERSION` in
   `working_source/app/xps_update.py`.
3. Update the bundled release README for the new version.
4. Compile both Python entry/update modules.
5. Confirm displayed/app/updater versions all match the intended release number.
6. Confirm unrelated Reno / Brown & Caldwell Year 15 / Phase 2 parsing and
   workbook logic was not removed.

## Full active regression suite

Run the full active regression suite under `working_source/tests/`, not only the
new test for the current fix.

The active baseline includes, at minimum:

- post-v97 Cleaning clipped-digit recovery regression;
- post-v96 editable MSA field / 8-26 OCR regression;
- post-v95 new-packet OCR/direction/total/layout regression;
- post-v95 padded complete endpoint-ID recovery regression;
- post-v95 MSA preview/reversal and NEW PIPE suffix-priority regression;
- v95 faint compact-table row recovery;
- v95 exact endpoint numeric-body priority;
- v94 stacked endpoint digit recovery;
- v93 low-confidence W/O blank behavior;
- v93 `NEW PIPE` / `NEW MANHOLE` Notes behavior;
- v92 4/5-digit W/O behavior;
- v91 color-aware W/O OCR;
- v91 new-asset preview and conservative endpoint recovery;
- v90 review UI behavior;
- v89 review workflow, printed-pair identity, Manhole count, and final-page total;
- v88 headerless continuation-page handling and partial-page safety;
- v87 total-separator behavior;
- v86 asset/node editing and endpoint safeguards;
- v85 edit previews and mandatory physical-row behavior;
- v84/v83 length and total-recovery behavior;
- v82 safeguards;
- older still-active v81-v73 regressions;
- compact-table fallback;
- length totals;
- split Pipe / MSA behavior;
- new assets;
- master insertion;
- R2 structural/canonicalization safeguards;
- Trouble Ticket tests when release scope could affect that path.

The following post-version-named regressions are already released and remain required:

- `working_source/tests/regression_post_v100_trouble_cells.py`
- `working_source/tests/regression_post_v100_826_trouble_geometry.py`
- `working_source/tests/regression_post_v99_faint_vertical_grid.py`
- `working_source/tests/regression_post_v98_short_wide_compact_table.py`
- `working_source/tests/regression_post_v97_cleaning_clipped_digits.py`
- `working_source/tests/regression_post_v96_msa_editable_fields.py`
- `working_source/tests/regression_post_v95_new_packet_ocr.py`
- `working_source/tests/regression_post_v95_msa_suffix_review.py`
- `working_source/tests/regression_post_v95_padded_endpoint_ids.py`

Do not delete or disable a regression simply because a new change conflicts with
it. Resolve the behavior intentionally.

## Important regression expectations

### Work Order OCR

- W/O text is machine-typed pink/magenta, not handwritten.
- Valid W/O values may be 4 or 5 digits.
- Pink/magenta isolation remains the primary OCR path.
- Clean/high-confidence values still prefill.
- Low-confidence values fail closed by opening the editable field blank.
- Conservative grayscale fallback remains available for desaturated scans.

### Matching / endpoint recovery

- Preserve full IDs, prefixes, hyphens, digit-bearing prefixes, and suffixes.
- `R2-280` must never become `R-2280`.
- Both endpoint cells must provide OCR/PDF numeric evidence before conservative
  pair recovery may use the master.
- Recovery must identify exactly one directional master pair.
- Complete printed upstream/downstream direction remains authoritative; a
  synthetic reverse-master lookup must not turn the opposite direction into an
  exact match.
- Exact numeric-body matches outrank tolerated leading-junk matches.
- True prefix ambiguity remains unresolved.
- Fully printed valid non-master pairs remain unresolved for Add/Ignore review.
- The master never supplies an endpoint that was not observed in the PDF.
- When complete printed endpoint evidence already resolves as `NEW PIPE`, R2,
  numeric-body, and slow OCR fallbacks must not erase the suffix before the
  existing independent suffix-confirmation path runs.
- A suffix that fails independent confirmation may still fall back conservatively;
  independently corroborated real suffix evidence must remain a NEW PIPE.
- Unresolved endpoint cells may use padded complete-ID recovery before lossy
  fallbacks, but a complete ID requires agreement from at least two independent
  OCR passes. The master may filter impossible prefixes only; it must never fill
  in a missing endpoint letter or digit.

### New assets

- Single-letter suffix detection remains possible.
- Suffixed NEW PIPE / NEW MANHOLE review shows the relevant PDF crop.
- Approved rows insert below the base asset when possible.
- The entire inserted row is highlighted green.
- Notes contain `NEW PIPE` or `NEW MANHOLE`.
- Generic unmatched printed IDs are not silently fuzzy-corrected.
- 8-24 page 4 is a key private real-fixture check for suffix handling; in
  particular `DN-2243S -> DN-2243 = 52` must remain a valid NEW PIPE.
- 8-28 page 4 is a key padded-complete-ID target: 21 physical Pipe rows must total
  3095.53 and printed suffixes such as `DN-2241A` / `DN-2242A` must survive.

### Continuation pages / totals

- Pipe, Cleaning, and Manhole tables may continue onto headerless pages within the
  same work order.
- Pipe/Cleaning continuations reuse the preceding confirmed geometry.
- Manhole continuations inherit the preceding Manhole type/orientation.
- Only the final page of a multi-page Pipe/Cleaning table supplies the printed
  total-length crop/validation.
- An unreadable page does not abort the whole PDF; later rows continue and a
  warning appears at the top of Live Summary.
- Faint/dashed compact B&C row rules remain recoverable without changing the
  normal solid-grid first pass.
- Faint interior vertical rules in a compact pair table may use the guarded post-v99 lighter-grid retry only after the established dark-grid passes fail; accepted rules must still satisfy the long-span/count/width evidence gates before row/header parsing.
- A compact table with usable column geometry but only a partial role mapping
  must enter the existing Layout Review instead of being skipped or crashing;
  only missing/unusable table geometry is an automatic skip.

### Manholes

- Manhole work orders request a user-confirmed expected count using the
  Description of Work crop.
- Parsed Manhole row count is checked against that expected count.

### Split Pipes / MSA

- Every Upstream ID, Downstream ID, and Length shown in MSA review must be editable.
- If corrected IDs no longer identify the same directed pipe, save the corrections and cancel MSA creation without merging.
- Manual MSA length corrections must not be overwritten by later OCR retries.
- 8-26 page 2 must preserve 84.48 + 82.87 and total 6720.58; 82.87 must not degrade to 2.87.
- Exactly two duplicate Pipe rows in one W/O may combine as an MSA split.
- Their lengths are summed and compared once to the master.
- Feedback includes `MSA DETECTED`.
- Three or more duplicates are not automatically treated as an MSA split.
- The MSA decision popup shows PDF crops for the Upstream ID, Downstream ID, and
  Length for both physical Pipe rows, plus combined/master/difference values.
- Choosing `Not MSA` remains a durable visible decision.
- A no-op Edit/Save must not silently clear `Not MSA`.
- Edit Selected must offer `Review / Change MSA Decision` for a rejected/pending
  reviewable two-row pair.
- If the user later confirms MSA, the rows combine and total validations are
  refreshed without requiring a new PDF analysis.

### Length / row integrity

- Difference threshold remains 4.5 ft.
- Over-threshold differences are highlighted red and produce an uppercase note.
- Header/title/printed-total rows never enter Live Summary or the master.
- Confirmed physical rows remain represented even when a field needs review.
- OCR/total recovery must not manufacture or round a PDF value to match master
  data.
- Cleaning disagreement handling retains competing batch/independent OCR as
  actual PDF observations; the master may break ties only between observed values.
- A clipped Cleaning digit may be restored only when the longer integer was
  observed by both stacked-column and independent row-cell OCR, the clipped token
  is a strict leading substring, and the master only breaks the tie between those
  PDF-observed candidates.
- A whole-table Pipe audit must not replace a currently valid measurement with a
  different OCR observation unless it improves printed-total mismatch and master
  plausibility, except when the new observation closes the printed total exactly.

## Private real-fixture checks

For the Trouble Ticket fixes released in v101, also run
`regression_post_v100_trouble_cells.py --fixtures /private/expected.json` against
the four B&C tickets and three older Consor/Reno tickets when available. Verify
complete IDs, all populated/blank fields, wrapped descriptions, small Pipe Size
values, dates, field previews, and edit/save identity. Keep the private fixture
expectations JSON out of Git and release packages. The default test uses only
synthetic forms and prints an explicit skip when private fixtures are not supplied.

Also retain `regression_post_v100_826_trouble_geometry.py`; when the private
8-26 packet is available, compare both ticket pages using detected cells.
The historical exclusion of Trouble Tickets from the older pair-table matrix
does not exclude these v101 ticket checks.

When local customer fixtures are available, run the applicable exact-PDF checks.
Known current fixture targets are documented in `PROJECT_CONTEXT.md` for the
8-19, 8-24, 8-26, and 8-28 packets.

The 8-28 page-2 compact B&C table is a key v95 real-PDF regression target.
The 8-24 packet is a key continuation/final-total/Manhole-count target, and page 4
is a key suffix-ID target. The 8-26 packet is a key two-part MSA plus total-reread
target. On 8-26 page 12, `DN-1789 -> DN-2305 = 34` and
`DN-2306 -> DN-887 = 54`, and the 8 Cleaning rows total 1700. The 8-28 page-4
table is a key complete-suffix-ID target.

The supplied 8-24, 8-26, and 8-28 private fixtures have passed the current
post-v95 source locally against the supplied Phase 2 Year 1 master, with Trouble
Tickets intentionally excluded from this test pass.


The current additional Phase 2 matrix must also preserve:

- 8-20 Manholes 20/20 and Cleaning 27 / 5690, including PDF-observed 56, 171,
  and 47 corrections.
- 8-21 Pipe page 2 = 22 / 6408.66 with 323.72 recovered and correct 250 not
  replaced by worse 260; Cleaning page 4 = 23 normal printed rows / 3926;
  Cleaning page 6 = 14 / 3724; Cleaning page 8 = 12 / 3180; Manholes page 10 =
  27/27. The known non-table anomaly on page 4 is excluded from this private
  fixture expectation only and must not create generic parser/filtering logic.
- 8-25 Pipe page 2 = 12 / 2803.46 and `R2-491 -> R2-489 = 53.22` remains NOT
  MATCHED; Cleaning page 4 = 5 / 1220; Cleaning page 6 = 20 / 4821 and
  `EC-1507 -> EC-1477 = 110` remains 110.
- 8-27 first Pipe = 34 / 5164.64; Manholes = 3/3; later Pipe = 9 / 2698.20;
  Cleaning = 12 / 3475 with production classification selecting the 90° table
  orientation.

These 8-20, 8-21, 8-25, and 8-27 private fixtures passed the current post-v95
source locally against the supplied Phase 2 Year 1 master. Trouble Tickets were
intentionally excluded from this matrix.

Private fixtures must remain local and must never be committed or packaged.

If a private fixture is unavailable on the CI runner, say so explicitly. Passing
structural tests does not equal passing real OCR.

## Platform limitations

Linux CI cannot fully exercise:

- Windows Excel COM write behavior;
- real Windows/Tkinter GUI interactions;
- some local Tesseract/private-fixture OCR paths.

Do not claim those paths were run when they were not.

## Package validation

1. Build `XPS_Tracker_Updater_vNN.zip` with one top-level
   `XPS_Tracker_Updater/` directory and the complete application contents.
2. Inspect release scope and package contents.
3. Explicitly confirm no customer/private `.pdf`, `.xlsx`, `.xls`, or `.xlsm`
   files are included or newly committed.
4. Run ZIP integrity testing.
5. Calculate and record the local ZIP SHA-256 and size.

## Publishing sequence

Only after every applicable check above passes or any unavoidable limitation is
clearly disclosed:

1. Publish a **new** GitHub release/tag `vNN` and upload
   `XPS_Tracker_Updater_vNN.zip`.
2. Verify the public release title/tag and asset name.
3. Download the **public release asset again**.
4. Verify the downloaded public asset size and SHA-256 against the expected local
   package.
5. Only after that verification succeeds, update the public `update_manifest.json`
   with:
   - the new version;
   - exact public release download URL;
   - exact verified SHA-256;
   - appropriate release notes.
6. Fetch/re-read the public manifest after the commit and verify version,
   download URL, and checksum.
7. Remove temporary publish workflow/trigger/bridge files created specifically
   for the release.
8. Confirm the development branch is clean of temporary release machinery and
   ready for the next change.

If public asset verification fails, **do not advance the manifest**.

## Current verified production reference

v102 is the current production release:

- Release commit: `0a868946652ef24372838c645857e53f83485e78`
- Asset: `XPS_Tracker_Updater_v102.zip`
- Size: `316053` bytes
- SHA-256: `ca2e64ce794eac5e685fb8bc60c050f7d70de0881e6f4f1fc32b08b8f5bbb994`
- Public manifest version/URL/SHA were re-read and verified after release asset re-download.
- 50/50 active Linux regression scripts passed on the versioned release source. Private fixture OCR and Windows Excel COM/live Tk GUI checks remain platform/fixture limitations rather than release-job coverage.

Previous verified production reference follows for history.

v101 was the previous production release:

- Release commit: `a32495b20d14783d4d0a54ac2ebcbbf2a715fd95`
- Asset: `XPS_Tracker_Updater_v101.zip`
- Size: `310270` bytes
- SHA-256: `dbf578af1bb8f01b937af9273bd1a4a872378ff751ec13a0c4c99763663d1003`
- Public manifest version/URL/SHA were re-read and verified after release asset re-download.

Previous verified production reference follows for history.

v100 was the previous production release:

- Release commit: `ab55fb90ceb833b5663f3561a1a2d86938ac0a93`
- Asset: `XPS_Tracker_Updater_v100.zip`
- Size: `306725` bytes
- SHA-256: `8737420f93bc9bda55fb3693c3231c163ff9881013660762685126788afc3fcd`

At the v100 release, the public updater manifest pointed to that verified asset; it now points to v101. The v100 safeguard adds a fail-closed lighter vertical-grid retry for compact B&C pair tables while preserving all v99-and-earlier safeguards.

## Documentation checks

Verify current production version, release asset/checksum, development branch,
and pending work agree across root docs, `working_source/docs/`, the bundled
README, and root docs on `main`. Check the production manifest on `main`, not
the historical copy on the development branch. Keep released safeguards out of
unreleased lists and distinguish prior fixture results from newly run checks.
Selective whole-work-order discard, problem-W/O exclusion during Update Master, and the enlarged Manhole count preview shipped in v102. Preserve those behaviors in future releases.
