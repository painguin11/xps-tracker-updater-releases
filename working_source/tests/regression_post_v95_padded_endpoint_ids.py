from pathlib import Path
import ast, re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')

for required in (
    'def _batch_pair_endpoint_full_candidates(',
    'if len(pass_ids)>=2',
    "if len(text)>1 and text[0] in 'IJL1'",
    "prefixes and (not parts or parts[0] not in prefixes)",
    'batch_up_full_endpoints=None; batch_dn_full_endpoints=None',
    'if padded_up: up_obs=padded_up',
    'if padded_dn: dn_obs=padded_dn',
    'authoritative_pair=(',
    "if not match and match_status!='NEW PIPE' and not authoritative_pair:",
    'if _new_suffix_asset_candidates([value],endpoint_items)',
):
    assert required in s, required

tree=ast.parse(s)
ns={'np':np,'cv2':cv2,'re':re}
for name in ('asset_key','canonical_asset_id','_asset_id_parts','_printed_asset_tokens','_batch_pair_endpoint_full_candidates'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

class FakeOutput:
    DICT='dict'
class FakePytesseract:
    Output=FakeOutput
    def __init__(self,reads): self.reads=iter(reads)
    def image_to_data(self,*_a,**_k):
        text=next(self.reads,'')
        return {'text':[text] if text else [],'top':[0] if text else [],'height':[20] if text else []}

img=np.full((40,120,3),255,np.uint8)
bands=[(0,40)]; table=(0,120); box=(0.0,1.0)
fmt={'mode':'prefixed_dash','requires_dash':True,'max_digits':4,'max_prefix_len':2,'allow_suffix':True}
known={'DN2241':'DN-2241','DN2226':'DN-2226'}

ns['pytesseract']=FakePytesseract(['DN-2241A','DN-2241A','',''])
out=ns['_batch_pair_endpoint_full_candidates'](img,bands,table,box,fmt,known)
assert out.get(0)==['DN-2241A'],out

ns['pytesseract']=FakePytesseract(['DN-2241A','','',''])
out=ns['_batch_pair_endpoint_full_candidates'](img,bands,table,box,fmt,known)
assert not out.get(0),out

ns['pytesseract']=FakePytesseract(['R2-2241','R2-2241','',''])
out=ns['_batch_pair_endpoint_full_candidates'](img,bands,table,box,fmt,known)
assert not out.get(0),out

print('Post-v95 padded complete endpoint-ID recovery regression passed.')
