from pathlib import Path
import ast
import re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

def node(name):
    found=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name),None)
    assert found is not None, f'missing {name}'
    return found

# The new contextual read is deliberately limited to compact B&C Pipe tables.
assert "kind=='pipes' and 'compact table grid' in str(prepared.get('source','')).lower()" in text
assert 'contextual_values=contextual_pipe_values' in text
assert '_corroborated_existing_asset(source_observations,known)' in text

# Model a compact Pipe value column after grid suppression. PSM 6 and 11 agree on
# 134,12 (decimal point OCRed as comma) and on the footer total, but disagree on
# another row. Only the two-pass agreements may survive.
class _Output:
    DICT='DICT'

class _Tesseract:
    Output=_Output
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        psm=11 if '--psm 11' in config else 6
        values=(['134,12','366.04','4426.25','999']
                if psm==6 else ['134,12','366.05','4426.25','999'])
        return {
            'text':values,
            'left':[760,760,760,50],
            'width':[80,80,100,40],
            'top':[112,172,232,112],
            'height':[20,20,20,20],
        }

class _Pytesseract:
    Output=_Output
    image_to_data=_Tesseract.image_to_data

pipe_ns={
    'np':np,'cv2':cv2,'pytesseract':_Pytesseract,'re':re,
    '_line_suppressed_table_header_image':lambda img,height_ratio=.35: img,
}
exec(compile(ast.Module(body=[node('_contextual_pipe_length_candidates')],type_ignores=[]),
             str(SOURCE),'exec'),pipe_ns)
img=np.full((500,1200,3),255,dtype=np.uint8)
bands=[(100,150),(160,210),(220,270)]
values=pipe_ns['_contextual_pipe_length_candidates'](
    img,bands,(100,1100),(.60,.80))
assert values.get(0)==[134.12],values
assert 1 not in values,values
assert values.get(2)==[4426.25],values

# Page-4 failure class: a grid stroke can make the printed Date header OCR as
# "IpDate". It must still establish the real header band rather than falling back
# to the coarse legacy Manhole crop.
header_calls={'count':0}
def header_data(image,config='',output_type=None):
    header_calls['count']+=1
    if header_calls['count']==1:
        return {'text':['MANHOLE','SURVEY','LIST'],'left':[10,100,200],
                'top':[2,2,2],'width':[40,40,40],'height':[10,10,10]}
    return {
        'text':['Manhole','Number','Street','Drainage','Area','IpDate'],
        'left':[5,70,260,520,610,760],
        'top':[2]*6,'width':[50]*6,'height':[10]*6,
    }

class _HeaderTesseract:
    Output=_Output
    image_to_data=staticmethod(header_data)

header_ns={'np':np,'cv2':cv2,'pytesseract':_HeaderTesseract,'re':re}
exec(compile(ast.Module(body=[node('_year15_manhole_column_boxes')],type_ignores=[]),
             str(SOURCE),'exec'),header_ns)
header_img=np.full((400,1000,3),255,dtype=np.uint8)
layout=header_ns['_year15_manhole_column_boxes'](
    header_img,[(20,50),(60,95),(100,125)],(100,900))
assert layout['source']=='header',layout
assert layout['header_band_index']==1,layout
assert layout['asset'][1]<.40,layout
assert layout['date'][0]>.60,layout

# A single damaged tight crop must not overrule two independent PDF OCR sources
# that agree on a different existing Manhole.
asset_ns={'re':re}
for name in ('canonical_asset_id','asset_key','_asset_id_parts',
             '_authoritative_asset_candidates','_corroborated_existing_asset'):
    exec(compile(ast.Module(body=[node(name)],type_ignores=[]),str(SOURCE),'exec'),asset_ns)
known={
    'R268':{'asset':'R2-68','asset_key':'R268'},
    'R269':{'asset':'R2-69','asset_key':'R269'},
}
winner=asset_ns['_corroborated_existing_asset'](
    [['R2-69'],['R2-68'],['R2-68']],known)
assert winner and winner['asset']=='R2-68',winner
assert asset_ns['_corroborated_existing_asset'](
    [['R2-69'],['R2-68']],known) is None

print('post-v107 compact Pipe contextual OCR + Manhole corroboration regression passed')
