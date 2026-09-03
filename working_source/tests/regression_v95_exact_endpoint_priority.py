from pathlib import Path
import ast
import re
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(s)
ns={'re':re}
for name in ('_asset_body_digits','_digit_token_asset_body_quality','_digit_token_matches_asset_body','_resolve_pipe_pair_from_endpoint_digits'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
ns['_endpoint_digit_tokens']=lambda _cell: []
cell=np.full((20,40,3),255,dtype=np.uint8)

# Reproduce the real master collision behind DN-1911 -> DN-1912 becoming '?'.
# Exact 1911/1912 must outrank the tolerated two-leading-digit matches to 11/12.
master={'pipe_items':[
    {'row':109,'up':'DN-1911','down':'DN-1912'},
    {'row':1612,'up':'EC-11','down':'EC-12'},
]}
resolved=ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,master,up_extra=['1911'],dn_extra=['1912'])
assert resolved and resolved['row']==109,resolved

# The old grid/prefix-noise behavior still works when there is no exact body read.
resolved=ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,master,up_extra=['21911'],dn_extra=['21912'])
assert resolved and resolved['row']==109,resolved

# True prefix ambiguity must still fail closed. Both rows have exact same bodies.
ambiguous={'pipe_items':[
    {'row':302,'up':'DN-2243','down':'DN-2244'},
    {'row':1684,'up':'EC-2243','down':'EC-2244'},
]}
assert ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,ambiguous,up_extra=['2243'],dn_extra=['2244']) is None

# Fully printed non-master bodies remain unresolved.
assert ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,master,up_extra=['1698'],dn_extra=['1697']) is None
assert ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,master,up_extra=['777'],dn_extra=['1762']) is None

print('v95 exact endpoint numeric-body priority regression passed')
