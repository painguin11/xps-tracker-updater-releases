"""Regression coverage for single-day and overnight physical work orders."""
from pathlib import Path
import ast
from datetime import datetime, timedelta

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

names=('_future_date','_work_order_group_key','_set_work_order_group_date',
       '_reconcile_work_order_group_dates','_work_order_date_problems')
ns={'datetime':datetime}
for name in names:
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

def mark(rec,reason):
    reasons=rec.setdefault('_review_skip_reasons',[])
    if reason not in reasons: reasons.append(reason)
    rec['skip_update']=True

def clear(rec,reason):
    reasons=[r for r in rec.get('_review_skip_reasons',[]) if r!=reason]
    rec['_review_skip_reasons']=reasons
    if not reasons and not rec.get('_field_review_reasons'):
        rec['skip_update']=False
        return True
    return False

ns['_mark_field_review_block']=mark
ns['_clear_field_review_block']=clear
reconcile=ns['_reconcile_work_order_group_dates']
set_date=ns['_set_work_order_group_date']
problems=ns['_work_order_date_problems']
day_a=datetime(2025,11,12)
day_b=datetime(2025,11,13)
day_c=datetime(2025,11,14)

def row(page,date,wo='1234',**extra):
    return {'kind':'Pipe','_workorder_group':page,'wo':wo,'date':date,
            'status':'Matched','skip_update':False,**extra}

# A confirmed date fills unreadable Pipe/Cleaning/Manhole rows in the same group.
one=[row(0,day_a),row(0,None),row(0,day_a)]
other=[row(4,day_c,wo='5678'),row(4,None,wo='5678')]
reconcile(one+other,{0:{'date':day_a},4:{'date':None}})
assert all(r['date']==day_a for r in one),one
assert all(r['date']==day_c for r in other),other
assert not problems(one+other)

# Distinct work-order pages remain separate even if the W/O number repeats.
same_number=[row(8,day_b),row(9,day_c)]
reconcile(same_number,{8:{'date':day_b},9:{'date':day_c}})
assert [r['date'] for r in same_number]==[day_b,day_c]

# Preserve strong adjacent-date rows and review an unresolvable midnight split.
mixed=[row(12,day_a),row(12,day_b,_row_date_strong=True),row(12,None)]
reconcile(mixed,{12:{'date':day_a}})
assert [r['date'] for r in mixed]==[day_a,day_b,None]
assert 'Overnight row date needs review' in mixed[2]['_field_review_reasons']
assert problems(mixed)==['1234']
set_date(mixed,mixed[2],day_b,clear_group_review=True,whole_group=False)
assert [r['date'] for r in mixed]==[day_a,day_b,day_b]
assert not problems(mixed)
# Ordinary no-op/row-only editing never erases the overnight date.
set_date(mixed,mixed[0],day_a,clear_group_review=True,whole_group=False)
assert mixed[1]['date']==day_b

# Strong adjacent dates with no missing cells are accepted.
overnight=[row(15,day_a),row(15,day_b,_row_date_strong=True)]
reconcile(overnight,{15:{'date':day_a}})
assert [r['date'] for r in overnight]==[day_a,day_b]
assert not problems(overnight)

# Weak isolated adjacent dates remain visible but require review.
weak=[row(16,day_a),row(16,day_b)]
reconcile(weak,{16:{'date':day_a}})
assert weak[1]['date']==day_b and problems(weak)==['1234']

# Missing dates bracketed by same-day rows can be filled, not at midnight.
bracket=[row(17,day_a,source_page=2),row(17,None,source_page=2),
         row(17,day_a,source_page=2),row(17,day_b,source_page=2,_row_date_strong=True)]
reconcile(bracket,{17:{'date':day_a}})
assert [r['date'] for r in bracket]==[day_a,day_a,day_a,day_b]
assert not problems(bracket)

# Date fallback assigned during extraction is not printed evidence.
fallback=[row(18,day_a,_row_date_observed=day_a),
          row(18,day_a,_row_date_observed=None),
          row(18,day_b,_row_date_observed=day_b,_row_date_strong=True)]
reconcile(fallback,{18:{'date':day_a}})
assert fallback[1]['date'] is None and problems(fallback)==['1234']

# Without a confirmed date, a single unambiguous OCR date fills missing rows.
unique=[row(13,day_b),row(13,None)]
reconcile(unique,{13:{'date':None}})
assert all(r['date']==day_b for r in unique)
assert not problems(unique)

# Conflicting OCR dates, or no dates at all, block workbook writes.
disputed=[row(20,day_a),row(20,day_c)]
reconcile(disputed,{20:{'date':None}})
assert [r['date'] for r in disputed]==[day_a,day_c]
assert all('Work order dates conflict' in r['_field_review_reasons'] for r in disputed)
assert problems(disputed)==['1234']
missing=[row(30,None),row(30,None)]
reconcile(missing,{30:{'date':None}})
assert all('Work order date missing' in r['_field_review_reasons'] for r in missing)
assert problems(missing)==['1234']

# One explicit date edit repairs the entire physical group, clearing only
# group-level blockers; independent rejected future-date evidence stays blocked.
disputed[1]['_field_review_reasons'].append('Future date rejected')
mark(disputed[1],'Future date rejected')
assert set_date(disputed,disputed[0],day_c,clear_group_review=True)==2
assert all(r['date']==day_c for r in disputed)
assert not problems(disputed)
assert not disputed[0].get('_field_review_reasons')
assert disputed[0]['skip_update'] is False
assert 'Future date rejected' in disputed[1]['_field_review_reasons']
assert disputed[1]['skip_update'] is True

# Direct mutations cannot bypass the independent master-write consistency gate.
disputed[0]['date']=day_a
assert problems(disputed)==['1234']
disputed[0]['date']=day_c

# Future dates are never accepted as manually applied group dates.
try:
    set_date(disputed,disputed[0],datetime.now()+timedelta(days=2))
except ValueError:
    pass
else:
    raise AssertionError('future date accepted')
assert all(r['date']==day_c for r in disputed)

# Check wiring: confirmation, extraction, edit and workbook-write gate.
confirm=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ConfirmDialog')
app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App')
methods={n.name:n for n in app.body if isinstance(n,ast.FunctionDef)}
calls=lambda node:{n.func.id for n in ast.walk(node)
                   if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
assert '_reconcile_work_order_group_dates' in calls(methods['analyze'])
assert '_set_work_order_group_date' in calls(methods['edit_selected'])
assert '_work_order_date_problems' in calls(methods['update_master'])
assert 'self.date_var' in text and 'Work Order Date:' in text
assert "and not (match or endpoint_signal)" in text

print('single-day and overnight work-order date consistency regression passed')
