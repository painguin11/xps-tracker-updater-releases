from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'working_source/app/reno_scan_updater.py'
TEST=ROOT/'working_source/tests/regression_post_v103_manhole_reordered_columns.py'
CONTEXT=ROOT/'PROJECT_CONTEXT.md'
CHECKLIST=ROOT/'RELEASE_CHECKLIST.md'
DOC_CONTEXT=ROOT/'working_source/docs/PROJECT_CONTEXT.md'
DOC_CHECKLIST=ROOT/'working_source/docs/RELEASE_CHECKLIST.md'

TEST_TEXT=r'''from pathlib import Path
import ast
from datetime import datetime
import re
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
parse_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')
retry_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_retry_year15_manhole_rows')
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
    @staticmethod
    def cvtColor(image,code):
        return image[:,:,0] if getattr(image,'ndim',0)==3 else image
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
assert len(rows)==37,rows
assert [row['asset'] for row in rows]==IDS,[row['asset'] for row in rows]
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
'''


def write_test():
    TEST.write_text(TEST_TEXT,encoding='utf-8')


def patch_source():
    text=SOURCE.read_text(encoding='utf-8')
    old='''            if not observations: continue\n            item,status=_resolve_full_asset(observations,known)\n            sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))\n            date_img=img[y1:y2,date_left:date_right]\n            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                 'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n'''
    new='''            if not observations: continue\n            # A real one-letter NEW MANHOLE may be read both with and without its\n            # final suffix across OCR variants. Exact-first matching would otherwise\n            # collapse that mixed evidence back to the existing base manhole. Require\n            # the suffix to survive independent physical-cell crops before it can\n            # override an observed base ID.\n            confirmed_suffixes=list(dict.fromkeys(_confirmed_suffix_asset_candidates(\n                id_img,known,asset_format=asset_format)))\n            if len(confirmed_suffixes)==1:\n                item=None; status='NEW MANHOLE'; sid=confirmed_suffixes[0]\n            else:\n                item,status=_resolve_full_asset(observations,known)\n                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))\n            date_img=img[y1:y2,date_left:date_right]\n            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                 'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n            if len(confirmed_suffixes)==1: rec['_mh_suffix_confirmed']=True\n'''
    if text.count(old)!=1:
        raise SystemExit(f'normal Manhole patch anchor count={text.count(old)}')
    text=text.replace(old,new,1)

    old_retry='''            if not observations: continue\n            item,status=_resolve_full_asset(observations,known)\n            if item is None and status!='NEW MANHOLE': continue\n            sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))\n            key=item['asset_key'] if item else asset_key(sid)\n'''
    new_retry='''            if not observations: continue\n            confirmed_suffixes=list(dict.fromkeys(_confirmed_suffix_asset_candidates(\n                base,known,asset_format=asset_format)))\n            if len(confirmed_suffixes)==1:\n                item=None; status='NEW MANHOLE'; sid=confirmed_suffixes[0]\n            else:\n                item,status=_resolve_full_asset(observations,known)\n                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))\n            if item is None and status!='NEW MANHOLE': continue\n            key=item['asset_key'] if item else asset_key(sid)\n'''
    if text.count(old_retry)!=1:
        raise SystemExit(f'retry Manhole patch anchor count={text.count(old_retry)}')
    text=text.replace(old_retry,new_retry,1)

    old_retry_rec='''            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                 'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n            rec['_field_previews']={\n                'asset':base.copy() if getattr(base,'size',0) else None,\n'''
    new_retry_rec='''            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                 'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n            if len(confirmed_suffixes)==1: rec['_mh_suffix_confirmed']=True\n            rec['_field_previews']={\n                'asset':base.copy() if getattr(base,'size',0) else None,\n'''
    # This shape appears once in retry and once potentially elsewhere; constrain by replacing last occurrence.
    pos=text.rfind(old_retry_rec)
    if pos<0:
        raise SystemExit('retry record patch anchor not found')
    text=text[:pos]+text[pos:].replace(old_retry_rec,new_retry_rec,1)

    old_select='''    out=grid_out if len(grid_out)>len(token_out) else token_out\n'''
    new_select='''    # Prefer the physical ruled-row result on a row-count tie when it carries an\n    # independently confirmed NEW MANHOLE suffix. This prevents a whole-page OCR\n    # read that dropped the final letter from overriding stronger cell evidence.\n    grid_has_confirmed_new=any(rec.get('_mh_suffix_confirmed') for rec in grid_out)\n    out=grid_out if (len(grid_out)>len(token_out) or\n                     (len(grid_out)==len(token_out) and grid_has_confirmed_new)) else token_out\n'''
    if text.count(old_select)!=1:
        raise SystemExit(f'selection patch anchor count={text.count(old_select)}')
    text=text.replace(old_select,new_select,1)
    SOURCE.write_text(text,encoding='utf-8')


def patch_docs():
    context=CONTEXT.read_text(encoding='utf-8')
    marker='## Released in v104 — reordered Manhole table columns\n'
    section='''## Pending after v104 — preserve independently confirmed new Manhole suffixes\n\n- A long Date-first B&C Manhole table exposed a second failure mode after the v104 column fix: the PDF can clearly print a one-letter suffixed Manhole that is absent from the master while another OCR variant reads the same cell as its existing unsuffixed base.\n- The B&C Manhole row parser and expected-count retry now independently reread the physical Manhole cell before resolving mixed base/suffix evidence. A suffix must survive the existing multi-crop confirmation helper before it can override an observed base ID and become `NEW MANHOLE`.\n- This keeps the conservative false-suffix safeguard while ensuring a genuinely confirmed new Manhole reaches the existing approval/add-to-master workflow instead of being silently collapsed to its base asset.\n- When token OCR and ruled-row OCR have the same row count, an independently confirmed new suffix makes the ruled-row result authoritative for that tie.\n- Permanent regression coverage remains in `working_source/tests/regression_post_v103_manhole_reordered_columns.py`, now modeling a master that contains the base Manhole but not the printed suffixed Manhole and exercising both normal and count-retry paths.\n- The supplied customer PDF and workbook remain private and are not committed or packaged.\n\n'''
    if section.strip() not in context:
        if marker not in context: raise SystemExit('PROJECT_CONTEXT release marker missing')
        context=context.replace(marker,section+marker,1)
    CONTEXT.write_text(context,encoding='utf-8')
    DOC_CONTEXT.write_text(context,encoding='utf-8')

    checklist=CHECKLIST.read_text(encoding='utf-8')
    needle='''- A mismatch automatically triggers a slower reread of every Manhole page in that\n  work order before the final mismatch is presented. The retry may use only\n  PDF-observed IDs that still pass the established matching/new-suffix safeguards;\n  it must never invent, delete, or arbitrarily select rows solely to hit the count.\n'''
    addition=needle+'''- If one B&C Manhole cell produces both the existing base ID and a one-letter\n  suffixed ID across OCR variants, the suffix may override the base only when it\n  survives the existing independent multi-crop suffix confirmation. A confirmed\n  suffix must remain `NEW MANHOLE` in both the normal parse and expected-count retry.\n'''
    if 'confirmed\n  suffix must remain `NEW MANHOLE`' not in checklist:
        if needle not in checklist: raise SystemExit('RELEASE_CHECKLIST Manhole anchor missing')
        checklist=checklist.replace(needle,addition,1)
    CHECKLIST.write_text(checklist,encoding='utf-8')
    DOC_CHECKLIST.write_text(checklist,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--test-only',action='store_true')
    args=parser.parse_args()
    write_test()
    if not args.test_only:
        patch_source(); patch_docs()
        print('Applied post-v104 NEW MANHOLE suffix preservation patch')
    else:
        print('Wrote failing post-v104 NEW MANHOLE regression only')

if __name__=='__main__':
    main()
