from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
UPDATER=Path('working_source/app/xps_update.py')
README=Path('working_source/app/README_XPS_Tracker_Updater.txt')
V91_WO=Path('working_source/tests/regression_v91_workorder_color_ocr.py')
V92_WO=Path('working_source/tests/regression_v92_workorder_4_or_5_digits.py')
V93_WO=Path('working_source/tests/regression_v93_workorder_low_confidence_blank.py')
V93_NOTES=Path('working_source/tests/regression_v93_new_asset_notes.py')

app=APP.read_text(encoding='utf-8')
assert "APP_VERSION = '93'" in app
assert 'def _batch_pair_endpoint_digit_candidates' in app
assert 'up_extra=batch_up_digit_endpoints.get(band_index,[])' in app
assert 'dn_extra=batch_dn_digit_endpoints.get(band_index,[])' in app
assert 'def _resolve_pipe_pair_from_endpoint_digits' in app
app=app.replace("APP_VERSION = '93'","APP_VERSION = '94'",1)
APP.write_text(app,encoding='utf-8')

updater=UPDATER.read_text(encoding='utf-8')
assert 'CURRENT_VERSION = "93"' in updater
updater=updater.replace('CURRENT_VERSION = "93"','CURRENT_VERSION = "94"',1)
UPDATER.write_text(updater,encoding='utf-8')

readme=README.read_text(encoding='utf-8').rstrip()+"\n"
if 'Version 94 padded endpoint-cell recovery' not in readme:
    readme += '''\n\nVersion 94 padded endpoint-cell recovery\n----------------------------------------\n- Adds a fallback for Brown & Caldwell pair tables where whole-column OCR skips an otherwise clean endpoint row.\n- Builds a clean synthetic endpoint column by cropping each physical endpoint cell, adding white padding, and stacking the cells before digit-only OCR.\n- Runs the stacked-cell pass only after normal endpoint matching has already failed, avoiding extra OCR work on rows that are already readable.\n- Uses only numeric bodies actually observed from each PDF endpoint cell; the master is never allowed to supply a missing endpoint number.\n- Resolves a damaged row only when both observed endpoint numbers identify exactly one existing directional master pipe.\n- Keeps valid non-master pairs such as DN-777 -> DN-1762 and DN-1698 -> DN-1697 unresolved for Add/Ignore review instead of force-matching them.\n- Preserves all v93 and earlier Work Order, new-asset, continuation, total-validation, R2, split-pipe, and review safeguards.\n'''
README.write_text(readme,encoding='utf-8')

# Historical regressions keep testing the behavior introduced in their original
# versions while accepting the newer release version.
t=V91_WO.read_text(encoding='utf-8')
t=t.replace("r\"APP_VERSION = '(?:91|92|93)'\"","r\"APP_VERSION = '(?:91|92|93|94)'\"")
V91_WO.write_text(t,encoding='utf-8')

t=V92_WO.read_text(encoding='utf-8')
t=t.replace("r\"APP_VERSION = '(?:92|93)'\"","r\"APP_VERSION = '(?:92|93|94)'\"")
V92_WO.write_text(t,encoding='utf-8')

t=V93_WO.read_text(encoding='utf-8')
t=t.replace("assert \"APP_VERSION = '93'\" in s","assert re.search(r\"APP_VERSION = '(?:93|94)'\",s)")
V93_WO.write_text(t,encoding='utf-8')

t=V93_NOTES.read_text(encoding='utf-8')
t=t.replace("assert \"APP_VERSION = '93'\" in s","assert any(f\"APP_VERSION = '{v}'\" in s for v in ('93','94'))")
V93_NOTES.write_text(t,encoding='utf-8')

print('Applied v94 release version bump, README notes, and regression version updates.')
