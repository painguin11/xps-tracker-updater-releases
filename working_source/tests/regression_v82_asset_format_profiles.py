from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'ASSET_FORMAT_RULES = {' in src
assert "'reno': 'reno_numeric'" in src
assert "'year15': 'prefixed_dash_1_4_optional_suffix'" in src
assert "'phase2_year1': 'prefixed_dash_1_4_optional_suffix'" in src
assert 'Future project formats should be changed HERE' in src
assert "def _ocr_asset_candidates(cell_img, fast_plain=False, profile=None):" in src
assert "profile=master_index.get('profile','')" in src
assert "_ocr_known_r2_candidates(cut(up_box),endpoint_items,profile=profile)" in src
assert "_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,profile=profile)" in src
assert "_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,profile=profile)" in src
assert "observations=_ocr_asset_candidates(id_img,profile=profile)" in src

# Exercise the centralized pure format helpers.
tree=ast.parse(src)
names={'_asset_format_rule','_profile_requires_asset_dash','_printed_asset_tokens',
       '_asset_value_matches_profile','asset_key','_asset_id_parts'}
nodes=[]
for n in tree.body:
    if isinstance(n,(ast.Assign,ast.AnnAssign)):
        targets=[]
        if isinstance(n,ast.Assign): targets=[t.id for t in n.targets if isinstance(t,ast.Name)]
        elif isinstance(n.target,ast.Name): targets=[n.target.id]
        if any(t in {'ASSET_FORMAT_RULES','PROJECT_ASSET_FORMAT_RULES'} for t in targets): nodes.append(n)
    elif isinstance(n,ast.FunctionDef) and n.name in names:
        nodes.append(n)
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<asset-format>','exec'),ns)
tokens=ns['_printed_asset_tokens']; valid=ns['_asset_value_matches_profile']; parts=ns['_asset_id_parts']

# Current B&C project syntax: a literal dash is mandatory, 1-4 digits, optional one suffix.
for value in ('DN-1','DN-12','DN-1234','DN-1234A','EC-1817','R2-280','R2-1234A'):
    assert tokens(value,'year15')==[value], value
    assert valid(value,'phase2_year1'), value
for value in ('DN1','DN1234A','EC1817','R2280','EN','SUNAA','1234','DN-12345','DN-1234AB'):
    assert tokens(value,'year15')==[], value
    assert not valid(value,'year15'), value
assert tokens('  DN - 1  ','year15')==['DN-1']

# Legacy Reno remains numeric-only and does not inherit the B&C dash rule.
assert tokens('1234','reno')==['1234']
assert valid('1234','reno')
assert tokens('DN-1','reno')==[]
assert not valid('DN-1','reno')

# Generic internal parsing now permits the valid one-digit current asset number.
assert parts('DN-1') is not None

print('v82 centralized project asset-format regression passed.')
