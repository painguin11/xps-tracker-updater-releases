from pathlib import Path
import ast
from datetime import datetime
import re
import numpy as np
import cv2
from PIL import Image

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

def node(name):
    return next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name),None)

classify_node=node('classify_for_profile')
parse_node=node('parse_year15_manholes')
assert classify_node is not None
assert parse_node is not None

# Page 6 failure class: low-res PSM 11 misses the printed activity header.
def synthetic_render(_page,scale=2.0):
    high=float(scale)>=2.0
    h,w=(240,160) if high else (120,80)
    image=np.full((h,w,3),255,dtype=np.uint8)
    image[0,0]=10
    image[0,-1]=20
    image[-1,0]=30
    image[-1,-1]=40
    return image

def synthetic_ocr(image,psm=6):
    marker=int(image[0,0,0]) if getattr(image,'size',0) else 0
    if psm==6 and marker==30:
        return 'Section No Date Drainage Area Upstream MH Downstream MH Street Length Surveyed'
    return 'scan text without a readable activity header'

classify_ns={
    'render_page':synthetic_render,
    'ocr_text':synthetic_ocr,
    '_ocr_digits':lambda *args,**kwargs:[],
    're':re,'np':np,'Image':Image,
}
exec(compile(ast.Module(body=[classify_node],type_ignores=[]),str(SOURCE),'exec'),classify_ns)
_oriented,deg,_text,kind=classify_ns['classify_for_profile'](object(),'phase2_year1')
assert kind=='pipes',f'expected weak rotated Length Surveyed page to classify as pipes; got {kind!r} at {deg}°'
assert deg==270,f'expected high-resolution header retry to recover 270° orientation; got {deg}°'

# Page 4 failure class: a physical Manhole row has clean digits but damaged prefix
# glyphs. Row existence comes from the table grid, not from successful matching.
# The program must show the row as review-only instead of silently filling DN-
# from the master or deleting the row.
H,W=320,600
LEFT,RIGHT=100,500
HEADER=(45,65)
ROW1=(75,95)
ROW2=(105,125)
BANDS=[HEADER,ROW1,ROW2]
image=np.full((H,W,3),255,dtype=np.uint8)
for code,(y1,y2) in enumerate(BANDS):
    image[y1:y2,LEFT:LEFT+160,1]=code
    image[y1:y2,LEFT:LEFT+160,0]=80
    image[y1:y2,LEFT:LEFT+160,2]=220

class _Output:
    DICT='DICT'

class _Pytesseract:
    Output=_Output
    @staticmethod
    def image_to_data(_image,config='',output_type=None):
        return {'text':[],'left':[],'top':[],'height':[]}

def row_code(cell):
    if not getattr(cell,'size',0): return -1
    return int(round(float(np.median(cell[:,:,1]))))

def ocr_assets(cell,fast_plain=False,asset_format=None):
    code=row_code(cell)
    return ['DN-1014'] if code==1 else []

def ocr_digits(cell,decimal=False,fast_plain=False):
    return ['1015'] if row_code(cell)==2 else []

def asset_key(value):
    return re.sub(r'[^A-Z0-9]','',str(value or '').upper())

item14={'asset':'DN-1014','asset_key':'DN1014'}
item15={'asset':'DN-1015','asset_key':'DN1015'}
known={'DN1014':item14,'DN1015':item15}
master={
    'asset_format':{'mode':'prefixed_dash','requires_dash':True,'max_digits':4,'max_prefix_len':2,'allow_suffix':True},
    'manholes':known,
    'manholes_by_number':{'1014':[item14],'1015':[item15]},
}

def resolve(values,known_items):
    exact=[known_items[asset_key(v)] for v in values if asset_key(v) in known_items]
    exact=list({item['asset_key']:item for item in exact}.values())
    if len(exact)==1: return exact[0],'Matched'
    return None,'NOT MATCHED'

parse_ns={
    're':re,'np':np,'cv2':cv2,'pytesseract':_Pytesseract,
    '_year15_oriented':lambda page,kind,preferred_deg=None:image,
    'parse_date_text':lambda value:None,
    '_printed_asset_tokens':lambda value,asset_format:[],
    '_resolve_full_asset':resolve,
    '_best_observed_asset_id':lambda values,known_items:values[0] if values else '',
    'canonical_asset_id':lambda value:str(value).strip().upper(),
    'asset_key':asset_key,
    '_table_row_bands':lambda img,min_y,max_y:(BANDS,(LEFT,RIGHT)),
    '_year15_manhole_column_boxes':lambda img,bands,table:{'asset':(0.0,.40),'date':(.75,1.0),'source':'test','header_band_index':0},
    '_ocr_asset_candidates':ocr_assets,
    '_ocr_digits':ocr_digits,
    '_confirmed_suffix_asset_candidates':lambda *args,**kwargs:[],
    '_parse_sheet_date':lambda cell:datetime(2026,9,15),
    'cached_ocr_string':lambda image,config='':'',
}
exec(compile(ast.Module(body=[parse_node],type_ignores=[]),str(SOURCE),'exec'),parse_ns)

rows=parse_ns['parse_year15_manholes'](object(),master)
assert len(rows)==2,f'expected both physical Manhole rows; got {rows}'
assert rows[0]['asset']=='DN-1014' and rows[0]['status']=='Matched',rows[0]
assert rows[1]['asset']=='1015',rows[1]
assert rows[1]['status']=='NOT MATCHED' and rows[1].get('skip_update') is True,rows[1]
assert rows[1].get('_field_previews',{}).get('asset') is not None,rows[1]

print('post-v105 rotated Pipe classification + visible Manhole physical-row regression passed')
