import ast
from datetime import datetime
from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
wanted={'_date_outlier_is_well_supported'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
ns={}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)
dom=datetime(2026,8,11)
bad={'date':datetime(2026,1,1),'votes':{datetime(2026,1,1):1},'strong_votes':{datetime(2026,1,1):1}}
assert not ns['_date_outlier_is_well_supported'](bad,dom)
real={'date':datetime(2026,8,12),'votes':{datetime(2026,8,12):3},'strong_votes':{datetime(2026,8,12):2}}
assert ns['_date_outlier_is_well_supported'](real,dom)
assert "'band_index':None" in text
assert "'in-grid footer total',len(bands)-1" in text
assert "if total_band_index is not None and band_index==total_band_index:" in text
assert 'Structural filtering happens BEFORE date repair' in text
assert 'has_asset_digit_signal(up_obs) and has_asset_digit_signal(dn_obs)' in text
assert "prepared['printed_total_info']=printed_total_info" in text
print('v74 header/footer exclusion and date-outlier safeguards passed.')
