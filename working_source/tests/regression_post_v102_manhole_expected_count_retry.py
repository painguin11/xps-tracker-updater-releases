from pathlib import Path
import ast
import cv2
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

assert "def parse_manhole_list(page, master_index, quick_text, on_row=None, on_progress=None):" in text
assert "def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):" in text
for required in (
    'def _retry_manhole_list_rows(',
    'def _retry_year15_manhole_rows(',
    '_year15_all_row_bands(img,.02,.90)',
    'for psm in (8,13):',
    "Manhole count {actual}/{expected} for W/O {wo_key} — retrying OCR",
    "manhole_retry_pages.setdefault(wo_key,[]).append",
    'candidate_total=actual+len(recovered)',
    'candidate_total<=expected',
    'automatic add skipped for review',
):
    assert required in text,required

helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_retry_year15_manhole_rows')
img=np.full((400,700,3),255,dtype=np.uint8)
bands=[(80,110),(120,150),(160,190)]
table=(50,600)
for color,(y1,y2) in zip((190,160,130),bands): img[y1:y2,:,:]=color
known={
    'DN1001':{'asset':'DN-1001','asset_key':'DN1001'},
    'DN1002':{'asset':'DN-1002','asset_key':'DN1002'},
}

def ocr_assets(cell,fast_plain=False,asset_format=None):
    mean=float(np.mean(cell)) if getattr(cell,'size',0) else 255
    if 180<mean<205: return ['DN-1001']
    if 145<mean<175: return ['DN-1002']
    if 115<mean<145: return ['DN-9999']
    return []

def resolve(values,known_items):
    for value in values:
        key=''.join(ch for ch in str(value).upper() if ch.isalnum())
        if key in known_items: return known_items[key],'Matched'
    return None,'NOT MATCHED'

ns={
    'cv2':cv2,'np':np,
    '_year15_oriented':lambda page,kind,preferred_deg=None: img,
    '_table_row_bands':lambda image,a,b:(bands,table),
    '_year15_all_row_bands':lambda image,a,b:(bands,table),
    '_ocr_asset_candidates':ocr_assets,
    'cached_ocr_string':lambda image,config='':'',
    '_printed_asset_tokens':lambda value,asset_format:[],
    '_resolve_full_asset':resolve,
    '_best_observed_asset_id':lambda values,known_items: values[0] if values else '',
    'canonical_asset_id':lambda value:str(value).strip().upper(),
    'asset_key':lambda value:''.join(ch for ch in str(value).upper() if ch.isalnum()),
    '_parse_sheet_date':lambda cell:None,
}
exec(compile(ast.Module(body=[helper],type_ignores=[]),str(SOURCE),'exec'),ns)
rows=ns['_retry_year15_manhole_rows'](
    object(),{'asset_format':{'mode':'prefixed_dash'},'manholes':known})
assert [row['asset'] for row in rows]==['DN-1001','DN-1002'],rows
assert all(row['status']=='Matched' for row in rows),rows

print('post-v102 Manhole expected-count OCR retry regression passed')
