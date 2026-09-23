from pathlib import Path
import ast
import re

source_path=Path(__file__).resolve().parents[1] / 'app' / 'reno_scan_updater.py'
source=source_path.read_text(encoding='utf-8')
tree=ast.parse(source)
needed={
    'canonical_asset_id','asset_key','asset_number','_ocr_id_text_variants','_edit_distance',
    '_rank_asset_candidates','_asset_id_parts','_authoritative_asset_candidates',
    '_new_suffix_asset_candidates','_endpoint_base_options','_new_pipe_base_item',
    '_resolve_pipe_pair','_header_role'
}
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in needed]
found={node.name for node in nodes}
missing=needed-found
assert not missing, f'missing source functions: {sorted(missing)}'
module=ast.Module(body=nodes,type_ignores=[])
ast.fix_missing_locations(module)
ns={'re':re}
exec(compile(module,str(source_path),'exec'),ns)

pipe_a={'row':10,'up':'DN-797','down':'DN-1763','up_key':'DN797','down_key':'DN1763','pipe_id':'P-A','expected':40}
pipe_b={'row':11,'up':'DN-1911','down':'DN-1912','up_key':'DN1911','down_key':'DN1912','pipe_id':'P-B','expected':296}
master={
    'pipe_items':[pipe_a,pipe_b],
    'pipes':{('DN797','DN1763'):pipe_a,('DN1911','DN1912'):pipe_b},
    'manholes':{}
}

item,status=ns['_resolve_pipe_pair'](['DN-797'],['DN-1763'],master)
assert item is pipe_a and status=='Matched', (item,status)

item,status=ns['_resolve_pipe_pair'](['DN-777'],['DN-1762'],master)
assert item is None and status=='NOT MATCHED', (item,status)

known={'DN1911':'DN-1911','DN1912':'DN-1912'}
repaired=ns['_authoritative_asset_candidates'](['IDN-1912'],known)
assert repaired==['DN-1912'], repaired
item,status=ns['_resolve_pipe_pair'](['DN-1911'],['IDN-1912'],master)
assert item is pipe_b and status=='Matched', (item,status)

assert ns['_header_role']('ilenethsurveved','pipes')=='value'
assert ns['_header_role']('lengthsurveyed','pipes')=='value'
print('v89 printed-pair identity, grid-prefix recovery, and header OCR regression passed.')
