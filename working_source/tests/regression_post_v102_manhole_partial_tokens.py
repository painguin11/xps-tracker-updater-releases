from pathlib import Path
import ast
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')

# The fix must remain Manhole-local: compare the positioned-token result with the
# ruled-row result and use a narrow retry rather than loosening global asset rules.
func_text=ast.get_source_segment(text,node) or ''
for required in (
    'token_out=[]',
    'grid_out=[]',
    'grid_has_confirmed_new=any(rec.get(\'_mh_suffix_confirmed\') for rec in grid_out)',
    'column_boxes=_year15_manhole_column_boxes(img,bands,table)',
    'left_trim=max(2,min(8,int(round(tw*.004))))',
    'retry_right=max(retry_left+1,asset_right-right_trim)',
    'fast_plain=True',
):
    assert required in func_text,required

IDS=[
    'DN-1752','DN-1786','DN-2031','DN-2230','DN-2231','DN-2232','DN-2233',
    'DN-2243','DN-2244','DN-2277','DN-2306','DN-2335','DN-805','DN-838',
    'DN-839','DN-884','DN-887','DN-889','DN-892','DN-893','DN-895',
]

class _CV2Stub:
    COLOR_RGB2GRAY=1
    @staticmethod
    def cvtColor(image,code):
        return image

class _OutputStub:
    DICT='DICT'

class _TesseractStub:
    Output=_OutputStub
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        # Reproduce the failure class: whole-page OCR sees only two valid IDs,
        # so the old parser returned two rows and never tried the physical grid.
        return {
            'text':['DN-2277','DN-895'],
            'left':[40,40],
            'top':[430,870],
            'height':[20,20],
        }

img=np.zeros((1000,1400,3),dtype=np.uint8)
bands=[(80+i*30,105+i*30) for i in range(23)]  # title, header, 21 data rows
table=(100,1100)
state={'wide':-1,'last_wide':-1,'retry_hits':0}

def _ocr_asset_candidates(cell,fast_plain=False,asset_format=None):
    if not fast_plain:
        state['wide']+=1
        state['last_wide']=state['wide']
        band_index=state['wide']
        if band_index<2:
            return []
        data_index=band_index-2
        if data_index==0:
            # First printed ID is lost when the left grid rule sticks to its D.
            return []
        return [IDS[data_index]] if 0<=data_index<len(IDS) else []
    band_index=state['last_wide']
    if band_index==2:
        state['retry_hits']+=1
        return [IDS[0]]
    return []

known={value.replace('-',''):{'asset':value,'asset_key':value.replace('-','')} for value in IDS}

def _resolve_full_asset(values,known_items):
    if not values:
        return None,'NOT MATCHED'
    key=values[0].replace('-','')
    item=known_items.get(key)
    return (item,'Matched') if item else (None,'NOT MATCHED')

def _printed_asset_tokens(value,asset_format):
    value=str(value).strip().upper()
    return [value] if value in ('DN-2277','DN-895') else []

ns={
    'cv2':_CV2Stub,
    'pytesseract':_TesseractStub,
    '_year15_oriented':lambda page,kind,preferred_deg=None: img,
    'parse_date_text':lambda value: None,
    '_printed_asset_tokens':_printed_asset_tokens,
    '_resolve_full_asset':_resolve_full_asset,
    '_best_observed_asset_id':lambda values,known_items: values[0] if values else '',
    'canonical_asset_id':lambda value: str(value).strip().upper(),
    '_table_row_bands':lambda image,min_y,max_y:(bands,table),
    '_year15_manhole_column_boxes':lambda image,row_bands,row_table:{'asset':(0.0,.27),'date':(.74,1.0),'source':'test'},
    '_ocr_asset_candidates':_ocr_asset_candidates,
    '_confirmed_suffix_asset_candidates':lambda cell,known_items,asset_format=None: [],
    '_parse_sheet_date':lambda cell: None,
}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

emitted=[]
rows=ns['parse_year15_manholes'](
    object(),
    {'asset_format':{'mode':'prefixed_dash'},'manholes':known},
    on_row=emitted.append,
)

assert state['retry_hits']==1,state
assert len(rows)==21,rows
assert len(emitted)==21,emitted
assert [row['asset'] for row in rows]==IDS,[row['asset'] for row in rows]
assert all(row['status']=='Matched' for row in rows),rows

print('post-v102 Manhole partial-token/grid-row regression passed')
