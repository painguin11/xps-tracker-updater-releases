import ast
from pathlib import Path

SOURCE = Path('working_source/app/reno_scan_updater.py')
src = SOURCE.read_text(encoding='utf-8')

native_gate = "if layout.get('confidence',0)>=100 and all(k in detected_roles for k in ('up','down','value','date')):"
assert native_gate in src, '100% native-layout auto-accept gate was removed'

saved_gate = """if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)"""
assert saved_gate in src, 'saved 100% layout still falls through to the confirmation dialog'
assert 'self.retry_total_length_ocr(check,verified)' in src, 'corrected totals do not trigger OCR retry'
assert 'self.retry_total_length_ocr(check,check.get(\'pdf_total\'))' in src, 'confident PDF totals do not trigger automatic OCR retry'
assert "rec['_length_ocr_cell']=value_cell.copy()" in src, 'cleaning cells are not retained for retry OCR'

# Exercise the pure arithmetic selector with the exact v75 failure pattern.
tree = ast.parse(src)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_find_cleaning_total_reconciliation')
ns = {}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), ns)
reconcile = ns['_find_cleaning_total_reconciliation']

wrong = [369,369,314,2,313,72,268,400,78,345,320,291,366,350,75,274,120]
records = [{
    'video_length': value,
    '_length_ocr_candidates': [value],
} for value in wrong]
records[14]['_length_ocr_candidates'] = [75,75,275,275,275,275,275]
records[15]['_length_ocr_candidates'] = [274,274,224,224,224,224,224]
result = reconcile(records,4476)
assert result['matched'], result
assert result['changes'] == [(14,75.0,275.0),(15,274.0,224.0)], result

# The total is a constraint over actual OCR observations, not permission to invent
# a number that was never read.
assert not reconcile(records,4475)['matched']

# A user-edited length is authoritative and cannot be silently changed by retry OCR.
records[14]['_length_user_edited'] = True
assert not reconcile(records,4476)['matched']

print('v76 layout skip + verified-total OCR reconciliation safeguards passed.')
