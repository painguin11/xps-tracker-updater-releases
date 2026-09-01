from pathlib import Path
import re
import subprocess

APP = Path('working_source/app/reno_scan_updater.py')
UPDATER = Path('working_source/app/xps_update.py')
README = Path('working_source/app/README_XPS_Tracker_Updater.txt')
V75_TEST = Path('working_source/tests/regression_v75_811_ocr.py')
LENGTH_TEST = Path('working_source/tests/regression_length_totals.py')
GUARD = Path('working_source/tests/regression_v78_rollback.py')


def git_show(path: str) -> str:
    return subprocess.check_output(
        ['git', 'show', f'origin/v75-work:{path}'], text=True, encoding='utf-8'
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'{label}: expected source block not found; refusing broad edit')
    return text.replace(old, new, 1)


# Restore the last cleaning OCR implementation before total-driven reselection
# (v76) and simple-first OCR (v77) were introduced.
text = git_show('working_source/app/reno_scan_updater.py')
LENGTH_TEST.write_text(git_show('working_source/tests/regression_length_totals.py'), encoding='utf-8')
V75_TEST.write_text(git_show('working_source/tests/regression_v75_811_ocr.py'), encoding='utf-8')

# Keep only the useful v76 saved-layout improvement. A previously confirmed
# layout should be accepted without immediately showing the same dialog again.
old = """                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                            dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                            if dlg.result is None:
                                self.status.set('Analysis cancelled.'); return
                            confirmed_layouts[fingerprint]=dlg.result
                            apply_confirmed_layout(layout,dlg.result)
                            save_layout_profile(fingerprint,layout,dlg.result)
"""
new = """                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                                if dlg.result is None:
                                    self.status.set('Analysis cancelled.'); return
                                confirmed_layouts[fingerprint]=dlg.result
                                apply_confirmed_layout(layout,dlg.result)
                                save_layout_profile(fingerprint,layout,dlg.result)
"""
text = replace_once(text, old, new, 'saved-layout confirmation gate')

text, n = re.subn(r"APP_VERSION = ['\"]\d+['\"]", "APP_VERSION = '78'", text, count=1)
if n != 1:
    raise SystemExit('APP_VERSION replacement failed')
text, n = re.subn(r"OCR_CACHE_VERSION = ['\"]v\d+['\"]", "OCR_CACHE_VERSION = 'v5'", text, count=1)
if n != 1:
    raise SystemExit('OCR cache version replacement failed')
APP.write_text(text, encoding='utf-8')

updater = UPDATER.read_text(encoding='utf-8')
updater, n = re.subn(r"CURRENT_VERSION = ['\"]\d+['\"]", 'CURRENT_VERSION = "78"', updater, count=1)
if n != 1:
    raise SystemExit('CURRENT_VERSION replacement failed')
UPDATER.write_text(updater, encoding='utf-8')

# The v75 OCR regression still applies; only its expected cache namespace changes.
test = V75_TEST.read_text(encoding='utf-8').replace("OCR_CACHE_VERSION = 'v3'", "OCR_CACHE_VERSION = 'v5'")
V75_TEST.write_text(test, encoding='utf-8')

readme = README.read_text(encoding='utf-8')
title = 'Version 78 cleaning OCR recovery'
if title not in readme:
    readme += """

Version 78 cleaning OCR recovery
--------------------------------
- Removes the v77 simple-first cleaning-length OCR strategy.
- Removes v76 automatic total-driven row reselection, which could change good OCR values just to force the arithmetic to match.
- Restores the v75 printed-value consensus and grid-rule-removal path that specifically handles border-touching digits such as 275 and 224.
- Keeps the saved-layout auto-accept improvement so confirmed table layouts do not prompt again unnecessarily.
- Total validation remains fail-closed: a mismatch blocks the master update but does not silently rewrite row lengths.
- Uses OCR cache v5 so incorrect v76/v77 cached reads are never reused.
"""
    README.write_text(readme, encoding='utf-8')

GUARD.write_text("""from pathlib import Path

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "APP_VERSION = '78'" in src
assert "OCR_CACHE_VERSION = 'v5'" in src
assert 'def _choose_cleaning_length' in src
assert 'def _ocr_gridless_number_candidates' in src
assert 'consensus.extend(_ocr_gridless_number_candidates(value_cell,True))' in src
assert 'def _simple_cleaning_length_candidates' not in src
assert 'def _fallback_cleaning_length_candidates' not in src
assert 'def retry_total_length_ocr' not in src
assert 'OCR LENGTH RESELECTED USING VERIFIED PDF TOTAL' not in src
saved_gate = """ + repr("""if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)""") + """
assert saved_gate in src
print('v78 v75-OCR recovery + fail-closed total guard passed.')
""", encoding='utf-8')

print('Applied v78 recovery source.')
