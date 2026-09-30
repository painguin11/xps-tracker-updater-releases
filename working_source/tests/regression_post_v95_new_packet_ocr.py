from pathlib import Path
import importlib.util
import sys
import types

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')

for required in (
    "match=re.fullmatch(r'([A-Z]+\\d*)-+(\\d{1,8})([A-Z]?)',punctuated)",
    "if item and not item.get('reverse'): exact_pairs[item['row']]=item",
    "if len(rule_ys)<=4 or anomalous_gap:",
    "if first_meaningful and gap<=max(12,int(bh*.025)):",
    "if all(role in detected for role in ('up','down','value','date')):",
    "if header_band_index is not None and band_index<=header_band_index:",
    "for scale in (1.6,2.5):",
    "if kind=='Cleaning' and all_rows and _valid_row_length_value(old_value):",
    "preferred_deg=item.get('effective_deg'))",
    "if not layout.get('column_boxes'):",
):
    assert required in s, required

win32com=types.ModuleType('win32com')
client=types.ModuleType('win32com.client')
win32com.client=client
sys.modules['win32com']=win32com
sys.modules['win32com.client']=client
pythoncom=types.ModuleType('pythoncom'); pythoncom.CoInitialize=lambda:None; pythoncom.CoUninitialize=lambda:None
sys.modules['pythoncom']=pythoncom
pywintypes=types.ModuleType('pywintypes'); pywintypes.com_error=Exception
sys.modules['pywintypes']=pywintypes
spec=importlib.util.spec_from_file_location('xps_post_v95_packets',SOURCE)
xps=importlib.util.module_from_spec(spec); spec.loader.exec_module(xps)

assert xps._asset_id_parts('R2-491')==('R2','491','')
assert xps._asset_id_parts('R2-414S')==('R2','414','S')

forward={'row':7,'expected':53.0,'pipe_id':'R2-489-R2-491',
         'up':'R2-489','down':'R2-491','up_key':'R2489','down_key':'R2491'}
reverse={**forward,'reverse':True}
master={'pipe_items':[forward],
        'pipes':{('R2489','R2491'):forward,('R2491','R2489'):reverse},
        'manholes':{}}
match,status=xps._resolve_pipe_pair(['R2-491'],['R2-489'],master)
assert match is None and status=='NOT MATCHED',(match,status)
match,status=xps._resolve_pipe_pair(['R2-489'],['R2-491'],master)
assert match is forward and status=='Matched',(match,status)

value,ok,source=xps._select_independent_length_candidate(
    [728.0,728.0,7.0,7.0,72.8,72.8],[722.0,722.0],'Pipe',72.419)
assert ok and value==72.8,(value,ok,source)

class Dummy: pass
d=Dummy(); d.records=[{'wo':'X','kind':'Cleaning','video_length':6.0,
                       'master_length':95.9,'_length_value_cell':'sentinel'}]
d._total_check_records=types.MethodType(xps.App._total_check_records,d)
orig=xps._independent_row_length_read
try:
    xps._independent_row_length_read=lambda *_a,**_k:{
        'value':96.0,'confident':True,'source':'synthetic independent OCR','candidates':[96.0,96.0]}
    check={'wo':'X','kind':'Cleaning','pdf_total':96.0,'pdf_total_confident':True}
    changed=xps.App._retry_length_total_mismatch(d,check,all_rows=True,force=True)
    assert changed and d.records[0]['video_length']==96.0,d.records
    assert xps._length_total_result(d.records,96.0)['matches']
finally:
    xps._independent_row_length_read=orig


# Partial role mappings must remain safe and reviewable rather than raising a
# KeyError or being treated as a fully parsed row before review.
import numpy as np
partial_prepared={
    'img':np.zeros((120,240),dtype=np.uint8),
    'bands':[(20,40),(40,60)],
    'table':(10,230),
    'mapping':{'up':(0.0,0.25),'down':(0.25,0.50)},
    'header_band_index':0,
}
partial=xps.parse_year15_pair_list(None,{'asset_format':{}},'cleaning',prepared=partial_prepared)
assert len(partial)==1 and partial[0]['asset']=='COLUMN HEADERS NOT RESOLVED',partial
assert partial[0]['skip_update'] is True,partial
assert "not all(role in roles for role in ('up','down','value','date'))" not in s

# A whole-table Pipe audit must not replace an already-valid 250 with a worse
# independently observed 260 when doing so increases the printed-total mismatch.
d2=Dummy(); d2.records=[
    {'wo':'P','kind':'Pipe','video_length':250.0,'master_length':250.0,
     '_length_value_cell':'pipe-sentinel'},
    {'wo':'P','kind':'Pipe','video_length':100.0,'master_length':100.0,
     '_length_value_cell':'other-sentinel'},
]
d2._total_check_records=types.MethodType(xps.App._total_check_records,d2)
orig=xps._independent_row_length_read
try:
    def fake_pipe(cell,*_a,**_k):
        if cell=='pipe-sentinel':
            return {'value':260.0,'confident':True,'source':'synthetic worse OCR','candidates':[260.0]}
        return {'value':100.0,'confident':True,'source':'synthetic same OCR','candidates':[100.0]}
    xps._independent_row_length_read=fake_pipe
    check={'wo':'P','kind':'Pipe','pdf_total':355.0,'pdf_total_confident':True}
    changed=xps.App._retry_length_total_mismatch(d2,check,all_rows=True,force=True)
    assert not changed,d2.records
    assert d2.records[0]['video_length']==250.0,d2.records
    assert d2.records[0].get('_length_crosscheck_conflict')==260.0,d2.records
finally:
    xps._independent_row_length_read=orig

print('Post-v95 new packet OCR/direction/total safeguards regression passed.')
