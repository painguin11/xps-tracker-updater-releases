from pathlib import Path
import ast
from datetime import datetime
import re
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
parse_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')
helper_nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_year15_manhole_column_boxes']

# Reproduce the September 15 B&C layout: Date is first, Manhole Number second,
# followed by Street and Drainage Area. The table is long enough that its final
# printed row falls below the old 72%-of-page Manhole scan limit.
IDS=[
    'DN-1697','DN-1698','DN-1771','DN-1788','DN-1788A','DN-2138','DN-2140',
    'DN-2141','DN-2142','DN-2153','DN-2163','DN-2165','DN-2171','DN-22',
    'DN-775','DN-779','DN-789','DN-790','DN-791','DN-792','DN-795','DN-796',
    'DN-807','DN-811','DN-814','DN-815','DN-816','DN-818','DN-820','DN-823',
    'DN-824','DN-825','DN-826','DN-827','DN-877','DN-881','DN-885',
]
H=W=1000
LEFT,RIGHT=100,900
TW=RIGHT-LEFT
HEADER=(80,96)
DATA=[(100+i*20,116+i*20) for i in range(len(IDS))]
ALL_BANDS=[HEADER]+DATA
img=np.zeros((H,W,3),dtype=np.uint8)
img[:]=255
# Encode column identity in red and physical row number in green so the OCR/date
# stubs can tell which printed cell the real parser cropped without knowing x/y.
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
    @staticmethod
    def cvtColor(image,code):
        # Whole-page OCR only needs a distinct 2-D shape. Header-role OCR may also
        # receive this output and is distinguished by its resized dimensions.
        return image[:,:,0] if getattr(image,'ndim',0)==3 else image

class _OutputStub:
    DICT='DICT'

class _TesseractStub:
    Output=_OutputStub
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        ih,iw=image.shape[:2]
        if (ih,iw)==(H,W):
            # Old whole-page OCR sees only two valid IDs, exactly the partial-token
            # failure class fixed in v103. Grid parsing must therefore win.
            return {
                'text':['DN-2142','DN-885'],
                'left':[250,250],
                'top':[DATA[8][0],DATA[-1][0]],
                'height':[12,12],
            }
        # Header OCR for the reordered four-column table. Positions are expressed
        # as fractions so the regression does not depend on a particular upscale.
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
    # The historical .72 limit loses the last physical row. The corrected Manhole
    # path must inspect the longer table extent.
    return ((ALL_BANDS if max_y>=.85 else ALL_BANDS[:-1]),(LEFT,RIGHT))


def ocr_assets(cell,fast_plain=False,asset_format=None):
    if not getattr(cell,'size',0): return []
    red=float(np.mean(cell[:,:,0])); row=int(round(float(np.mean(cell[:,:,1]))))
    if 55<=red<=105 and 1<=row<=len(IDS):
        return [IDS[row-1]]
    return []


def parse_sheet_date(cell):
    if not getattr(cell,'size',0): return None
    red=float(np.mean(cell[:,:,0]))
    return datetime(2026,9,14) if red<45 else None

known={value.replace('-',''):{'asset':value,'asset_key':value.replace('-','')} for value in IDS}

def resolve(values,known_items):
    for value in values:
        key=str(value).replace('-','')
        item=known_items.get(key)
        if item: return item,'Matched'
    return None,'NOT MATCHED'

ns={
    're':re,'np':np,'cv2':_CV2Stub,'pytesseract':_PytesseractStub,
    '_year15_oriented':lambda page,kind,preferred_deg=None: img,
    'parse_date_text':lambda value:None,
    '_printed_asset_tokens':lambda value,asset_format:[str(value)] if str(value) in ('DN-2142','DN-885') else [],
    '_resolve_full_asset':resolve,
    '_best_observed_asset_id':lambda values,known_items:values[0] if values else '',
    'canonical_asset_id':lambda value:str(value).strip().upper(),
    '_table_row_bands':table_bands,
    '_ocr_asset_candidates':ocr_assets,
    '_parse_sheet_date':parse_sheet_date,
}
for node in helper_nodes+[parse_node]:
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

emitted=[]
rows=ns['parse_year15_manholes'](
    object(),
    {'asset_format':{'mode':'prefixed_dash'},'manholes':known},
    on_row=emitted.append,
)
assert len(rows)==37,rows
assert [row['asset'] for row in rows]==IDS,[row['asset'] for row in rows]
assert len(emitted)==37,emitted
assert all(row['status']=='Matched' for row in rows),rows
assert all(row['row_date']==datetime(2026,9,14) for row in rows),rows

print('post-v103 reordered Manhole-column regression passed')
