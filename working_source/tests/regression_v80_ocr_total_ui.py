from pathlib import Path
import ast
from datetime import datetime
import re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "APP_VERSION = '80'" in src
assert "OCR_CACHE_VERSION = 'v6'" in src
assert 'def _preferred_printed_total_candidates' in src
assert "return direct,'direct full cell'" in src
assert "return gridless,'gridless fallback'" in src
assert 'batch_suspect=' in src
assert 'cell_candidates=_ocr_digits(value_cell,True,fast_plain=True)' in src
assert 'def _plausible_sheet_year' in src
assert "use_date=current_wo.get('date') or current_report_date or page_date" in src
assert 'def _draw_total_outlines' in src
assert 'def _total_warning_for_record_index' in src
assert "tags=('total_warning',)" not in src
assert "record.setdefault('warnings',[]): record['warnings'].append(warning)" not in src
assert 'work-order group remains outlined in red' in src

# Execute only pure helpers so this regression remains independent of Windows/Tk.
tree=ast.parse(src)
names={'_printed_total_value_is_plausible','_choose_printed_total','_preferred_printed_total_candidates',
       '_plausible_sheet_year','_parse_sheet_date_text_candidates','_choose_cleaning_length'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'datetime':datetime,'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v80-helpers>','exec'),ns)

# Stable untouched OCR wins over a larger pile of damaged fallback reads.
cands,mode=ns['_preferred_printed_total_candidates']([8427,8427],[87]*12,24)
assert mode=='direct full cell' and ns['_choose_printed_total'](cands)[0]==8427
# If the raw cell is not independently stable, a stable rule-free read may recover it.
cands,mode=ns['_preferred_printed_total_candidates']([776],[4321]*5+[7]*2,18)
assert mode=='gridless fallback' and ns['_choose_printed_total'](cands)[0]==4321
# One bad batch read cannot beat two matching conservative cell reads.
assert ns['_choose_cleaning_length']([42,342,342],340)==342
# An absurd expected year must not overwrite a clearly printed plausible year.
result=ns['_parse_sheet_date_text_candidates']('8/17/2026',datetime(2096,8,17))
assert result and result[0][0].year==2026
# An absurd printed year is repaired only when a plausible packet year is available.
result=ns['_parse_sheet_date_text_candidates']('8/17/2096',datetime(2026,8,17))
assert result and result[0][0].year==2026
assert ns['_parse_sheet_date_text_candidates']('8/17/2096',None)==[]

print('v80 OCR/total/group-review regression passed.')
