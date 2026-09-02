from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v82_cleaning_header_noise.py')
text=APP.read_text(encoding='utf-8')

marker="def _base_asset_key(value,known_items):\n"
if marker not in text:
    raise SystemExit('asset helper insertion marker not found')
if 'def _keep_unresolved_pair_row' not in text:
    helper=r'''def _keep_unresolved_pair_row(up_value,down_value,length_value,row_date):
    """Reject empty header/footer OCR while preserving real unresolved data rows.

    If an unresolved pair has no readable numeric/date evidence, both displayed
    endpoints must still look like complete asset IDs. This prevents header text
    such as EN -> SUNAA from becoming a fake cleaning row while keeping a real
    EC-1234 -> EC-5678 row available for manual length/date review.
    """
    if length_value is not None or row_date:
        return True
    return bool(_asset_id_parts(up_value) and _asset_id_parts(down_value))


'''
    text=text.replace(marker,helper+marker,1)

old="""        if not match and (edge_band or tall_band) and not endpoint_signal:
            continue
        if not match and not endpoint_signal:
            continue
        if d is None:
"""
new="""        if not match and (edge_band or tall_band) and not endpoint_signal:
            continue
        if not match and not endpoint_signal:
            continue
        if not match:
            unresolved_up=_best_observed_asset_id(up_obs,endpoint_items) or (canonical_asset_id(up_obs[0]) if up_obs else '')
            unresolved_dn=_best_observed_asset_id(dn_obs,endpoint_items) or (canonical_asset_id(dn_obs[0]) if dn_obs else '')
            if not _keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d):
                continue
        if d is None:
"""
if old not in text:
    raise SystemExit('structural unresolved-row gate not found')
text=text.replace(old,new,1)
APP.write_text(text,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'def _keep_unresolved_pair_row' in src
assert "if not _keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d):" in src
assert "unresolved_up=_best_observed_asset_id(up_obs,endpoint_items)" in src
assert "unresolved_dn=_best_observed_asset_id(dn_obs,endpoint_items)" in src

tree=ast.parse(src)
names={'asset_key','_asset_id_parts','_keep_unresolved_pair_row'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<header-noise>','exec'),ns)
keep=ns['_keep_unresolved_pair_row']

# Exact false row from the 8/26 cleaning page: header OCR, no length/date.
assert keep('EN','SUNAA',None,None) is False
# Real unresolved asset rows must remain visible even when length/date OCR fails.
assert keep('EC-1521','EC-1475',None,None) is True
assert keep('R2-380','R2-413',None,None) is True
# If other row evidence exists, keep it for review even with one damaged endpoint.
assert keep('EC-1521','SUNAA',240.0,None) is True
assert keep('EN','SUNAA',None,'08/26/2026') is True

print('v82 cleaning header-noise structural regression passed.')
''',encoding='utf-8')

print('Applied v82 cleaning header-noise structural guard.')
