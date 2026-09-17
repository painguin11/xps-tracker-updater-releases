from pathlib import Path
import ast
from datetime import datetime
import re
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

pair_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_pair_list')
mh_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')
edit_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply_manual_asset_edit')

class _CV2Stub:
    COLOR_RGB2GRAY=1
    @staticmethod
    def cvtColor(image,code):
        return image[:,:,0] if getattr(image,'ndim',0)==3 else image

class _OutputStub:
    DICT='DICT'

class _TesseractStub:
    Output=_OutputStub
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        # Whole-page token OCR intentionally sees nothing. Physical table geometry
        # is the evidence that rows exist; asset matching must not decide existence.
        return {'text':[],'left':[],'top':[],'height':[]}

class _PytesseractStub:
    Output=_OutputStub
    image_to_data=_TesseractStub.image_to_data


def asset_key(value):
    return re.sub(r'[^A-Z0-9]','',str(value or '').upper())


def canonical(value):
    raw=str(value or '').strip().upper()
    if raw=='?': return '?'
    m=re.fullmatch(r'([A-Z0-9]+)-?(\d+[A-Z]?)',raw)
    return f'{m.group(1)}-{m.group(2)}' if m and '-' in raw else raw

DATE=datetime(2026,9,16)
PIPE_ITEM={'row':7,'up':'DN-1001','down':'DN-1002','up_key':'DN1001','down_key':'DN1002',
           'expected':120.0,'pipe_id':'P-7'}
MH1={'row':11,'asset':'DN-1001','asset_key':'DN1001'}
MH2={'row':12,'asset':'DN-1015','asset_key':'DN1015'}


def resolve_pair(up_values,dn_values,master_index):
    up={asset_key(v) for v in up_values}; dn={asset_key(v) for v in dn_values}
    if 'DN1001' in up and 'DN1002' in dn:
        return PIPE_ITEM,'Matched'
    return None,'NOT MATCHED'


def resolve_mh(values,known):
    exact=[]
    for value in values:
        item=known.get(asset_key(value))
        if item and item not in exact: exact.append(item)
    if len(exact)==1: return exact[0],'Matched'
    if len(exact)>1: return None,'AMBIGUOUS ASSET'
    return None,'NOT MATCHED'


def best_observed(values,known_items):
    return str(values[0]).strip().upper() if values else ''

# ---------------- Pair-table invariant: Pipe and Cleaning ----------------
PAIR_IMG=np.full((120,400,3),255,dtype=np.uint8)
PAIR_BANDS=[(10,30),(40,60)]  # one printed header band + one physical data row
PAIR_TABLE=(0,400)
PAIR_PREPARED={
    'img':PAIR_IMG,
    'bands':PAIR_BANDS,
    'table':PAIR_TABLE,
    'mapping':{'up':(0.0,.25),'down':(.25,.50),'value':(.50,.75),'date':(.75,1.0)},
    'header_band_index':0,
}

pair_ns={
    'np':np,'re':re,
    'asset_key':asset_key,'canonical_asset_id':canonical,
    '_read_sheet_date_evidence':lambda cell,expected_date=None:{'date':DATE,'strong':True,'candidates':[DATE],'votes':{},'strong_votes':{}},
    '_dominant_sheet_date':lambda reads,expected_date=None:DATE,
    '_read_pair_table_printed_total':lambda *args,**kwargs:{'found':False,'band_index':None,'value':None,'confident':False},
    '_batch_cleaning_length_candidates':lambda *args,**kwargs:{1:[120.0]},
    '_batch_pair_endpoint_candidates':lambda *args,**kwargs:{},
    '_batch_pair_endpoint_full_candidates':lambda *args,**kwargs:{},
    '_batch_pair_endpoint_digit_candidates':lambda *args,**kwargs:{},
    '_resolve_pipe_pair':resolve_pair,
    '_resolve_pipe_pair_from_endpoint_digits':lambda *args,**kwargs:None,
    '_authoritative_asset_candidates':lambda *args,**kwargs:[],
    '_ocr_known_r2_candidates':lambda *args,**kwargs:[],
    '_ocr_asset_candidates':lambda *args,**kwargs:[],
    '_best_observed_asset_id':best_observed,
    '_direct_pair_length_candidates':lambda cell:[120.0],
    '_choose_length':lambda values,expected=None:120.0 if values else None,
    '_ocr_length_candidates':lambda *args,**kwargs:[],
    '_choose_pair_length_observation':lambda values,direct,expected,cell,expanded=None:120.0,
    '_choose_cleaning_length':lambda values,expected=None:120.0 if values else None,
    '_ocr_gridless_number_candidates':lambda *args,**kwargs:[],
    '_conservative_cleaning_reread':lambda *args,**kwargs:{'confident':False,'value':None,'candidates':[]},
    '_valid_row_length_value':lambda value:value is not None and float(value)>0,
    '_date_outlier_is_well_supported':lambda *args,**kwargs:False,
    '_keep_unresolved_pair_row':lambda *args,**kwargs:True,
    'LENGTH_DIFF_THRESHOLD':4.5,
    'refresh_length_status':lambda record:None,
}
exec(compile(ast.Module(body=[pair_node,edit_node],type_ignores=[]),str(SOURCE),'exec'),pair_ns)

PAIR_MASTER={
    'asset_format':{'mode':'prefixed_dash','requires_dash':True},
    'pipe_items':[PIPE_ITEM],
    'pipes':{('DN1001','DN1002'):PIPE_ITEM},
    'manholes':{},
}
for kind in ('pipes','cleaning'):
    emitted=[]
    rows=pair_ns['parse_year15_pair_list'](
        object(),PAIR_MASTER,kind,prepared=dict(PAIR_PREPARED),on_row=emitted.append,expected_date=DATE)
    assert len(rows)==1, f'{kind}: physical data row disappeared from summary: {rows}'
    assert len(emitted)==1, f'{kind}: on_row did not receive physical row: {emitted}'
    row=rows[0]
    assert row['status']=='NOT MATCHED', f'{kind}: unresolved physical row must warn NOT MATCHED: {row}'
    assert row.get('skip_update') is True,row
    assert row.get('up')=='?' and row.get('down')=='?',row
    assert row.get('video_length')==120.0,row
    assert row.get('row_date')==DATE,row
    # Existing Edit Selected behavior must re-check matching immediately after the
    # user corrects the two endpoints.
    matched=pair_ns['apply_manual_asset_edit'](row,PAIR_MASTER,up='DN-1001',down='DN-1002')
    assert matched is True,row
    assert row.get('skip_update') is False and row.get('status')=='Matched',row

# ---------------- Manhole invariant ----------------
# Header + three physical rows. Row 2 has only the numeric body readable; row 3
# OCRs to the same ID as row 1. Neither condition permits deleting a physical row.
MH_IMG=np.full((140,400,3),255,dtype=np.uint8)
MH_BANDS=[(10,30),(40,60),(70,90),(100,120)]
MH_TABLE=(0,400)
for value,(y1,y2) in zip((240,100,150,110),MH_BANDS):
    MH_IMG[y1:y2,:,:]=value


def row_mean(cell):
    return int(round(float(np.mean(cell)))) if getattr(cell,'size',0) else 255


def mh_asset_ocr(cell,fast_plain=False,asset_format=None):
    mean=row_mean(cell)
    if 90<=mean<=120:
        return ['DN-1001']
    return []


def mh_digits(cell,decimal=False,fast_plain=False):
    return ['1015'] if 140<=row_mean(cell)<=160 else []

mh_ns={
    're':re,'np':np,'cv2':_CV2Stub,'pytesseract':_PytesseractStub,
    '_year15_oriented':lambda page,kind,preferred_deg=None:MH_IMG,
    'parse_date_text':lambda text:None,
    '_printed_asset_tokens':lambda text,asset_format:[],
    '_resolve_full_asset':resolve_mh,
    '_best_observed_asset_id':best_observed,
    'canonical_asset_id':canonical,'asset_key':asset_key,
    '_table_row_bands':lambda image,min_y,max_y:(MH_BANDS,MH_TABLE),
    '_year15_manhole_column_boxes':lambda image,bands,table:{'asset':(0.0,.25),'date':(.75,1.0),'source':'test','header_band_index':0},
    '_ocr_asset_candidates':mh_asset_ocr,
    '_ocr_digits':mh_digits,
    '_unique_manhole_digit_match':lambda cell,master_index: MH2 if ('1015' in mh_digits(cell)) else None,
    '_confirmed_suffix_asset_candidates':lambda *args,**kwargs:[],
    '_parse_sheet_date':lambda cell: DATE if row_mean(cell)<200 else None,
    'refresh_length_status':lambda record:None,
}
exec(compile(ast.Module(body=[mh_node,edit_node],type_ignores=[]),str(SOURCE),'exec'),mh_ns)
MH_MASTER={
    'asset_format':{'mode':'prefixed_dash','requires_dash':True},
    'manholes':{'DN1001':MH1,'DN1015':MH2},
    'manholes_by_number':{'1001':[MH1],'1015':[MH2]},
}
emitted=[]
rows=mh_ns['parse_year15_manholes'](object(),MH_MASTER,on_row=emitted.append)
assert len(rows)==3, f'Manhole physical rows must all remain visible; got {len(rows)}: {rows}'
assert len(emitted)==3,emitted
assert rows[0]['asset']=='DN-1001' and rows[0]['status']=='Matched',rows[0]
# Numeric-only evidence is a useful edit hint, not permission to silently fill in
# the missing prefix from the master.
assert rows[1]['asset']=='1015',rows[1]
assert rows[1]['status']=='NOT MATCHED' and rows[1].get('skip_update') is True,rows[1]
# Duplicate OCR identity is also review information, not permission to discard a row.
assert rows[2]['asset']=='DN-1001',rows[2]
assert rows[2].get('skip_update') is True,rows[2]
assert 'DUPLICATE IN PDF' in rows[2].get('validation_warnings',[]),rows[2]
# User correction must invoke the established re-match behavior.
matched=mh_ns['apply_manual_asset_edit'](rows[1],MH_MASTER,asset='DN-1015')
assert matched is True,rows[1]
assert rows[1]['asset']=='DN-1015' and rows[1].get('skip_update') is False and rows[1]['status']=='Matched',rows[1]

print('post-v105 physical Pipe/Cleaning/Manhole row retention + manual re-match regression passed')
