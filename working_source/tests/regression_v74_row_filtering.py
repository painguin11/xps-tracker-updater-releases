import ast
from datetime import datetime
from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
wanted={'_date_outlier_is_well_supported'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
ns={'datetime':datetime}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)
dom=datetime(2026,8,11)
expected=datetime(2026,8,11)
# Two full-year OCR reads are not enough to override a table/date consensus
# that agrees with the confirmed work-order date.
bad={'date':datetime(2026,3,11),'votes':{datetime(2026,3,11):4},'strong_votes':{datetime(2026,3,11):2}}
assert not ns['_date_outlier_is_well_supported'](bad,dom,expected)
# Three independent strong reads preserve a genuinely different row date.
real={'date':datetime(2026,8,12),'votes':{datetime(2026,8,12):4},'strong_votes':{datetime(2026,8,12):3}}
assert ns['_date_outlier_is_well_supported'](real,dom,expected)
# If the table's dominant date does not agree with the W/O date, keep the
# less aggressive two-strong-read threshold.
assert ns['_date_outlier_is_well_supported'](bad,dom,datetime(2026,8,10))
assert "'band_index':None" in text
assert "'in-grid footer total',len(bands)-1" in text
assert "if total_band_index is not None and band_index==total_band_index:" in text
assert 'Structural filtering happens BEFORE date repair' in text
assert 'has_asset_digit_signal(up_obs) and has_asset_digit_signal(dn_obs)' in text
assert "prepared['printed_total_info']=printed_total_info" in text
print('v74 header/footer exclusion and date-outlier safeguards passed.')
