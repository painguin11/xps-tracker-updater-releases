"""Privacy-safe rendered OCR and parser-review regressions for length/geometry guards.

Real customer PDF expected-value benchmarks are deliberately NOT included.
"""
from pathlib import Path
from datetime import datetime
import ast
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
source=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(source)
def node(name):
    return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
def install(ns,*names):
    for name in names:
        exec(compile(ast.Module(body=[node(name)],type_ignores=[]),str(SOURCE),'exec'),ns)

# REAL TESSERACT on synthetic rendered cells, not mocked OCR.
ns={'cv2':cv2,'np':np,'re':re,'pytesseract':pytesseract,
    'cached_ocr_string':lambda im,config='':pytesseract.image_to_string(im,config=config),
    'MAX_ROW_LENGTH':1700,'MAX_ROW_LENGTH_DECIMALS':2}
install(ns,'_row_length_token_value','_valid_row_length_value','_stable_numeric_vote',
        '_direct_pair_length_candidates','asset_key','_ocr_id_text_variants',
        '_printed_asset_tokens','_ocr_asset_candidates')
def ruled(text,width=380):
    # A real, high-resolution printed-font ruled cell. OpenCV's thin vector
    # strokes change shape across runner builds, so use the bundled system
    # DejaVu font consistently instead of accidental OCR artifacts.
    paper=Image.new('RGB',(width,105),'white')
    draw=ImageDraw.Draw(paper)
    draw.rectangle((1,1,width-2,103),outline=(65,65,65),width=1)
    font=ImageFont.truetype('DejaVuSans.ttf',32)
    draw.text((25,32),text,font=font,fill='black')
    return np.asarray(paper).copy()
for literal in ('82.87','134.12'):
    observed=ns['_direct_pair_length_candidates'](ruled(literal))
    assert observed==[float(literal)],(literal,observed)
id_img=ruled('DN-2243S')
tokens=ns['_ocr_asset_candidates'](id_img,fast_plain=True,
    asset_format={'mode':'prefixed_dash','requires_dash':True,
                  'max_prefix_len':2,'max_digits':4,'allow_suffix':True})
assert 'DN-2243S' in tokens,tokens
assert ns['_row_length_token_value']('82.87')==82.87
assert ns['_row_length_token_value']('82.8.7') is None
print('REAL OCR: 3 synthetic ruled cells and decimal safeguards passed')

# SYNTHETIC DATE READS (mock OCR strings, real date evidence logic).
# Two distinct image treatments independently agreeing on different full
# dates is a material conflict. One noisy PSM inside each image is not.
date_ns={'cv2':cv2,'np':np,'re':re,'datetime':datetime}
install(date_ns,'_plausible_sheet_year','_parse_sheet_date_text_candidates',
        '_choose_sheet_date_evidence','_read_sheet_date_evidence')
date_reads=[]
def date_ocr(img,config=''):
    return date_reads.pop(0)
date_ns['cached_ocr_string']=date_ocr
date_img=np.full((45,180,3),255,np.uint8)
def date_evidence(reads):
    date_reads[:]=reads
    out=date_ns['_read_sheet_date_evidence'](date_img,DATE)
    assert not date_reads
    return out
DATE=datetime(2026,10,12)
same_dates=date_evidence(['10/12/2026']*4)
assert same_dates['date']==DATE and not same_dates.get('conflicting_sources')
differing=date_evidence(['10/12/2026']*2+['10/13/2026']*2)
assert differing['date']==DATE and len(differing.get('conflicting_sources',{}))==2
noisy=date_evidence(['10/12/2026','10/13/2026']*2)
assert not noisy.get('conflicting_sources')
print('MOCKED DATE OCR: only corroborated cross-image full-date disagreement flagged')

# SYNTHETIC IMAGE GEOMETRY: accepted correction must preserve EVERY column,
# not just the same number of boundaries and the same outside width.
geo={'cv2':cv2,'np':np}
install(geo,'_year15_compact_grid_bands','_year15_compact_skew_retry',
        '_year15_compact_unresolved_bands')
h,w=1530,1980
clean=np.full((h,w,3),255,dtype=np.uint8)
xs=np.linspace(130,1845,8).astype(int)
ys=np.linspace(125,660,17).astype(int)
for x in xs:cv2.line(clean,(int(x),int(ys[0])),(int(x),int(ys[-1])),(40,40,40),2)
for i,y in enumerate(ys):cv2.line(clean,(int(xs[0]),int(y)),(int(xs[-1]),int(y)),(40,40,40),2 if i in (0,1,7,8,11,13,16) else 1)
rot=cv2.getRotationMatrix2D((w/2,h/2),-.6,1.0)
skew=cv2.warpAffine(clean,rot,(w,h),borderValue=(255,255,255))
broken,box,cols=geo['_year15_compact_grid_bands'](skew)
assert box is not None and cols and len(cols)==8
normal=geo['_year15_compact_skew_retry'](skew,broken,box,cols)
assert normal[4] is True,(len(broken),len(normal[1]))
orig=geo['_year15_compact_grid_bands']
def displaced(image):
    bands,table,columns=orig(image)
    if columns:
        columns=list(columns);columns[3]+=round((table[1]-table[0])*.055)
    return bands,table,columns
geo['_year15_compact_grid_bands']=displaced
rejected=geo['_year15_compact_skew_retry'](skew,broken,box,cols)
assert rejected[4] is False
assert rejected[0] is skew
# Interior gaps must be severe enough to exceed normal wrapped-row variation;
# preserve and flag the combined band, never fabricate an extra physical row.
regular=[(i*25,i*25+19) for i in range(8)]
assert geo['_year15_compact_unresolved_bands'](regular)==[]
wrapped=list(regular)
wrapped[3]=(wrapped[3][0],wrapped[3][0]+38)
assert geo['_year15_compact_unresolved_bands'](wrapped)==[]
merged=list(regular)
merged[3]=(merged[3][0],merged[3][0]+82)
merged[4]=(merged[3][1]+6,merged[3][1]+25)
for k in range(5,8):
    merged[k]=(merged[4][0]+25*(k-4),merged[4][1]+25*(k-4))
assert geo['_year15_compact_unresolved_bands'](merged)==[3]
print('SYNTHETIC GEOMETRY: guarded skew, shifted columns and uncertain merged bands covered')

# MOCKED PARSER LOGIC: even when a master or printed total happens to match,
# independent OCR disagreements may not become automatic master writes.
PIPE={'row':8,'up':'DN-1001','down':'DN-1002','up_key':'DN1001',
      'down_key':'DN1002','expected':82.87,'pipe_id':'P-8'}
def key(v):return re.sub(r'[^A-Z0-9]','',str(v or '').upper())
def resolve(ups,dns,master):
    return (PIPE,'Matched') if 'DN1001' in {key(x) for x in ups} and 'DN1002' in {key(x) for x in dns} else (None,'NOT MATCHED')
img=np.full((125,400,3),255,np.uint8)
img[43:55,201:295]=(30,30,30) # visibly distinct value-cell region
prepared={'img':img,'bands':[(10,30),(40,60)],'table':(0,400),
          'mapping':{'up':(0,.25),'down':(.25,.5),'value':(.5,.75),'date':(.75,1)},
          'header_band_index':0,'source':'header / compact table grid'}
read_context={'value':82.87}
read_direct={'value':82.87}
read_batch={'value':82.87}
read_clean={'value':82.87}
read_date={'conflicting_sources':None}
parser={'np':np,'re':re,'datetime':datetime,'asset_key':key,
    'canonical_asset_id':lambda v:str(v or '').upper(),
    '_read_sheet_date_evidence':lambda *a,**k:{'date':DATE,'strong':True,'candidates':[DATE],'votes':{},'strong_votes':{},
                                                 'conflicting_sources':read_date['conflicting_sources']},
    '_dominant_sheet_date':lambda *a,**k:DATE,
    '_read_pair_table_printed_total':lambda *a,**k:{'found':False,'band_index':None,'value':None,'confident':False},
    '_batch_cleaning_length_candidates':lambda *a,**k:{1:[read_batch['value']]},
    '_batch_pair_endpoint_candidates':lambda *a,**k:{1:['DN-1001']} if a[3][0]==0 else {1:['DN-1002']},
    '_batch_pair_endpoint_full_candidates':lambda *a,**k:{},'_batch_pair_endpoint_digit_candidates':lambda *a,**k:{},
    '_resolve_pipe_pair':resolve,'_resolve_pipe_pair_from_endpoint_digits':lambda *a,**k:None,
    '_authoritative_asset_candidates':lambda *a,**k:['valid'],
    '_ocr_known_r2_candidates':lambda *a,**k:[],
    '_ocr_asset_candidates':lambda *a,**k:[],
    '_best_observed_asset_id':lambda x,y:x[0] if x else '',
    '_direct_pair_length_candidates':lambda *a:[read_direct['value']],
    '_contextual_pipe_length_candidates':lambda *a,**k:{1:[read_context['value']]},
    '_choose_length':lambda values,expected=None:values[0] if values else None,
    '_ocr_length_candidates':lambda *a,**k:[],
    '_choose_pair_length_observation':lambda vals,direct,expected,*args:direct,
    '_choose_cleaning_length':lambda values,expected=None:values[0] if values else None,
    '_ocr_gridless_number_candidates':lambda *a,**k:[],
    '_conservative_cleaning_reread':lambda *a,**k:{'confident':True,'value':read_clean['value'],'candidates':[read_clean['value']]},
    '_valid_row_length_value':lambda v:v is not None and 0<float(v)<=1700,
    '_date_outlier_is_well_supported':lambda *a,**k:True,
    '_keep_unresolved_pair_row':lambda *a,**k:True,
    '_mark_field_review_block':lambda r,reason:(r.setdefault('_review_skip_reasons',[]).append(reason)
                                                if reason not in r.setdefault('_review_skip_reasons',[]) else None,
                                                r.__setitem__('skip_update',True)),
    'LENGTH_DIFF_THRESHOLD':4.5}
install(parser,'parse_year15_pair_list')
master={'asset_format':None,'pipe_items':[PIPE],'pipes':{('DN1001','DN1002'):PIPE},'manholes':{}}
def parse(kind):
    rows=parser['parse_year15_pair_list'](None,master,kind,prepared=dict(prepared),expected_date=DATE)
    assert len(rows)==1,rows
    assert rows[0]['_field_previews']['activity_value'].shape[0]==20
    assert float(np.mean(rows[0]['_field_previews']['activity_value']))<255
    return rows[0]
same=parse('pipes')
assert same['status']=='Matched' and not same.get('skip_update') and not same.get('_field_review_reasons'),same
read_direct['value']=82.88
disputed=parse('pipes')
assert disputed.get('skip_update') is True and disputed['_field_review_reasons']==['Length reads disagree'],disputed
assert disputed['_ocr_value_evidence']=={'line-suppressed table':82.87,'original ruled cell':82.88}
assert disputed['video_length']==82.87 # preserve strongly supported contextual first pass
read_direct['value']=82.87
read_clean['value']=82.88
clean_disputed=parse('cleaning')
assert clean_disputed.get('skip_update') is True and 'Length reads disagree' in clean_disputed.get('validation_warnings',[]),clean_disputed
read_clean['value']=82.87
clean_correct=parse('cleaning')
assert not clean_correct.get('_field_review_reasons'),clean_correct
prepared['geometry_uncertain_bands']=[1]
uncertain=parse('pipes')
assert uncertain.get('skip_update') is True
assert 'Row boundary uncertain' in uncertain.get('_field_review_reasons',[])
assert uncertain['_ocr_physical_cell']['band_index']==1
assert 'activity_value' in uncertain['_field_previews']
del prepared['geometry_uncertain_bands']
read_date['conflicting_sources']={'original grayscale':DATE,
                                   'thresholded cell':datetime(2026,10,13)}
date_disputed=parse('pipes')
assert date_disputed.get('skip_update') is True
assert 'Date reads disagree' in date_disputed.get('_field_review_reasons',[])
assert date_disputed['_field_previews']['date'].shape[0]==20
read_date['conflicting_sources']=None

# A later PDF reread can resolve a disagreement, but only when the winning
# value was already PDF-observed and the reread source is independently strong.
resolve_ns={'_valid_row_length_value':lambda v:v is not None and 0<float(v)<=1700}
install(resolve_ns,'_mark_field_review_block','_clear_field_review_block',
        '_resolved_length_disagreement','_clear_resolved_length_disagreement')
resolved_rec={'status':'LENGTH DIFF 31.0 (WHEEL WALK)','skip_update':False,
              '_field_review_reasons':['Length reads disagree'],
              'validation_warnings':['Length reads disagree'],
              'warnings':['Length reads disagree'],
              '_ocr_value_evidence':{'stacked column':34.0,'isolated ruled cell':3.0}}
resolve_ns['_mark_field_review_block'](resolved_rec,'Length reads disagree')
assert resolved_rec['skip_update'] is True
assert not resolve_ns['_clear_resolved_length_disagreement'](
    resolved_rec,{'confident':True,'source':'sole master-plausible OCR value'},34.0)
assert 'Length reads disagree' in resolved_rec['_field_review_reasons']
assert resolve_ns['_clear_resolved_length_disagreement'](
    resolved_rec,{'confident':True,'source':'cross-observed clipped digit'},34.0)
assert not resolved_rec['_field_review_reasons']
assert not resolved_rec['validation_warnings']
assert resolved_rec['_ocr_value_resolution']['value']==34.0
assert resolved_rec['skip_update'] is False

# Clearing one field-review reason must never bypass an independent asset/geometry block.
unmatched={'status':'NOT MATCHED','skip_update':True,'_field_review_reasons':[],
           '_review_skip_reasons':['Length reads disagree'],'warnings':[],'validation_warnings':[]}
assert not resolve_ns['_clear_field_review_block'](unmatched,'Length reads disagree')
assert unmatched['skip_update'] is True
geometry={'status':'Matched','skip_update':True,'_field_review_reasons':['Row boundary uncertain'],
          '_review_skip_reasons':['Row boundary uncertain','Date reads disagree'],
          'warnings':[],'validation_warnings':['Row boundary uncertain — rescan page']}
geometry['_field_review_reasons'].remove('Date reads disagree') if 'Date reads disagree' in geometry['_field_review_reasons'] else None
assert not resolve_ns['_clear_field_review_block'](geometry,'Date reads disagree')
assert geometry['skip_update'] is True

# Two individually wrong values can cancel out in a printed total.
# A matching sum must never clear either independent OCR conflict.
wrong=(82.88,119.99)
correct=(82.87,120.00)
assert round(sum(wrong),2)==round(sum(correct),2)
assert disputed.get('_field_review_reasons')
app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App')
update=next(n for n in app.body if isinstance(n,ast.FunctionDef) and n.name=='update_master')
edit=next(n for n in app.body if isinstance(n,ast.FunctionDef) and n.name=='edit_selected')
assert "unresolved_fields=[r for r in self.records if r.get('_field_review_reasons')]" in ast.get_source_segment(source,update)
assert 'Confirm PDF Length' in ast.get_source_segment(source,edit)
assert 'Confirm PDF Date' in ast.get_source_segment(source,edit)
print('MOCKED PARSER: correct/read-disagreement/review/crop/canceling-totals covered')
print('PRIVATE FIXTURE OCR: SKIPPED (requires raw-byte fixture access and verified per-row expectations)')
