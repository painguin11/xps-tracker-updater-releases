from pathlib import Path
import ast,re

p=Path('working_source/app/reno_scan_updater.py')
s=p.read_text(encoding='utf-8')
assert 'MAX_ROW_LENGTH = 1700.0' in s
assert 'MAX_ROW_LENGTH_DECIMALS = 2' in s
assert 'def _row_length_token_value(token):' in s
assert 'def _ocr_length_candidates(cell_img, fast_plain=False):' in s
assert 'def _independent_row_length_read(cell_img,expanded_img=None,kind=' in s
assert 'cv2.threshold(threshold_base,200,255,cv2.THRESH_BINARY)' in s
# v84 strengthens the old threshold-first selection into evidence-strength voting.
assert 'def _select_independent_length_candidate(' in s
assert 'threshold-supported tie break' in s
assert 'def _retry_length_total_mismatch(self,check,all_rows=False,force=False):' in s
assert "rec['_length_value_cell']" in s and "rec['_length_expanded_cell']" in s
assert '_ocr_gridless_number_candidates(cell_img,True,row_length=True)' in s
# Printed work-order/page totals deliberately remain allowed above 1700 and v84
# reads them independently at high resolution rather than with the row parser.
block=s[s.index('def _read_pair_table_printed_total'):s.index('def _resolve_printed_total_sources')]
assert '_high_res_printed_total_candidates(cell)' in block
assert 'row_length=True' not in block

# Execute only the pure token helper plus constants.
tree=ast.parse(s)
nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('MAX_ROW_LENGTH','MAX_ROW_LENGTH_DECIMALS') for t in node.targets): nodes.append(node)
    if isinstance(node,ast.FunctionDef) and node.name in ('_row_length_token_value','_valid_row_length_value'): nodes.append(node)
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<helpers>','exec'),ns)
parse=ns['_row_length_token_value']
assert parse('100.99') == 100.99
assert parse('100.9') == 100.9
assert parse('100') == 100.0
assert parse('399.021') is None
assert parse('1700') == 1700.0
assert parse('1700.01') is None
assert parse('2401') is None
print('v83 length value constraints regression passed')

# Behaviorally exercise App.verify_length_totals instead of relying on brittle
# whole-file source ordering. This proves the actual recovery policy:
# targeted/master-suspect pass first, then the all-row independent pass only if
# the group still does not reconcile.
app_node=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='App')
verify_node=next(node for node in app_node.body if isinstance(node,ast.FunctionDef) and node.name=='verify_length_totals')
verify_module=ast.Module(body=[verify_node],type_ignores=[])
ast.fix_missing_locations(verify_module)
verify_ns={'_resolve_printed_total_sources': lambda sources: {
    'available': True, 'pages': [2], 'value': 100.0, 'confident': True, 'mode': 'printed'
}}
exec(compile(verify_module,'<verify_length_totals>','exec'),verify_ns)
verify=verify_ns['verify_length_totals']

class DummyRecovery:
    def __init__(self,targeted_succeeds=False):
        self.targeted_succeeds=targeted_succeeds
        self.fixed=False
        self.calls=[]
        self.prompts=0
        self.total_validations=[]
    def refresh_total_check(self,check):
        check['passed']=self.fixed
        return self.fixed
    def _retry_length_total_mismatch(self,check,all_rows=False,force=False):
        self.calls.append((all_rows,force))
        if (not all_rows and self.targeted_succeeds) or all_rows:
            self.fixed=True
            return True
        return False
    def prompt_total_check(self,check):
        self.prompts+=1

# If the master-targeted stage cannot resolve the mismatch, every row gets the
# independent second-stage audit before any popup is shown.
dummy=DummyRecovery(targeted_succeeds=False)
verify(dummy,{('11734','Pipe'):[{'page':2}]})
assert [all_rows for all_rows,_force in dummy.calls] == [False,True], dummy.calls
assert dummy.prompts == 0
assert dummy.total_validations and dummy.total_validations[0].get('passed') is True

# If targeted rereading resolves the total, the expensive all-row audit must not run.
dummy=DummyRecovery(targeted_succeeds=True)
verify(dummy,{('11734','Pipe'):[{'page':2}]})
assert [all_rows for all_rows,_force in dummy.calls] == [False], dummy.calls
assert dummy.prompts == 0
assert dummy.total_validations[0].get('passed') is True
print('v83/v84 two-stage total recovery behavior regression passed')

assert "record.get('_length_value_cell') or record.get('_cleaning_value_cell')" not in s
assert "cell=record.get('_length_value_cell')" in s
print('v83 numpy cell-selection regression passed')
