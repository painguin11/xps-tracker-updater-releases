import ast
from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
wanted={'_choose_printed_total','_resolve_printed_total_sources','_length_total_result'}
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted]
module=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(module)
ns={}; exec(compile(module,str(SOURCE),'exec'),ns)

value,confident=ns['_choose_printed_total']([5690,5690,5690,5690])
assert value==5690 and confident
value,confident=ns['_choose_printed_total']([5690,5680])
assert value is None and not confident

single=ns['_resolve_printed_total_sources']([
    {'page':4,'info':{'found':True,'value':5690,'confident':True}}
])
assert single['available'] and single['value']==5690 and single['confident']

pages=ns['_resolve_printed_total_sources']([
    {'page':2,'info':{'found':True,'value':2000,'confident':True}},
    {'page':3,'info':{'found':True,'value':3690,'confident':True}},
])
assert pages['value']==5690 and pages['confident']

partial=ns['_resolve_printed_total_sources']([
    {'page':2,'info':{'found':True,'value':2000,'confident':True}},
    {'page':3,'info':{'found':False,'value':None,'confident':False}},
    {'page':4,'info':{'found':True,'value':3690,'confident':True}},
])
assert partial['value']==5690 and not partial['confident']

lengths=[56,163,190,165,190,60,35,206,296,171,47,262,114,101,105,140,299,299,296,258,300,299,317,305,301,319,396]
records=[{'video_length':value} for value in lengths]
result=ns['_length_total_result'](records,5690)
assert result['summary_total']==5690 and result['matches'] and result['missing']==0
bad=[dict(r) for r in records]; bad[12]['video_length']=None
result=ns['_length_total_result'](bad,5690)
assert result['summary_total']==5576 and not result['matches'] and result['missing']==1
bad[12]['video_length']=104
result=ns['_length_total_result'](bad,5690)
assert result['summary_total']==5680 and result['difference']==-10 and not result['matches']

source=SOURCE.read_text(encoding='utf-8')
assert 'needs_consensus=(value is None or len(distinct)>1' in source
assert "prepared['printed_total_info']=_read_pair_table_printed_total" in source
assert 'TOTAL LENGTH VALIDATION FAILURE(S) — UPDATE MASTER BLOCKED' in source
print('Length-total reconciliation and invalid-first-pass OCR safeguards passed.')
