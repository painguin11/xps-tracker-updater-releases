from pathlib import Path
import ast,re
from datetime import datetime
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8'); tree=ast.parse(text)
pair_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_pair_list')
mh_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')
edit_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply_manual_asset_edit')

class CV2:
    COLOR_RGB2GRAY=1
    @staticmethod
    def cvtColor(image,code): return image[:,:,0] if getattr(image,'ndim',0)==3 else image
class Output: DICT='DICT'
class Tess:
    Output=Output
    @staticmethod
    def image_to_data(image,config='',output_type=None): return {'text':[],'left':[],'top':[],'height':[]}
class Pytess: Output=Output; image_to_data=Tess.image_to_data

def key(v): return re.sub(r'[^A-Z0-9]','',str(v or '').upper())
def canonical(v): return str(v or '').strip().upper()
def best(values,known): return str(values[0]).strip().upper() if values else ''
DATE=datetime(2026,9,16)
PIPE={'row':7,'up':'DN-1001','down':'DN-1002','up_key':'DN1001','down_key':'DN1002','expected':120.0,'pipe_id':'P-7'}
MH1={'row':11,'asset':'DN-1001','asset_key':'DN1001'}
MH2={'row':12,'asset':'DN-1015','asset_key':'DN1015'}

def resolve_pair(ups,dns,master):
    return (PIPE,'Matched') if 'DN1001' in {key(v) for v in ups} and 'DN1002' in {key(v) for v in dns} else (None,'NOT MATCHED')
def resolve_mh(values,known):
    hits=[]
    for value in values:
        item=known.get(key(value))
        if item and item not in hits: hits.append(item)
    return (hits[0],'Matched') if len(hits)==1 else (None,'NOT MATCHED' if not hits else 'AMBIGUOUS ASSET')

# Pipe/Cleaning: a structurally confirmed row with unreadable endpoints must still
# reach Live Summary as review-only, preserving any readable length/date.
img=np.full((120,400,3),255,dtype=np.uint8)
bands=[(10,30),(40,60)]
prepared={'img':img,'bands':bands,'table':(0,400),
          'mapping':{'up':(0,.25),'down':(.25,.5),'value':(.5,.75),'date':(.75,1)},
          'header_band_index':0}
ns={'np':np,'re':re,'datetime':datetime,'asset_key':key,'canonical_asset_id':canonical,
    '_read_sheet_date_evidence':lambda *a,**k:{'date':DATE,'strong':True,'candidates':[DATE],'votes':{},'strong_votes':{}},
    '_dominant_sheet_date':lambda *a,**k:DATE,
    '_read_pair_table_printed_total':lambda *a,**k:{'found':False,'band_index':None,'value':None,'confident':False},
    '_batch_cleaning_length_candidates':lambda *a,**k:{1:[120.0]},
    '_batch_pair_endpoint_candidates':lambda *a,**k:{},'_batch_pair_endpoint_full_candidates':lambda *a,**k:{},
    '_batch_pair_endpoint_digit_candidates':lambda *a,**k:{},'_resolve_pipe_pair':resolve_pair,
    '_resolve_pipe_pair_from_endpoint_digits':lambda *a,**k:None,'_authoritative_asset_candidates':lambda *a,**k:[],
    '_ocr_known_r2_candidates':lambda *a,**k:[],'_ocr_asset_candidates':lambda *a,**k:[],
    '_best_observed_asset_id':best,'_direct_pair_length_candidates':lambda cell:[120.0],
    '_choose_length':lambda values,expected=None:120.0 if values else None,'_ocr_length_candidates':lambda *a,**k:[],
    '_choose_pair_length_observation':lambda *a,**k:120.0,'_choose_cleaning_length':lambda values,expected=None:120.0 if values else None,
    '_ocr_gridless_number_candidates':lambda *a,**k:[],'_conservative_cleaning_reread':lambda *a,**k:{'confident':False,'value':None,'candidates':[]},
    '_valid_row_length_value':lambda v:v is not None and float(v)>0,'_date_outlier_is_well_supported':lambda *a,**k:False,
    '_keep_unresolved_pair_row':lambda *a,**k:True,'LENGTH_DIFF_THRESHOLD':4.5,'refresh_length_status':lambda r:None}
exec(compile(ast.Module(body=[pair_node,edit_node],type_ignores=[]),str(SOURCE),'exec'),ns)
master={'asset_format':{'mode':'prefixed_dash','requires_dash':True},'pipe_items':[PIPE],
        'pipes':{('DN1001','DN1002'):PIPE},'manholes':{}}
for kind in ('pipes','cleaning'):
    emitted=[]; rows=ns['parse_year15_pair_list'](object(),master,kind,prepared=dict(prepared),on_row=emitted.append,expected_date=DATE)
    assert len(rows)==1 and len(emitted)==1,f'{kind}: physical row disappeared: {rows}'
    row=rows[0]
    assert row['status']=='NOT MATCHED' and row.get('skip_update') is True,row
    assert row.get('up')=='?' and row.get('down')=='?' and row.get('video_length')==120.0 and row.get('row_date')==DATE,row
    assert ns['apply_manual_asset_edit'](row,master,up='DN-1001',down='DN-1002') is True,row
    assert row['status']=='Matched' and row.get('skip_update') is False,row

# Manholes: missing full-ID OCR and duplicate OCR identity are review conditions,
# never permission to remove a physical row. Numeric-only OCR is only an edit hint;
# it must not silently pull a prefix/identity from the master.
mh_img=np.full((140,400,3),255,dtype=np.uint8)
mh_bands=[(10,30),(40,60),(70,90),(100,120)]
for value,(y1,y2) in zip((240,100,150,110),mh_bands): mh_img[y1:y2,:,:]=value
def mean(cell): return int(round(float(np.mean(cell)))) if getattr(cell,'size',0) else 255
def mh_ocr(cell,fast_plain=False,asset_format=None): return ['DN-1001'] if 90<=mean(cell)<=120 else []
def mh_digits(cell,decimal=False,fast_plain=False): return ['1015'] if 140<=mean(cell)<=160 else []
mh_ns={'re':re,'np':np,'cv2':CV2,'pytesseract':Pytess,'_year15_oriented':lambda *a,**k:mh_img,
       'parse_date_text':lambda t:None,'_printed_asset_tokens':lambda *a,**k:[],'_resolve_full_asset':resolve_mh,
       '_best_observed_asset_id':best,'canonical_asset_id':canonical,'asset_key':key,
       '_table_row_bands':lambda *a,**k:(mh_bands,(0,400)),
       '_year15_manhole_column_boxes':lambda *a,**k:{'asset':(0,.25),'date':(.75,1),'source':'test','header_band_index':0},
       '_ocr_asset_candidates':mh_ocr,'_ocr_digits':mh_digits,
       '_unique_manhole_digit_match':lambda cell,master:MH2 if '1015' in mh_digits(cell) else None,
       '_confirmed_suffix_asset_candidates':lambda *a,**k:[],
       '_parse_sheet_date':lambda cell:DATE if mean(cell)<200 else None,'refresh_length_status':lambda r:None}
exec(compile(ast.Module(body=[mh_node,edit_node],type_ignores=[]),str(SOURCE),'exec'),mh_ns)
mh_master={'asset_format':{'mode':'prefixed_dash','requires_dash':True},
           'manholes':{'DN1001':MH1,'DN1015':MH2},'manholes_by_number':{'1001':[MH1],'1015':[MH2]}}
emitted=[]; rows=mh_ns['parse_year15_manholes'](object(),mh_master,on_row=emitted.append)
assert len(rows)==3 and len(emitted)==3,f'Manhole physical rows disappeared: {rows}'
assert rows[0]['asset']=='DN-1001' and rows[0]['status']=='Matched',rows[0]
assert rows[1]['asset']=='1015' and rows[1]['status']=='NOT MATCHED' and rows[1].get('skip_update') is True,rows[1]
assert rows[2]['asset']=='DN-1001' and rows[2].get('skip_update') is True,rows[2]
assert 'DUPLICATE IN PDF' in rows[2].get('validation_warnings',[]),rows[2]
assert mh_ns['apply_manual_asset_edit'](rows[1],mh_master,asset='DN-1015') is True,rows[1]
assert rows[1]['asset']=='DN-1015' and rows[1]['status']=='Matched' and rows[1].get('skip_update') is False,rows[1]
print('post-v105 physical Pipe/Cleaning/Manhole row retention + manual re-match regression passed')
