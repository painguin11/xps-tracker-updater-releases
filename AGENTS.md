# XPS Tracker Updater agent instructions

Before modifying this project, read `PROJECT_CONTEXT.md` and
`RELEASE_CHECKLIST.md` completely.

The current production source and regression scripts are in the versioned source
bundle stored with this repository. Extract it before editing. Keep changes
narrowly scoped and preserve unrelated behavior. Never describe a build as
validated merely because it compiles; run the applicable regression checks and
clearly state which fixture-based checks could not run.

For every release:

1. Increment `APP_VERSION` in `app/reno_scan_updater.py` and `CURRENT_VERSION`
   in `app/xps_update.py`.
2. Update the bundled README and package the complete `app/` directory.
3. Run the release checklist.
4. Publish the ZIP as a GitHub release asset.
5. Only after the release asset is public and its SHA-256 is verified, update
   `update_manifest.json`.

Do not upload customer PDFs, master workbooks, operator names, work-order
documents, OCR caches, or generated Trouble Tickets workbooks to this public
repository.
