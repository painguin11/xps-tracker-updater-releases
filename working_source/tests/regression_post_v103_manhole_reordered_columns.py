from pathlib import Path
import ast
from datetime import datetime
import re
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
parse_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')
retry_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_retry_year15_manhole_rows')
assert 'grid_has_confirmed_new' in text or '_mh_suffix_confirmed' not in text
helper_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_year15_manhole_column_boxes')

# Reproduce the supplied 37-row B&C layout: Date is first, Manhole Number second,
# followed by Street and Drainage Area. DN-1788A is printed in the PDF, while the
# selected master contains the base DN-1788 but not DN-1788A. Some OCR views may
# see the complete suffix while another view drops the final A. The independently
# confirmed suffix must remain NEW MANHOLE rather than collapsing to the base row.
IDS=[
    'DN-1697','DN-1698','DN-1771','DN-1788','DN-1788A','DN-2138','DN-2140',
    'DN-2141','DN-2142','DN-2153','DN-2163','DN-2165','DN-2171','DN-22',
    'DN-775','DN-779','DN-789','DN-790','DN-791','DN-792','DN-795','DN-796',
    'DN-807','DN-811','DN-814','DN-815','DN-816','DN-818','DN-820','DN-823',
    'DN-824','DN-825','DN-826','DN-827','DN-877','DN-881','DN-885',
]
MASTER_IDS=[value for value in IDS if value!='DN-1788A']
H=W=1000
LEFT,RIGHT=100,900
TW=RIGHT-LEFT
HEADER=(80,96)
DATA=[(100+i*20,116+i*20) for i in range(len(IDS))]
ALL_BANDS=[HEADER]+DATA
img=np.zeros((H,W,3),dtype=np.uint8)
img[:]=255
column_edges=[LEFT,LEFT+int(.25*TW),LEFT+int(.50*TW),LEFT+int(.75*TW),RIGHT]
column_codes=[20,80,140,200]
for band_index,(y1,y2) in enumerate(ALL_BANDS):
    row_number=max(0,band_index)
    for ci,(x1,x2) in enumerate(zip(column_edges,column_edges[1:])):
        img[y1:y2,x1:x2,0]=column_codes[ci]
        img[y1:y2,x1:x2,1]=row_number
        img[y1:y2,x1:x2,2]=240

class _CV2Stub:
    COLOR_RGB2GRAY=1
    BORDER_CONSTANT=0
    THRESH_BINARY=0
    @staticmethod
    def cvtColor(image,code):
        return image[:,:,0] if getattr(image,'ndim',0)==3 else image
    @staticmethod
    def bitwise_not(image):
        return 255-image
    @staticmethod
    def threshold(image,*args):
        return (0,image)
    @staticmethod
    def copyMakeBorder(image,*args,**kwargs):
        return image

class _OutputStub:
    DICT='DICT'

class _TesseractStub:
    Output=_OutputStub
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        ih,iw=image.shape[:2]
        if (ih,iw)==(H,W):
            # Whole-page OCR remains intentionally partial so the physical ruled-row
            # path is exercised. The bug itself is in mixed base/suffix cell evidence.
            return {
                'text':['DN-2142','DN-885'],
                'left':[250,250],
                'top':[DATA[8][0],DATA[-1][0]],
                'height':[12,12],
            }
        return {
            'text':['Date','Manhole','Number','Street','Drainage','Area'],
            'left':[int(iw*.01),int(iw*.25),int(iw*.34),int(iw*.50),int(iw*.75),int(iw*.84)],
            'top':[2]*6,
            'width':[20]*6,
            'height':[10]*6,
        }

class _PytesseractStub:
    Output=_OutputStub
    image_to_data=_TesseractStub.image_to_data


def table_bands(image,min_y,max_y):
    return ((ALL_BANDS if max_y>=.85 else ALL_BANDS[:-1]),(LEFT,RIGHT))


def all_row_bands(image,min_y,max_y):
    return ALL_BANDS,(LEFT,RIGHT)


def row_number(cell):
    return int(round(float(np.mean(cell[:,:,1])))) if getattr(cell,'ndim',0)==3 else 0


def ocr_assets(cell,fast_plain=False,asset_format=None):
    if not getattr(cell,'size',0): return []
    red=float(np.mean(cell[:,:,0])); row=row_number(cell)
    if 55<=red<=105 and 1<=row<=len(IDS):
        value=IDS[row-1]
        # This is the real failure class: independent OCR passes disagree only on
        # the final suffix, so the old exact-first resolver silently chose DN-1788.
        if value=='DN-1788A':
            return ['DN-1788','DN-1788A']
        return [value]
    return []


def confirmed_suffixes(cell,known_items,asset_format=None):
    row=row_number(cell)
    return ['DN-1788A'] if row==5 else []


def parse_sheet_date(cell):
    if not getattr(cell,'size',0): return None
    red=float(np.mean(cell[:,:,0]))
    return datetime(2026,9,14) if red<45 else None


def asset_key(value):
    return re.sub(r'[^A-Z0-9]','',str(value or '').upper())

known={asset_key(value):{'asset':value,'asset_key':asset_key(value)} for value in MASTER_IDS}

def resolve(values,known_items):
    # Mirror production's conservative exact-first behavior. Without the new
    # independent suffix confirmation, ['DN-1788','DN-1788A'] becomes Matched DN-1788.
    exact=[]
    for value in values:
        item=known_items.get(asset_key(value))
        if item and item not in exact: exact.append(item)
    if len(exact)==1:
        return exact[0],'Matched'
    if len(exact)>1:
        return None,'AMBIGUOUS ASSET'
    for value in values:
        key=asset_key(value)
        if len(key)>1 and key[-1].isalpha() and key[:-1] in known_items and key not in known_items:
            return None,'NEW MANHOLE'
    return None,'NOT MATCHED'


def best_observed(values,known_items):
    for value in values:
        key=asset_key(value)
        if len(key)>1 and key[-1].isalpha() and key[:-1] in known_items and key not in known_items:
            return value
    return values[0] if values else ''

ns={
    're':re,'np':np,'cv2':_CV2Stub,'pytesseract':_PytesseractStub,
    '_year15_oriented':lambda page,kind,preferred_deg=None: img,
    'parse_date_text':lambda value:None,
    '_printed_asset_tokens':lambda value,asset_format:[str(value)] if str(value) in ('DN-2142','DN-885') else [],
    '_resolve_full_asset':resolve,
    '_best_observed_asset_id':best_observed,
    'canonical_asset_id':lambda value:str(value).strip().upper(),
    'asset_key':asset_key,
    '_table_row_bands':table_bands,
    '_year15_all_row_bands':all_row_bands,
    '_ocr_asset_candidates':ocr_assets,
    '_confirmed_suffix_asset_candidates':confirmed_suffixes,
    '_parse_sheet_date':parse_sheet_date,
    'cached_ocr_string':lambda image,config='':'',
}
for node in (helper_node,parse_node,retry_node):
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

emitted=[]
rows=ns['parse_year15_manholes'](
    object(),
    {'asset_format':{'mode':'prefixed_dash'},'manholes':known},
    on_row=emitted.append,
)
assert len(rows)==37, f'expected 37 physical rows including NEW DN-1788A; got {len(rows)} rows: {[row["asset"] for row in rows]}'
assert [row['asset'] for row in rows]==IDS, f'expected exact 37-row asset order including NEW DN-1788A; got assets: {[row["asset"] for row in rows]}'
new_rows=[row for row in rows if row['asset']=='DN-1788A']
assert len(new_rows)==1,new_rows
assert new_rows[0]['status']=='NEW MANHOLE',new_rows[0]
assert new_rows[0].get('skip_update') is True,new_rows[0]
assert new_rows[0].get('_mh_suffix_confirmed') is True,new_rows[0]
assert len(emitted)==37,emitted
assert all(row['row_date']==datetime(2026,9,14) for row in rows),rows

retry_rows=ns['_retry_year15_manhole_rows'](
    object(),
    {'asset_format':{'mode':'prefixed_dash'},'manholes':known},
)
assert len(retry_rows)==37,retry_rows
retry_new=[row for row in retry_rows if row['asset']=='DN-1788A']
assert len(retry_new)==1,retry_new
assert retry_new[0]['status']=='NEW MANHOLE',retry_new[0]
assert retry_new[0].get('_mh_suffix_confirmed') is True,retry_new[0]

print('post-v103 reordered Manhole-column + confirmed NEW MANHOLE regression passed')
