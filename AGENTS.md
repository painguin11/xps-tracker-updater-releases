# XPS Tracker Updater agent instructions

Before modifying this project, read `PROJECT_CONTEXT.md` and
`RELEASE_CHECKLIST.md` completely.

## Current baseline

- Production version: **v95**.
- Development branch: **`v95-work`**.
- The authoritative editable source is under `working_source/` on the development
  branch. Preserve all documented v95 behavior unless the user explicitly asks
  to change it.
- Do **not** publish a new release unless the user explicitly says `PUBLISH`.

Keep changes narrowly scoped and preserve unrelated behavior. Do not broadly
refactor OCR, matching, table parsing, review UI, workbook writes, or update logic
just to fix one fixture. Never weaken a fail-closed safeguard merely to make a
single regression pass.

Real PDF/OCR behavior matters more than static assertions. Never describe a build
as validated merely because it compiles; run the applicable regression checks
and clearly state which real-fixture, Windows Excel COM, Tkinter, or OCR checks
could not run in the current environment.

Do not change Operator/Truck OCR unless the user specifically asks for it.

## Release rules

For every release, and only after an explicit `PUBLISH` instruction:

1. Increment `APP_VERSION` in `working_source/app/reno_scan_updater.py` and
   `CURRENT_VERSION` in `working_source/app/xps_update.py`.
2. Update the bundled release README.
3. Compile and run the full active regression suite.
4. Validate release scope and confirm unrelated Reno/Year 15/Phase 2 behavior
   remains present.
5. Package the complete app as `XPS_Tracker_Updater_vNN.zip`.
6. Confirm no private/customer `.pdf`, `.xlsx`, `.xls`, or `.xlsm` files are in
   the package or release commit.
7. Test ZIP integrity and calculate its SHA-256.
8. Publish a new tag/release. Never overwrite an already-published version/tag.
9. Download the public release asset again and verify its name, size, and SHA-256.
10. Only after public asset verification, update `update_manifest.json` with the
    exact public URL and checksum.
11. Re-read the public manifest and verify version, URL, and SHA-256.
12. Remove temporary publish workflow/trigger files created for that release.

Do not upload customer PDFs, master workbooks, operator names, work-order
documents, OCR caches, generated Trouble Tickets workbooks, logs, or other
company data to this public repository.
