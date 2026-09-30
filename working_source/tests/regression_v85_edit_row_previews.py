from pathlib import Path
import ast

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "'activity_value':value_cell.copy()" in src
assert "'date':date_img.copy() if getattr(date_img,'size',0) else None" in src
assert "dlg.result['_field_previews']" in src
assert "'wo':confirmed_preview('wo_preview')" in src
assert "'truck':confirmed_preview('truck_preview')" in src
assert "'operator':confirmed_preview('operator_preview')" in src
assert "rec['_field_preview_pages']=field_pages" in src
assert "'page':record.get('source_page')" in src
assert "if key=='activity_value' and int(r.get('part_count') or 0)>1:" in src
assert "Compare each value with its PDF image before saving." in src

# Execute the fallback-label helper without importing Windows-only dependencies.
tree=ast.parse(src)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_preview_unavailable_text')
ns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<preview-fallback>','exec'),ns)
label=ns['_preview_unavailable_text']
assert label([4])=='Preview unavailable — check PDF page 4.'
assert label([2,3])=='Preview unavailable — check PDF pages 2, 3.'
assert label('10')=='Preview unavailable — check PDF page 10.'

# Confirm the edit form requests previews for every editable field. Newer versions
# may add more fields; this v85 regression only guarantees the original five remain.
edit=src[src.index('    def edit_selected(self):'):src.index('    def edit_trouble_ticket(self,index):')]
for key in ('activity_value','date','wo','truck','operator'):
    assert repr(key) in edit
assert '_preview_unavailable_text(pages)' in edit

print('v85 edit-row PDF preview regression passed.')
