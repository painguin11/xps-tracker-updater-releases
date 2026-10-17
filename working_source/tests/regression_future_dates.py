"""Regression: PDF future dates must never be selected or silently substituted.

Uses the application's actual date-parser function AST with today's local date.
No customer files are needed.
"""
import ast
import re
from datetime import datetime, timedelta
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
names={'_future_date','parse_date_text','_plausible_sheet_year',
       '_parse_sheet_date_text_candidates','_choose_sheet_date_evidence'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert {n.name for n in nodes}==names
ns={'datetime':datetime,'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)

today=datetime.now().date()
yesterday=today-timedelta(days=1)
tomorrow=today+timedelta(days=1)
assert not ns['_future_date'](datetime.combine(today,datetime.min.time()))
assert ns['_future_date'](datetime.combine(tomorrow,datetime.min.time()))

for day in (yesterday,today):
    val=ns['parse_date_text'](day.strftime('%m/%d/%Y'))
    assert val is not None and val.date()==day,(day,val)
    assert ns['_choose_sheet_date_evidence']([day.strftime('%m/%d/%Y')])['date'].date()==day
for day in (tomorrow,tomorrow+timedelta(days=40)):
    value=day.strftime('%m/%d/%Y')
    assert ns['parse_date_text'](value) is None,value
    assert ns['parse_date_text'](value,allow_future=True).date()==day
    assert ns['parse_date_text'](day.strftime('%B %-d, %Y')) is None
    assert ns['_parse_sheet_date_text_candidates'](value)==[],value
    assert ns['_parse_sheet_date_text_candidates'](day.strftime('%Y/%d/%m'))==[],day
    evidence=ns['_choose_sheet_date_evidence']([value]*4)
    assert evidence['date'] is None and evidence['future_dates'],evidence
    assert all(dt.date()>today for dt in evidence['future_dates'])
    # Even when the report's confirmed date is older, flag a conflicting future read.
    evidence=ns['_choose_sheet_date_evidence']([value]*4,datetime.combine(yesterday,datetime.min.time()))
    assert evidence['future_dates'],evidence

# Confirm source-level write gate remains before any workbook modification.
source=SOURCE.read_text(encoding='utf-8')
a=source.index('    def update_master(self):')
b=source.index('        if not self.resolve_pipe_duplicate_groups(',a)
guard=source[a:b]
assert 'future_rows=' in guard and 'future_tickets=' in guard
assert '_future_date_rejected' in guard and 'Future date rejected' in guard
assert "if _future_date(edited_date)" in source
assert "if _future_date(date)" in source
print('PASS future dates rejected in report, sheet, ticket and write paths')
