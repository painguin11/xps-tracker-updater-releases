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

print('Post-v95 new packet OCR/direction/total safeguards regression passed.')
