from pathlib import Path
import importlib.util
import sys
import types

import numpy as np

APP=Path('working_source/app/reno_scan_updater.py')
src=APP.read_text(encoding='utf-8')

# Source-level guarantees for the edit UI and parser wiring.
for required in (
    'def _batch_pair_endpoint_candidates(',
    'batch_up_endpoints=_batch_pair_endpoint_candidates(',
    'batch_dn_endpoints=_batch_pair_endpoint_candidates(',
    "'upstream':up_preview.copy()",
    "'downstream':dn_preview.copy()",
    "'asset':asset_preview.copy()",
    "fields=[('Upstream Node','upstream'),('Downstream Node','downstream')",
    "fields=[('Asset','asset'),('Date','date')",
    "apply_manual_asset_edit(r,self.master_index,vars['Upstream Node'].get(),vars['Downstream Node'].get())",
    "apply_manual_asset_edit(r,self.master_index,asset=vars['Asset'].get())",
    'def _resolve_pipe_pair_from_endpoint_digits(',
    'digit_match=_resolve_pipe_pair_from_endpoint_digits(cut(up_box),cut(dn_box),master_index)',
):
    assert required in src, required

# Import production source while stubbing only Windows COM modules unavailable in CI.
win32com=types.ModuleType('win32com')
client=types.ModuleType('win32com.client')
win32com.client=client
sys.modules['win32com']=win32com
sys.modules['win32com.client']=client
sys.modules['pythoncom']=types.ModuleType('pythoncom')
sys.modules['pywintypes']=types.ModuleType('pywintypes')
spec=importlib.util.spec_from_file_location('xps_v86',APP)
xps=importlib.util.module_from_spec(spec)
spec.loader.exec_module(xps)

# Whole-column OCR evidence must be mapped back to the correct physical row band.
original_data=xps.pytesseract.image_to_data
try:
    def fake_image_to_data(_image,config='',output_type=None):
        return {
            'text':['EC-1817','EC-1826'],
            'top':[15,135],
            'height':[30,30],
        }
    xps.pytesseract.image_to_data=fake_image_to_data
    image=np.zeros((80,200,3),dtype=np.uint8)
    bands=[(0,40),(40,80)]
    got=xps._batch_pair_endpoint_candidates(
        image,bands,(0,200),(0.0,0.5),
        {'mode':'prefixed_dash','requires_dash':True,'max_digits':4,'max_prefix_len':2,'allow_suffix':True})
    assert got[0]==['EC-1817'],got
    assert got[1]==['EC-1826'],got
finally:
    xps.pytesseract.image_to_data=original_data

# A user correction in Edit Selected must immediately become a real matched master row.
pipe={'row':7,'expected':284.6,'pipe_id':'EC1817EC1801','up':'EC-1817','down':'EC-1801',
      'up_key':'EC1817','down_key':'EC1801'}
master={'pipe_items':[pipe],
        'pipes':{('EC1817','EC1801'):pipe},
        'manholes':{'EC1817':{'row':1,'asset':'EC-1817','asset_key':'EC1817'}}}
record={'kind':'Pipe','up':'?','down':'?','video_length':284.65,'status':'NOT MATCHED','skip_update':True}
assert xps.apply_manual_asset_edit(record,master,'EC-1817','EC-1801')
assert (record['up'],record['down'])==('EC-1817','EC-1801')
assert record['status']=='Matched' and record['skip_update'] is False
assert record['master_length']==284.6

mh={'kind':'Manhole','asset':'?','status':'NOT MATCHED','skip_update':True}
assert xps.apply_manual_asset_edit(mh,master,asset='EC-1817')
assert mh['asset']=='EC-1817' and mh['status']=='Matched' and mh['skip_update'] is False


# Prefix-loss recovery must use both endpoint cells and fail closed on ambiguity.
original_digit_tokens=xps._endpoint_digit_tokens
try:
    xps._endpoint_digit_tokens=lambda cell:list(cell)
    pair_a={'row':1,'expected':188.8,'pipe_id':'EC1826EC1817','up':'EC-1826','down':'EC-1817',
            'up_key':'EC1826','down_key':'EC1817'}
    pair_b={'row':2,'expected':390.5,'pipe_id':'R2335R2336','up':'R2-335','down':'R2-336',
            'up_key':'R2335','down_key':'R2336'}
    pair_c={'row':3,'expected':250.0,'pipe_id':'DN1826DN1900','up':'DN-1826','down':'DN-1900',
            'up_key':'DN1826','down_key':'DN1900'}
    digit_master={'pipe_items':[pair_a,pair_b,pair_c]}
    assert xps._resolve_pipe_pair_from_endpoint_digits(['1826','11826'],['1817'],digit_master)['row']==1
    assert xps._resolve_pipe_pair_from_endpoint_digits(['12335'],['12336'],digit_master)['row']==2
    assert xps._resolve_pipe_pair_from_endpoint_digits([],['1817'],digit_master) is None
    ambiguous={'pipe_items':[pair_a,dict(pair_a,row=4,up='DN-1826',down='DN-1817',up_key='DN1826',down_key='DN1817')]}
    assert xps._resolve_pipe_pair_from_endpoint_digits(['1826'],['1817'],ambiguous) is None
finally:
    xps._endpoint_digit_tokens=original_digit_tokens

print('v86 asset OCR evidence + editable asset/node regression passed.')
