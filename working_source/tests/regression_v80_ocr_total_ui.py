from pathlib import Path
import ast
from datetime import datetime
import re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
version_match=re.search(r"APP_VERSION = ['\"](\d+)['\"]",src)
assert version_match and int(version_match.group(1))>=80
assert "OCR_CACHE_VERSION = 'v6'" in src

# Printed total: least-destructive stable source wins before fallback transforms.
assert 'def _preferred_printed_total_candidates' in src
assert "return direct,'direct full cell'" in src
assert "return gridless,'gridless fallback'" in src

# Cleaning path: one aligned-column first pass, then fallback only after validation.
assert 'batch_suspect=' not in src
assert 'value=_choose_cleaning_length(value_candidates,None)' in src
assert 'right_bleed=max(2,int(round((x2-x1)*.02)))' in src
assert 'sample[:,-edge:]=255' not in src
assert 'def _stable_numeric_vote' in src
assert 'def _conservative_cleaning_reread' in src
assert 'def _retry_cleaning_total_mismatch' in src
assert "if not check.get('passed') and kind=='Cleaning':" in src
assert "self._retry_cleaning_total_mismatch(check,force=True)" in src
assert "r['_length_user_edited']=True" in src
assert "rec['_cleaning_value_cell']" in src

# Date and group-level review behavior remain in place. As of v83, a total
# failure has its own Live Summary row instead of being appended to the first
# asset row in the work-order group.
assert 'def _plausible_sheet_year' in src
assert "use_date=current_wo.get('date') or current_report_date or page_date" in src
assert 'def _draw_total_outlines' in src
assert 'def show_total_summary_error(self,check,follow=False):' in src
assert "tags=('total_warning',)" in src
assert '_total_warning_for_record_index' not in src
assert "record.setdefault('warnings',[]): record['warnings'].append(warning)" not in src
assert 'work-order group remains outlined in red' in src

# Execute only pure helpers so this regression remains independent of Windows/Tk.
tree=ast.parse(src)
names={'_printed_total_value_is_plausible','_choose_printed_total','_preferred_printed_total_candidates',
       '_plausible_sheet_year','_parse_sheet_date_text_candidates','_choose_cleaning_length',
       '_stable_numeric_vote'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'datetime':datetime,'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v80-helpers>','exec'),ns)

# Stable untouched total OCR wins over a larger pile of damaged fallback reads.
cands,mode=ns['_preferred_printed_total_candidates']([8427,8427],[87]*12,24)
assert mode=='direct full cell' and ns['_choose_printed_total'](cands)[0]==8427
# If the raw total cell is not stable, a stable rule-free read may recover it.
cands,mode=ns['_preferred_printed_total_candidates']([776],[4321]*5+[7]*2,18)
assert mode=='gridless fallback' and ns['_choose_printed_total'](cands)[0]==4321

# Stable numeric voting never manufactures the master/total value.
assert ns['_stable_numeric_vote']([366,366],2)==(366.0,True)
assert ns['_stable_numeric_vote']([36,366],2)==(None,False)
assert ns['_stable_numeric_vote']([366,366,366,36],3)==(366.0,True)

# An absurd expected year must not overwrite a clearly printed plausible year.
result=ns['_parse_sheet_date_text_candidates']('8/17/2026',datetime(2096,8,17))
assert result and result[0][0].year==2026
# An absurd printed year is repaired only when a plausible packet year is available.
result=ns['_parse_sheet_date_text_candidates']('8/17/2096',datetime(2026,8,17))
assert result and result[0][0].year==2026
assert ns['_parse_sheet_date_text_candidates']('8/17/2096',None)==[]

print('v80 simple-first OCR/total/group-review regression passed.')
