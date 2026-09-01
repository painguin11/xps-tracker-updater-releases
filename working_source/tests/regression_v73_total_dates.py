import ast,re
from datetime import datetime
from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
wanted={'_parse_sheet_date_text_candidates','_choose_sheet_date_evidence','_dominant_sheet_date','_printed_total_value_is_plausible'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
ns={'re':re,'datetime':datetime}; exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)
expected=datetime(2026,8,11)
strong=ns['_choose_sheet_date_evidence'](['8/11/2026'],expected)
assert strong['date']==expected and strong['strong']
weak=ns['_choose_sheet_date_evidence'](['8/11/9026'],expected)
assert weak['date']==expected and not weak['strong']
other=ns['_choose_sheet_date_evidence'](['8/12/2026'],expected)
assert other['date']==datetime(2026,8,12) and other['strong']
reads=[
 {'date':datetime(2026,8,17),'strong':False},
 {'date':datetime(2026,1,11),'strong':False},
 {'date':datetime(2026,2,11),'strong':False},
 {'date':expected,'strong':False},{'date':expected,'strong':False},
 {'date':expected,'strong':False},{'date':expected,'strong':True},{'date':expected,'strong':False},
 {'date':datetime(2026,9,11),'strong':False},
]
assert ns['_dominant_sheet_date'](reads,expected)==expected
assert not ns['_printed_total_value_is_plausible'](4,19)
assert ns['_printed_total_value_is_plausible'](4476,19)
assert 'in-grid footer total' in text
assert '_ocr_gridless_number_candidates(cell,True)' in text
assert 'dominant_date=_dominant_sheet_date' in text
assert "self.pump_analysis_ui,use_date)" in text
print('v73 total-row and date-consensus safeguards passed.')
