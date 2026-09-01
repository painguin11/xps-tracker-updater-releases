XPS Tracker Updater
===================

Purpose
-------
Reads scanned Xpert Pipe Services work-order packets, shows every work-order
confirmation popup first, then reviews and writes matched rows to a selected
master tracking workbook. Trouble-ticket pages are extracted into a separate
Trouble Tickets.xlsx beside the selected master.

Supported project layouts
-------------------------
1. Reno master: Pipes and Manholes worksheets. The established v14 pipe-list
   reader is preserved for this layout.
2. Year 15 master: Year15Pipes and Year15Manholes worksheets. Supports:
   - Pipe video, matched by UP_MH and DN_MH
   - Manholes, matched by MH_ID
   - Cleaning, matched by UP_MH and DN_MH

For Year 15 cleaning, Wheel Walk, Date, W/O, Truck, and Operator are written
to the CLEAN section (columns I:M). Video values remain in the VIDEO section.
3. B&C Small Diameter Phase 2 Year 1 master: Pipes and Phase 2 Year 1
   Manholes worksheets. Supports full-prefix UP_MH/DN_MH matching, cleaning
   fields W WALK through OPERATOR (I:M), and PANO fields PANO LGTH through
   OPERATOR (N:R).

Run
---
Double-click setup_and_run.bat. The first run creates a private Python
environment and installs the required packages. Tesseract OCR must also be
installed on the Windows computer.

Workflow and safety
-------------------
1. Select the scanned PDF and master spreadsheet.
2. Click Analyze PDF.
3. Confirm W/O, operator, and truck in the back-to-back popups.
4. Review the extracted rows and statuses.
5. Click Update Master.

Before writing, the program creates a timestamped copy in a Backups folder.
Update logs and the processed-PDF registry are stored in a Logs folder. Pages
that are irrelevant or cannot be associated with a work order are reported.
Existing target data is never replaced without a confirmation prompt.

Trouble Tickets.xlsx is created automatically when needed. Later runs append
new tickets to the existing workbook, skip duplicates, and back up the existing
ticket workbook before saving. Trouble tickets appear in the extracted-row
review table and can be edited by double-clicking before Update Master is used.

Version 27 reliability fix
--------------------------
If Excel temporarily rejects a workbook-reading request while it is starting,
calculating, or loading an add-in, the updater now waits and retries instead of
immediately displaying the technical "Call was rejected by callee" error.

Version 28 performance improvement
----------------------------------
The master worksheets are now transferred from Excel in bulk and indexed in
memory. This replaces tens of thousands of individual cell-reading requests.
The updater also reuses that index when writing, avoiding a second full scan.

Version 29 Year 15 packet fixes
--------------------------------
- Corrected the Year 15 W/O, operator, and truck popup image crops.
- Added a portrait Manhole Number reader for the Year 15 manhole list.
- Made cleaning detection tolerant of OCR punctuation and "Wheel Wal" scans.
- Added color-aware reading for cyan-highlighted UP_MH and DN_MH values.
- Changed the pipe-length difference warning threshold from 3.0 to 4.5 feet.

Version 30 full asset matching
------------------------------
- Preserves complete manhole IDs, including prefix, hyphen, and letter suffix.
- Matches Year 15 pipe video and cleaning with complete UP_MH + DN_MH pairs.
- Number-only OCR is used only when it identifies exactly one full master ID.
- Ambiguous prefixes or suffixes are flagged for review instead of guessed.
- Cleaning keeps every detected table row visible, including unmatched rows.

Version 31 multi-computer setup fix
-----------------------------------
- Detects Tesseract in both Program Files and the current user's LocalAppData.
- Rechecks immediately after winget installs Tesseract, preventing repeat installs.
- Automatically removes and rebuilds a copied or stale .venv that points to
  Python on a different computer or Windows user profile.

Version 32 Phase 2 Year 1 master support
-----------------------------------------
- Recognizes the Pipes and Phase 2 Year 1 Manholes sheet names.
- Maps Sewer_ID, UP_MH, DN_MH, W WALK, and PANO LGTH headers.
- Preserves full-prefixed pipe endpoints and manhole IDs.
- Keeps the Reno and earlier Year 15 project profiles unchanged.

Version 33 dynamic table columns and launcher
---------------------------------------------
- Detects UP_MH, DN_MH, Wheel Walk/video length, and Date columns from each
  scanned table's printed headers instead of assuming one fixed column order.
- Installs Python packages only when the environment is new or needs repair.
- Creates a desktop shortcut named XPS Tracker Updater.
- The shortcut uses the lightweight run_xps_tracker.bat launcher for normal use.

Version 34 faster unhighlighted cleaning lists
------------------------------------------------
- Uses a focused grayscale/threshold OCR path for future unhighlighted cleaning
  tables instead of running multiple color-isolation passes on every cell.
- Retains dynamic header-based columns and full-prefix UP_MH + DN_MH matching.
- Leaves the Reno, pipe-video, and manhole readers unchanged.

Version 35 uppercase master entries
-----------------------------------
- Normalizes all text at the Excel-writing boundary.
- Writes W/O, Truck, and Operator in uppercase for cleaning, pipe video, and
  manhole updates regardless of OCR or manual-entry capitalization.
- Writes newly added length-difference notes in uppercase.

Version 36 strict dynamic asset columns
---------------------------------------
- Tries multiple possible header bands and OCR modes to locate UP_MH, DN_MH,
  Wheel Walk/video length, and Date cells.
- Recognizes common scans such as UP_MA, DN_NH, and Wheel Wal.
- Removes the unsafe fixed-column fallback for pair-based project tables.
- If required headers cannot be resolved, shows COLUMN HEADERS NOT RESOLVED
  and blocks updates from that page instead of creating false asset names.

Version 37 universal work-order OCR and custom icon
---------------------------------------------------
- Uses value-only W/O crops and weighted OCR agreement for every project.
- Reads the supplied 12055 work order without letting a broad 49055 result win.
- Removes Operator, Perator, Erator, and Rator label fragments from names.
- Applies the same work-order rules to Reno, Year 15, and Phase 2 projects.
- Includes a multi-resolution XPS Tracker Updater icon for the desktop shortcut
  and optional EXE build.

Version 38 vertical-grid table detection
----------------------------------------
- Finds the full list table from long vertical grid rules before reading headers.
- Rejects repeated text strokes that do not remain dark through most table rows.
- Uses the detected grid boundaries to crop every header cell separately.
- Handles faint or broken upper horizontal rules without starting in a data row.
- Expands the true header crop upward so UP_MH and DN_MH are not clipped.

Version 39 cleaning length warnings
-----------------------------------
- Compares Wheel Walk with the matched pipe Length from the master.
- Uses the same 4.5-foot review threshold as pipe-video length checks.
- Shows LENGTH DIFF (WHEEL WALK) in a red review row.
- Recalculates the warning after manual Wheel Walk edits.
- Highlights the Wheel Walk master cell red and appends an uppercase Notes
  warning when the selected project master contains a Notes column.

Version 40 popup wording
------------------------
- Changes the confirmation popup label from Master operator to Operator.

Version 41 universal layout, confidence, cache, and validation
--------------------------------------------------------------
- Shows a layout confirmation screen before asset-row processing for every
  unique pipe or cleaning table format in the selected PDF.
- Allows correction of UP_MH, DN_MH, activity value, and activity date columns.
- Saves confirmed mappings by table-layout fingerprint and preselects them when
  the same format appears in a future PDF on that computer.
- Scores sampled endpoint-column pairs against valid pairs in the selected
  master when header OCR is incomplete.
- Tests grid/master evidence on an initially unclassified page after a work
  order so a damaged table title does not automatically cause the page to be ignored.
- Runs fast OCR first and escalates only unmatched, missing, or implausible cells.
- Caches rendered PDF pages plus Tesseract results by exact PDF fingerprint,
  crop pixels, and OCR settings under the current user's LocalAppData folder.
- Reuses cached page images and OCR on later runs of the same unchanged PDF.
- Validates printed row totals when present, duplicates, master-match rate,
  detected grid size, zero-row pages, and unexpected table structures.
- Reports page-level validation warnings without silently treating them as success.

Version 42 learned truck and operator values
--------------------------------------------
- Uses Truck and Operator values already present in the selected master as
  gentle OCR hints for every supported project type.
- Remembers the full operator names and truck codes confirmed in successful
  updates on that computer, even when a future project starts with a blank master.
- Uses frequency only to break close OCR matches; unrelated handwriting is never
  replaced merely because a name or truck was used often.
- Saves learned values only after Excel confirms that the master was saved.

Version 43 live analysis summary
--------------------------------
- Adds each completed asset row to the summary as soon as it is extracted.
- Keeps the newest row visible and shows a running count during PDF processing.
- Refreshes rows after packet-wide duplicate validation so late warnings remain accurate.

Version 44 true row-by-row summary updates
------------------------------------------
- Moves live summary updates inside each project's row-extraction loop.
- Reno, Year 15, and Phase 2 now publish pipe, cleaning, and manhole rows as
  soon as each row finishes OCR and master matching.
- Fixes long single-page Reno lists appearing all at once only after analysis.

Version 45 readable status and warning summaries
------------------------------------------------
- Places status and warning details on a dedicated full-width line below the buttons.
- Automatically wraps long messages as the program window is resized.
- Allows the complete analysis summary, validation counts, and OCR cache details
  to remain visible instead of being clipped at the right edge.

Version 46 forced live screen painting
--------------------------------------
- Processes a complete Windows/Tkinter event cycle after every summary-row insertion.
- Prevents native screen painting from remaining queued while the next OCR row runs.
- Keeps row-by-row updates visibly incremental across all supported projects.

Version 47 Consor printed-count validation
------------------------------------------
- Reads Consor pipe counts beside "Number of surveys in this."
- Reads Consor manhole counts beside "Report Survey Count."
- Skips printed-count validation for cleaning reports because those reports do
  not provide a count for this purpose.
- Accepts the count on either side of its label because rotated-page OCR can
  reverse their text order.
- Rejects digits embedded in comma-formatted or decimal lengths, preventing
  7,106.2 feet from being misreported as a printed count of 7.

Version 48 project-aware count validation
-----------------------------------------
- Runs printed-count validation only for Consor/Reno pipe and manhole reports.
- Skips printed-count validation for all Brown and Caldwell Year 15 and Phase 2
  pipe, cleaning, and manhole reports because those formats do not provide an
  applicable total count.
- Continues match-rate, duplicate, grid, zero-row, and length validation on
  Brown and Caldwell reports.

Version 49 simplified user-facing summary
-----------------------------------------
- Removes OCR cache hit/miss counters from the visible analysis summary.
- Keeps persistent OCR and rendered-page caching fully enabled in the background.
- Leaves the summary focused on update rows, work orders, ignored pages, and
  warnings that may require user action.

Version 50 branded interface refresh
------------------------------------
- Replaces Tkinter's feather with the included XPS Tracker Updater icon on the
  main window, taskbar entry, confirmation dialogs, and edit window.
- Adds a branded header, cleaner source-file panel, clearer primary actions,
  improved spacing, modern colors, and a dedicated status panel.
- Improves table headers, row height, selection colors, and visual grouping
  while keeping the existing Analyze, review, and Update Master workflow.

Version 51 streamlined controls and cancellation
------------------------------------------------
- Removes the large XPS Tracker Updater title and subtitle banner from the top.
- Opens the same row editor when an extracted row is double-clicked or selected
  and Edit Selected is clicked.
- Adds Cancel Current Process during analysis and checks for cancellation between
  pages and individual row OCR attempts across every supported project type.
- Clears partial rows after cancellation so incomplete results cannot be updated.
- Clears the Extracted rows section immediately when a different PDF is selected.

Version 52 animated analysis control
------------------------------------
- Animates the Analyze button through "Analyzing" dot frames while OCR is active.
- Keeps the button at a fixed width so surrounding controls do not move.
- Disables repeated Analyze clicks during processing and restores the normal
  button text after success, cancellation, or an input error.

Version 53 scanline analysis animation
--------------------------------------
- Keeps the "1. Analyze PDF" text fixed and stationary throughout processing.
- Replaces the changing dot text with a cyan scanline moving horizontally back
  and forth across the blue Analyze button.
- Uses time-based motion so the scanline resumes at the correct position after
  a long OCR operation temporarily delays screen refreshes.

Version 54 scanline startup fix
-------------------------------
- Fixes the custom Analyze button overwriting Tkinter's reserved `_w` widget
  command attribute, which caused `invalid command name "145"` at startup.
- Uses non-reserved width and height fields while preserving the same scanline effect.

Version 55 Analyze-button progress fill
---------------------------------------
- Replaces the moving scanline with a gradual left-to-right button fill.
- Advances the fill at real processing checkpoints, so a pause reflects difficult
  OCR work instead of making a decorative animation appear laggy.
- Keeps the button label fixed and resets the fill when processing ends or is cancelled.

Version 56 visible application version
--------------------------------------
- Shows "XPS Tracker Updater v56" in the Windows title bar.
- Defines the application name and version separately so future builds can update
  the displayed version from one consistent location.

Version 59 native-DPI icons
---------------------------
- Declares per-monitor DPI awareness before Tkinter creates the window.
- Supplies every native ICO layer to Tkinter instead of letting iconbitmap
  choose and stretch a single layer.

Version 58 taskbar icon clarity
-------------------------------
- Uses a separate, clean hard-edged X icon for the title bar and taskbar.
- Keeps the full detailed XPS artwork for the desktop shortcut.
- Avoids shrinking glow, text, and fine artwork into Windows' tiny UI icon sizes.

Version 57 small-icon clarity
-----------------------------
- Rebuilds the ICO with native 16, 20, 24, 32, 40, 48, 64, 128, and 256 pixel layers.
- Uses a tightly framed XPS "X" mark for small title-bar and taskbar layers instead
  of shrinking the detailed full desktop artwork into unreadable pixels.
- Keeps the full supplied artwork for the larger desktop and shortcut layers.
- Uses a versioned Windows application identity so a stale taskbar icon is not reused.

Version 60 trouble-ticket tracking
----------------------------------
- Extracts every labeled field from Consor trouble-ticket pages instead of
  treating those pages as ignored.
- Shows trouble tickets live in the review table and supports double-click editing.
- Creates Trouble Tickets.xlsx beside the selected master, or appends to the
  existing workbook while preserving prior rows.
- Stores ticket date, reporter, pipe ID, location, service type, manholes,
  dimensions, description, confirmed work-order context, and source PDF/page.
- Uses a hidden stable ticket key to prevent duplicate rows on repeated runs.
- Creates a timestamped backup before changing an existing Trouble Tickets.xlsx.

Version 61 trouble-ticket history grouping
------------------------------------------
- Identifies duplicates by the actual scanned ticket page instead of pipe/manhole
  number or issue wording.
- Keeps new issues and follow-up tickets even when they concern the same asset or
  repeat much of a previous description.
- Inserts each new same-asset ticket immediately below that asset's existing
  ticket history instead of placing it at the unrelated end of the workbook.
- Migrates v60 duplicate keys when an existing Trouble Tickets.xlsx is first used.

Version 62 trouble-ticket tracker layout
----------------------------------------
- Uses one Operator field for both the ticket reporter and operator value.
- Renames Pipe ID to Pipe/MH ID and places the primary tracking fields first.
- Adds manual Status and Resolution / Follow-up Notes columns.
- Gives Status an Excel dropdown with Open, In Progress, Resolved, and
  No Action Needed; new tickets default to Open.
- Keeps Area / Major Intersection as the full location header.
- Changes the Trouble Tickets.xlsx header bar from blue to green.
- Automatically migrates v60/v61 ticket workbooks to the new layout while
  preserving all rows, source details, and hidden duplicate keys.

Version 63 split-pipe surveys
-----------------------------
- Allows the same pipe to appear on multiple video rows within one work order.
- Adds the surveyed lengths from all parts before comparing against the master.
- Writes one combined pipe update to the master instead of discarding later parts.
- Shows MSA DETECTED and the number of combined parts in the review feedback.
- Keeps missing part lengths visible for review rather than accepting a partial total.
- Does not change duplicate handling for cleaning rows, manholes, or separate work orders.

Version 64 new suffixed assets
------------------------------
- Recognizes a new manhole only when its ID is an existing master manhole ID plus
  exactly one trailing letter, such as DE-1234A when DE-1234 already exists.
- Recognizes a new pipe when either or both printed endpoints are new suffixed
  manholes, such as DE-1234A -> DE-1235 or DE-1234A -> DE-1235B.
- Preserves the complete printed IDs and shows NEW MANHOLE or NEW PIPE in feedback.
- Requests approval before adding each detected new asset to the master.
- Approved assets are inserted directly below their base manhole or pipe row,
  receive the current survey data, and are highlighted green across the row.
- Declined assets remain skipped and are labeled NOT APPROVED in feedback.
- Never substitutes or overwrites the nearest existing master asset.
- Keeps ordinary OCR correction and unmatched/ambiguous handling for IDs that do
  not follow the trailing-letter rule.

Version 65 automatic update foundation
--------------------------------------
- Checks a configured HTTPS release manifest before normal startup.
- Offers Update Now or Later only when a newer version is available.
- Downloads the release ZIP and verifies its SHA-256 checksum before installation.
- Verifies the version and required program files inside the downloaded package.
- Installs only after the current program has closed, then restarts automatically.
- Preserves the Python environment and all Local AppData settings, OCR caches,
  history, and layout profiles.
- Creates a program-file backup and restores it automatically if installation fails.
- Continues opening the installed version if the internet or update server is down.
- Does not update during PDF analysis or while an Excel workbook is being saved.
- Uses the official public release feed at:
  https://github.com/painguin11/xps-tracker-updater-releases

Version 68 R2 IDs and cleaning lengths
- IDs with digit-bearing prefixes retain their original structure (for example, R2-280 no longer becomes R-2280).
- Questionable Wheel Walk values are re-read with several border-free crops.
- OCR consensus selects the printed value; the master length is used only to break equal OCR votes.
- New crop pixels prevent stale border-touching OCR results from controlling corrected rows.

Version 69 R2 endpoint OCR recovery
-----------------------------------
- Re-reads unresolved R2 endpoint cells with a border-free, R2-focused OCR pass.
- Recovers scan artifacts such as 32-427, 2-417, and R2-414 followed by a grid-rule character.
- Accepts a recovered ID only when the complete endpoint already exists in the selected master and the full upstream/downstream pair matches one master pipe.
- Preserves joined one-letter suffixes such as R2-414A and R2-414S as possible new assets instead of reducing them to the base ID.
- Verified 8-17-2026(1).pdf as R2-427 -> R2-414 and R2-417 -> R2-427.

Version 67 work-order preview
- The confirmation popup now displays a wider, dedicated Work Order crop.
- The complete handwritten work-order number remains visible even when OCR uses a tighter crop.
- Work-order OCR and all extraction behavior are unchanged.
- Fallback table layouts no longer display a false blank Column 1.
- The final Cleaning Date column now appears as the tenth mapping option.

Version 66 tall cleaning-table headers
--------------------------------------
- Recognizes cleaning pages when Wheel, Walk, Cleaning, and Date are separated
  by OCR reading order inside a tall wrapped header.
- Allows one taller leading table-header band while retaining the stricter
  data-row limits everywhere else.
- Keeps ordinary-height cleaning, pipe, and manhole layouts unchanged.


Version 70 layout confidence, DPI, and cleaning headers
------------------------------------------------------
- Skips the PDF table-layout confirmation popup when native detection is 100%
  confident and all four required column roles are present.
- Makes the main UI DPI-aware so buttons, summary rows, and summary columns keep
  readable proportions on computers using different Windows display scaling.
- Allows Asset / Nodes and Status to use extra window width while retaining the
  horizontal scrollbar on smaller displays.
- Preserves confidently recognized partial table-header roles instead of
  discarding them when one role is missing.
- For B&C cleaning tables, recognizes the final Date column plus an immediately
  preceding Length-labelled column as Cleaning Date and Wheel Walk when OCR
  splits the narrow printed headers.


Version 71 length-total validation
----------------------------------
- Reads the printed PDF activity total independently from the individual row
  lengths and reconciles it against the lengths shown in the live summary.
- A mismatch is a blocking validation failure: affected rows are dark red and
  Update Master remains blocked until the totals reconcile.
- If the printed total itself was OCRed incorrectly, the user can enter the
  total they visually verify from the PDF; this changes only the expected PDF
  total and never changes an individual row length.
- Editing an extracted length automatically recalculates its work-order/activity
  total validation.
- Cleaning-length OCR now escalates to the border-free focused reread when the
  first OCR result is blank or contains only impossible values, closing cases
  such as a printed 114 being read initially as 6114/36114.
