# XPS Tracker Updater release checklist

This checklist applies to the current **v95 baseline** and all future releases.
Do not publish unless the user explicitly says `PUBLISH`.

Never overwrite an existing release/tag. If a published version needs a fix,
create the next version.

## Before changing release state

1. Confirm development is on the intended work branch (currently `v95-work`).
2. Read `AGENTS.md` and `PROJECT_CONTEXT.md`.
3. Confirm the requested code changes are complete and narrowly scoped.
4. Confirm no private customer PDF/workbook fixture has been added to Git.
5. Do not change `update_manifest.json` yet.

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
- Exact numeric-body matches outrank tolerated leading-junk matches.
- True prefix ambiguity remains unresolved.
- Fully printed valid non-master pairs remain unresolved for Add/Ignore review.
- The master never supplies an endpoint that was not observed in the PDF.

### New assets

- Single-letter suffix detection remains possible.
- Suffixed NEW PIPE / NEW MANHOLE review shows the relevant PDF crop.
- Approved rows insert below the base asset when possible.
- The entire inserted row is highlighted green.
- Notes contain `NEW PIPE` or `NEW MANHOLE`.
- Generic unmatched printed IDs are not silently fuzzy-corrected.

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

### Manholes

- Manhole work orders request a user-confirmed expected count using the
  Description of Work crop.
- Parsed Manhole row count is checked against that expected count.

### Split Pipes / MSA

- Exactly two duplicate Pipe rows in one W/O may combine as an MSA split.
- Their lengths are summed and compared once to the master.
- Feedback includes `MSA DETECTED`.
- Three or more duplicates are not automatically treated as an MSA split.

### Length / row integrity

- Difference threshold remains 4.5 ft.
- Over-threshold differences are highlighted red and produce an uppercase note.
- Header/title/printed-total rows never enter Live Summary or the master.
- Confirmed physical rows remain represented even when a field needs review.
- OCR/total recovery must not manufacture or round a PDF value to match master
  data.

## Private real-fixture checks

When local customer fixtures are available, run the applicable exact-PDF checks.
Known current fixture targets are documented in `PROJECT_CONTEXT.md` for the
8-19, 8-24, 8-26, and 8-28 packets.

The 8-28 page-2 compact B&C table is a key v95 real-PDF regression target.
The 8-24 packet is a key continuation/final-total/Manhole-count target.

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
5. Only after that verification succeeds, update `update_manifest.json` with:
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

v95 is the current production release:

- Release commit: `427bf94939484ed7aa19d05a6a9166893d190b75`
- Asset: `XPS_Tracker_Updater_v95.zip`
- Size: `298928` bytes
- SHA-256: `eb4e816b010d7cf8730e97ad83acc40bc502f6f175085d49c13fce891999be41`

The public updater manifest points to that verified v95 asset.
