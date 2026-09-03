from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
UPDATER=Path('working_source/app/xps_update.py')
README=Path('working_source/app/README_XPS_Tracker_Updater.txt')
V91_WO=Path('working_source/tests/regression_v91_workorder_color_ocr.py')
V92_WO=Path('working_source/tests/regression_v92_workorder_4_or_5_digits.py')
V93_WO=Path('working_source/tests/regression_v93_workorder_low_confidence_blank.py')
V93_NOTES=Path('working_source/tests/regression_v93_new_asset_notes.py')

app=APP.read_text(encoding='utf-8')
assert "APP_VERSION = '92'" in app
assert app.count("append_note(ps.Cells(rr,notes_col),'NEW PIPE')")==2
assert app.count("append_note(ms.Cells(rr,notes_col),'NEW MANHOLE')")==2
assert 'def _workorder_confident_magenta_candidate' in app
assert "elif magenta_seen:\n        wo=''" in app
app=app.replace("APP_VERSION = '92'","APP_VERSION = '93'",1)
APP.write_text(app,encoding='utf-8')

updater=UPDATER.read_text(encoding='utf-8')
assert 'CURRENT_VERSION = "92"' in updater
updater=updater.replace('CURRENT_VERSION = "92"','CURRENT_VERSION = "93"',1)
UPDATER.write_text(updater,encoding='utf-8')

readme=README.read_text(encoding='utf-8').rstrip()+"\n"
if 'Version 93 low-confidence W/O and new-asset notes' not in readme:
    readme += '''\n\nVersion 93 low-confidence W/O and new-asset notes\n--------------------------------------------------\n- Leaves the Work Order confirmation field blank when pink/magenta W/O ink is present but too faded, incomplete, or inconsistent for a trustworthy 4- or 5-digit read.\n- Requires strong agreement across the isolated-color OCR passes plus the expected visible digit structure before auto-filling a Work Order number.\n- Does not let the grayscale fallback override a low-confidence pink/magenta read; grayscale is reserved for scans where the color signal is genuinely absent/desaturated.\n- Writes NEW PIPE in the master Notes column for every approved new pipe row, including Add to Master rows.\n- Writes NEW MANHOLE in the master Notes column for every approved new manhole row, including Add to Master rows.\n- Preserves the v92 4/5-digit Work Order support and all prior matching, continuation, new-asset, total-validation, and review safeguards.\n'''
README.write_text(readme,encoding='utf-8')

# Historical regressions must accept the newer release version while continuing
# to test the behavior introduced in their original versions.
t=V91_WO.read_text(encoding='utf-8')
t=t.replace("r\"APP_VERSION = '(?:91|92)'\"","r\"APP_VERSION = '(?:91|92|93)'\"")
V91_WO.write_text(t,encoding='utf-8')

t=V92_WO.read_text(encoding='utf-8')
t=t.replace("assert \"APP_VERSION = '92'\" in s","assert re.search(r\"APP_VERSION = '(?:92|93)'\",s)")
V92_WO.write_text(t,encoding='utf-8')

t=V93_WO.read_text(encoding='utf-8')
t=t.replace("assert \"APP_VERSION = '92'\" in s  # dev branch remains on production version until publish","assert \"APP_VERSION = '93'\" in s")
V93_WO.write_text(t,encoding='utf-8')

t=V93_NOTES.read_text(encoding='utf-8')
t=t.replace("assert \"APP_VERSION = '92'\" in s  # development branch stays on production version until publish","assert \"APP_VERSION = '93'\" in s")
V93_NOTES.write_text(t,encoding='utf-8')

print('Applied v93 release version bump, README notes, and regression version updates.')
