from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'PROJECT_ASSET_FORMAT_RULES' not in src
assert 'ASSET_FORMAT_RULES = {' not in src
assert 'def _infer_asset_format(values):' in src
assert "'allow_suffix':True" in src
assert "'asset_format':asset_format" in src
assert "asset_format=master_index.get('asset_format')" in src
assert "_ocr_asset_candidates(cell,fast_plain=fast,asset_format=asset_format)" in src
assert "_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,asset_format=asset_format)" in src
assert "formatted=_printed_asset_tokens(raw,asset_format)" in src

# Exercise the pure master-format inference helpers without importing Windows UI deps.
tree=ast.parse(src)
names={'_raw_master_asset','_infer_asset_format','_asset_format_requires_dash',
       '_printed_asset_tokens','_asset_value_matches_format'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<master-format>','exec'),ns)
infer=ns['_infer_asset_format']; tokens=ns['_printed_asset_tokens']; valid=ns['_asset_value_matches_format']

# Current B&C-style master: dash is learned from master, not from project name.
rule=infer(['EC-1817','EC-1801','R2-280','DN-1234'])
assert rule['mode']=='prefixed_dash' and rule['requires_dash']
assert rule['max_digits']==4
assert rule['allow_suffix'] is True
for value in ('DN-1','DN-1234','EC-1817','R2-280'):
    assert tokens(value,rule)==[value], value
# Critical: no suffixed example exists above, but one-letter suffixes are STILL
# structurally possible new assets and must not be rejected for that reason.
for value in ('EC-1817A','DN-1234A','R2-280A'):
    assert tokens(value,rule)==[value], value
    assert valid(value,rule), value
for value in ('EC1817','R2280','EN','SUNAA','DN-12345','DN-1234AB'):
    assert tokens(value,rule)==[], value

# Numeric-only master is inferred automatically too. A one-letter new suffix is
# still possible even if the master contains only unsuffixed numbers.
reno=infer(['1','25','430','1234'])
assert reno['mode']=='numeric' and not reno['requires_dash']
assert tokens('1234',reno)==['1234']
assert tokens('1234A',reno)==['1234A']
assert valid('1234A',reno)
assert tokens('DN-1',reno)==[]

print('v82 master-inferred asset-format regression passed.')
