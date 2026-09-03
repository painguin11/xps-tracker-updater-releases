from pathlib import Path
import ast, re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')

# Suffixed NEW PIPE / NEW MANHOLE approvals must use a crop-capable Yes/No dialog,
# not the old messagebox path.
start=s.index('class NewAssetApprovalDialog')
end=s.index('\n\nclass UnmatchedAssetDecisionDialog',start)
d=s[start:end]
for required in ('PDF ID verification',"'upstream'","'downstream'","'asset'",
                 'ImageTk.PhotoImage(image,master=self)',"text='Yes'","text='No'"):
    assert required in d, required
commit_start=s.index('    def commit_extracted_record')
commit_end=s.index('\n    def analyze',commit_start)
commit=s[commit_start:commit_end]
assert 'NewAssetApprovalDialog(self,rec,base_info)' in commit
assert "messagebox.askyesno(\n                    f'New {label.title()} Detected'" not in commit

# Simulate the Windows failure mode: normal digit OCR returns nothing, but the
# independent padded endpoint view sees the printed numeric body.  No real OCR or
# customer fixture is required for this deterministic fallback-unit check.
tree=ast.parse(s)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_endpoint_digit_tokens')
ns={'cv2':cv2,'re':re,'_ocr_digits':lambda *_a,**_k:[],
    'cached_ocr_string':lambda *_a,**_k:'1912'}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
cell=np.full((28,90,3),255,dtype=np.uint8)
assert ns['_endpoint_digit_tokens'](cell)==['1912']

# The downstream recovery remains conservative: both OCR-observed numeric bodies
# must identify exactly one existing directional master pair.
for name in ('_asset_body_digits','_digit_token_matches_asset_body','_resolve_pipe_pair_from_endpoint_digits'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
reads=iter((['1911'],['1912']))
ns['_endpoint_digit_tokens']=lambda _cell: next(reads)
master={'pipe_items':[
    {'row':109,'up':'DN-1911','down':'DN-1912','up_key':'DN1911','down_key':'DN1912'},
    {'row':110,'up':'DN-1913','down':'DN-1911','up_key':'DN1913','down_key':'DN1911'},
]}
resolved=ns['_resolve_pipe_pair_from_endpoint_digits'](cell,cell,master)
assert resolved and resolved['up']=='DN-1911' and resolved['down']=='DN-1912', resolved

# A legitimate pair that simply does not exist in the master is still unresolved.
reads=iter((['1698'],['1697']))
ns['_endpoint_digit_tokens']=lambda _cell: next(reads)
assert ns['_resolve_pipe_pair_from_endpoint_digits'](cell,cell,master) is None
print('v91 new-asset preview + conservative endpoint recovery regression passed')
