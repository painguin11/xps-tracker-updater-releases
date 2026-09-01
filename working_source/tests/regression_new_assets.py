import ast
import re
from pathlib import Path


SOURCE=Path('output/package_v69/XPS_Tracker_Updater/reno_scan_updater.py')
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
wanted={
    'digits','canonical_asset_id','asset_key','asset_number','_ocr_id_text_variants',
    '_edit_distance','_best_known_id','_rank_asset_candidates',
    '_asset_id_parts','_authoritative_asset_candidates','_new_suffix_asset_candidates',
    '_base_asset_key','_endpoint_base_options','_new_pipe_base_item',
    '_best_observed_asset_id','_resolve_full_asset','_resolve_pipe_pair',
    'review_status','record_needs_review','new_asset_base_info',
}
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted]
module=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(module)
namespace={'re':re}
exec(compile(module,str(SOURCE),'exec'),namespace)


known_manholes={
    'DE1234':{'row':2,'asset':'DE-1234','asset_key':'DE1234'},
    'DE1235':{'row':3,'asset':'DE-1235','asset_key':'DE1235'},
}
item,status=namespace['_resolve_full_asset'](['DE-1234'],known_manholes)
assert status=='Matched' and item['asset']=='DE-1234'

# A complete suffix is authoritative and must not be corrected to DE-1234.
item,status=namespace['_resolve_full_asset'](['DE-1234A'],known_manholes)
assert item is None and status=='NEW MANHOLE'
assert namespace['_best_observed_asset_id'](['DE-1234A'],known_manholes)=='DE-1234A'

# A common OCR letter-for-digit error can still recover an exact master ID.
item,status=namespace['_resolve_full_asset'](['DE-I234'],known_manholes)
assert status=='Matched' and item['asset']=='DE-1234'

# A complete but unrelated value remains NOT MATCHED rather than being labeled new.
item,status=namespace['_resolve_full_asset'](['DE-9999'],known_manholes)
assert item is None and status=='NOT MATCHED'

# A different final digit is not a new asset; only one appended letter qualifies.
item,status=namespace['_resolve_full_asset'](['DE-1236'],known_manholes)
assert status!='NEW MANHOLE'

pipe_item={
    'row':8,'pipe_id':'P-1','up':'DE-1234','down':'DE-1235',
    'up_key':'DE1234','down_key':'DE1235','expected':200.0,
}
master={
    'pipe_items':[pipe_item],
    'manholes':known_manholes,
    'pipes':{
        ('DE1234','DE1235'):pipe_item,
        ('DE1235','DE1234'):{**pipe_item,'reverse':True},
    },
}
match,status=namespace['_resolve_pipe_pair'](['DE-1234'],['DE-1235'],master)
assert status=='Matched' and match['row']==8

# Do not turn DE-1234 -> DE-1234A into the nearby DE-1234 -> DE-1235 master pipe.
match,status=namespace['_resolve_pipe_pair'](['DE-1234'],['DE-1234A'],master)
assert match is None and status=='NEW PIPE'
endpoints={'DE1234':'DE-1234','DE1235':'DE-1235'}
assert namespace['_best_observed_asset_id'](['DE-1234'],endpoints)=='DE-1234'
assert namespace['_best_observed_asset_id'](['DE-1234A'],endpoints)=='DE-1234A'

# Upstream-only, downstream-only, and both-new endpoint combinations all qualify.
for up,down in (
    ('DE-1234A','DE-1235'),
    ('DE-1234','DE-1235A'),
    ('DE-1234A','DE-1235B'),
):
    match,status=namespace['_resolve_pipe_pair']([up],[down],master)
    assert match is None and status=='NEW PIPE',(up,down,status)

# Suffixes alone are not enough: the unsuffixed endpoint pair must identify the
# exact base pipe row that the new version will be inserted beneath.
no_base={**master,'pipes':{},'pipe_items':[]}
match,status=namespace['_resolve_pipe_pair'](['DE-1234A'],['DE-1235'],no_base)
assert status!='NEW PIPE'

# Numeric-style Reno identifiers use the same explicit trailing-letter rule.
assert namespace['_best_known_id'](['12345'],['12345'])=='12345'
assert namespace['_new_suffix_asset_candidates'](['12345A'],['12345'])==['12345A']
assert namespace['_new_suffix_asset_candidates'](['12346'],['12345'])==[]
new_row={'status':'NEW PIPE','warnings':[]}
assert namespace['review_status'](new_row)=='NEW PIPE'
assert namespace['record_needs_review'](new_row)
approved_row={'status':'NEW PIPE','warnings':[],'new_asset_approved':True}
assert namespace['review_status'](approved_row)=='NEW PIPE — APPROVED FOR MASTER'
assert not namespace['record_needs_review'](approved_row)

mh_info=namespace['new_asset_base_info'](
    {'status':'NEW MANHOLE','asset':'DE-1234A'},master)
assert mh_info=={'kind':'Manhole','row':2,'base_asset':'DE-1234'}
pipe_info=namespace['new_asset_base_info'](
    {'status':'NEW PIPE','kind':'Pipe','up':'DE-1234A','down':'DE-1235','asset':''},master)
assert pipe_info=={'kind':'Pipe','row':8,'base_asset':'DE-1234 -> DE-1235'}
both_info=namespace['new_asset_base_info'](
    {'status':'NEW PIPE','kind':'Pipe','up':'DE-1234A','down':'DE-1235B','asset':''},master)
assert both_info==pipe_info

reno_master={'manholes':{},'pipes':{},'pipe_items':[],
             'pipe_by_id':{'12345':{'row':11,'pipe_id':'12345'}}}
reno_info=namespace['new_asset_base_info'](
    {'status':'NEW PIPE','kind':'Pipe','up':'','down':'','asset':'12345A'},reno_master)
assert reno_info=={'kind':'Pipe','row':11,'base_asset':'12345'}

print('Exact matching and NEW MANHOLE/NEW PIPE safeguards passed.')
