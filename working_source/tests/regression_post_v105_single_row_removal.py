from pathlib import Path
import ast

root=Path(__file__).resolve().parents[1]
wrapper_path=root/'app'/'xps_review_controls.py'
wrapper=wrapper_path.read_text(encoding='utf-8')

# Row-level deletion must be an explicit reviewer action, separate from whole-W/O discard.
for token in (
    "text='Remove Selected Row'",
    "def remove_selected_row(self):",
    "if not str(iid).startswith('record:'):",
    "_remove_pending_record(self.records,index,self.manhole_count_validations)",
    "self.resolve_pipe_duplicate_groups(prompt=False,update_mode=False)",
    "self.refresh_total_check(check,redraw=False)",
    "self._rebuild_review_tree()",
):
    assert token in wrapper,token

method=wrapper[wrapper.index('    def remove_selected_row(self):'):]
method=method[:method.index('\n    def ',1)]
assert "self.trouble_tickets" not in method
assert "self.groups=" not in method
assert "_discard_work_order_set" not in method
assert "askyesno" in method
assert "_analysis_running" in method

# Exercise the pure mutation/count helper so deletion is proven to remove exactly
# one selected record while preserving neighboring rows and the rest of the W/O.
tree=ast.parse(wrapper)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_remove_pending_record')
ns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(wrapper_path),'exec'),ns)
remove=ns['_remove_pending_record']

records=[
    {'kind':'Manhole','asset':'DN-1001','wo':'12001'},
    {'kind':'Manhole','asset':'?','wo':'12001'},
    {'kind':'Manhole','asset':'DN-1003','wo':'12001'},
    {'kind':'Pipe','asset':'P-1','wo':'12002'},
]
checks=[
    {'kind':'Manhole','wo':'12001','expected':2,'actual':3,'passed':False},
    {'kind':'Manhole','wo':'99999','expected':4,'actual':4,'passed':True},
]
removed=remove(records,1,checks)
assert removed['asset']=='?'
assert [r['asset'] for r in records]==['DN-1001','DN-1003','P-1']
assert checks[0]['actual']==2 and checks[0]['passed'] is True
assert checks[1]=={'kind':'Manhole','wo':'99999','expected':4,'actual':4,'passed':True}

print('post-v105 single-row removal regression passed')
