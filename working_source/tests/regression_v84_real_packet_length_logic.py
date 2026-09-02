from pathlib import Path
import ast

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

assert "prepared['printed_total_info']=printed_total_info" in src
assert 'def _high_res_printed_total_candidates(cell_img):' in src
assert "fx=4.0,fy=4.0" in src
assert "direct=_high_res_printed_total_candidates(cell)" in src
assert "expanded_value_cell=cut(val_box,vertical_bleed=3)" in src
assert 'def _select_independent_length_candidate(' in src
assert 'def _independent_split_pipe_read(record):' in src
assert "existing['_length_part_reads']=part_reads" in src
assert "record.get('master_length'))" in src
assert "self._retry_length_total_mismatch(check,all_rows=True,force=True)" in src

# Exercise the pure selection rule against OCR evidence reproduced from the
# actual 8-26-2026 problem cells. Master values are only tie-break evidence.
tree=ast.parse(src)
wanted={'_valid_row_length_value','_select_independent_length_candidate'}
nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign):
        names={target.id for target in node.targets if isinstance(target,ast.Name)}
        if names & {'MAX_ROW_LENGTH'}:
            nodes.append(node)
    elif isinstance(node,ast.FunctionDef) and node.name in wanted:
        nodes.append(node)
ns={}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v84 helpers>','exec'),ns)
choose=ns['_select_independent_length_candidate']

value,ok,_=choose([78.12]*4,[30.0]*2,'Pipe',78.24863)
assert ok and value==78.12

value,ok,_=choose([242.15]*2,[242.16]*2,'Pipe',242.12554)
assert ok and value==242.16

value,ok,_=choose([360.31,360.31,260.3,260.3],[360.3]*4,'Pipe',360.339175)
assert ok and value==360.3

value,ok,_=choose([333.89]*4,[333.89]*2,'Pipe',334.240277)
assert ok and value==333.89

# The master can only break a tie between values that OCR really returned.
value,ok,source=choose([100.0,100.0],[101.0,101.0],'Cleaning',100.2)
assert ok and value==100.0 and 'master' in source
value,ok,_=choose([100.0],[101.0],'Cleaning',100.2)
assert not ok and value is None

print('v84 real-packet length reconciliation regression passed')
