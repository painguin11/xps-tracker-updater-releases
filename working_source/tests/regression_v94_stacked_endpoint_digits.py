from pathlib import Path
import ast
import re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(s)

# The pair parser must keep the new OCR pass lazy and use its per-band evidence
# only in the existing conservative numeric-body recovery path.
start=s.index('def parse_year15_pair_list')
end=s.index('\ndef parse_year15_manholes',start)
block=s[start:end]
for required in (
    'batch_up_digit_endpoints=None',
    'batch_dn_digit_endpoints=None',
    '_batch_pair_endpoint_digit_candidates(img,bands,table,up_box)',
    '_batch_pair_endpoint_digit_candidates(img,bands,table,dn_box)',
    'up_extra=batch_up_digit_endpoints.get(band_index,[])',
    'dn_extra=batch_dn_digit_endpoints.get(band_index,[])',
):
    assert required in block, required

# Exercise the stack/mapping helper without relying on runner Tesseract output.
helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_batch_pair_endpoint_digit_candidates')
class FakeTesseract:
    class Output:
        DICT=dict
    calls=0
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        FakeTesseract.calls+=1
        # Three padded tiles are stacked. Put one observed token in the middle tile.
        assert image.ndim==2 and image.shape[0]>120
        middle=image.shape[0]//2
        return {'text':['1912'],'top':[middle-5],'height':[10]}
ns={'np':np,'cv2':cv2,'re':re,'pytesseract':FakeTesseract}
exec(compile(ast.Module(body=[helper],type_ignores=[]),str(SOURCE),'exec'),ns)
img=np.full((60,120,3),255,dtype=np.uint8)
bands=[(0,20),(20,40),(40,60)]
result=ns['_batch_pair_endpoint_digit_candidates'](img,bands,(0,120),(0.0,0.5))
assert result.get(1)==['1912'],result
assert FakeTesseract.calls==2

# Extra PDF-observed stacked digits may recover an existing pair even if the
# isolated-cell OCR returns nothing. The master still cannot invent either side.
for name in ('_asset_body_digits','_digit_token_asset_body_quality','_digit_token_matches_asset_body','_resolve_pipe_pair_from_endpoint_digits'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
ns['_endpoint_digit_tokens']=lambda _cell: []
master={'pipe_items':[
    {'row':109,'up':'DN-1911','down':'DN-1912'},
    {'row':110,'up':'DN-1913','down':'DN-1911'},
]}
cell=np.full((30,80,3),255,dtype=np.uint8)
resolved=ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,master,up_extra=['1911'],dn_extra=['1912'])
assert resolved and resolved['row']==109,resolved

# A fully printed but non-master pair remains unresolved even when both numeric
# bodies are clearly observed by the stacked fallback.
assert ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,master,up_extra=['777'],dn_extra=['1762']) is None
assert ns['_resolve_pipe_pair_from_endpoint_digits'](
    cell,cell,master,up_extra=['1698'],dn_extra=['1697']) is None

print('v94 stacked endpoint digit recovery regression passed')
