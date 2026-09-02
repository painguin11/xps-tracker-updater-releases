from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'def _keep_unresolved_pair_row' in src
assert "if not _keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,profile=profile):" in src
assert "unresolved_up=_best_observed_asset_id(up_obs,endpoint_items)" in src
assert "unresolved_dn=_best_observed_asset_id(dn_obs,endpoint_items)" in src

# The structural gate must happen before inferred dominant-date repair; otherwise
# a header row can inherit the real rows' date and survive as fake data.
parser=src[src.index('def parse_year15_pair_list'):src.index('def parse_year15_manholes')]
assert parser.index('_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,profile=profile)') < parser.index('if dominant_date is not None')

tree=ast.parse(src)
names={'asset_key','_asset_id_parts','_keep_unresolved_pair_row'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<header-noise>','exec'),ns)
keep=ns['_keep_unresolved_pair_row']

# Exact false row from the 8/26 cleaning page before dominant date inheritance.
assert keep('EN','SUNAA',None,None) is False
# Generic fallback behavior still preserves real unresolved asset-shaped rows.
assert keep('EC-1521','EC-1475',None,None) is True
assert keep('R2-380','R2-413',None,None) is True
# Direct row evidence keeps an uncertain row available for review when no project
# format has been configured; configured profiles are covered by the v82 format test.
assert keep('EC-1521','SUNAA',240.0,None) is True
assert keep('EN','SUNAA',None,'08/26/2026') is True

print('v82 cleaning header-noise structural regression passed.')
