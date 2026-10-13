"""Regression: selective border-isolated OCR must read printed length, not infer digits."""
import ast
import re
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from PIL import Image,ImageDraw,ImageFont

src=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
tree=ast.parse(src.read_text(encoding='utf-8'))
ns={'cv2':cv2,'np':np,'re':re,'MAX_ROW_LENGTH':1700,'MAX_ROW_LENGTH_DECIMALS':2,
    'cached_ocr_string':lambda im,config='':pytesseract.image_to_string(im,config=config)}
for name in ('_row_length_token_value','_valid_row_length_value','_border_isolated_length_evidence'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(src),'exec'),ns)

def printed_length(text):
    width,height=148,33
    im=Image.new('RGB',(width,height),'white')
    draw=ImageDraw.Draw(im)
    font=ImageFont.truetype('DejaVuSans.ttf',20)
    bb=draw.textbbox((0,0),text,font=font)
    draw.text((width-9-(bb[2]-bb[0]),8-bb[1]),text,font=font,fill=(20,20,20))
    draw.line([(0,1),(width-1,1)],fill=(40,40,40),width=2)
    draw.line([(0,height-1),(width-1,height-1)],fill=(40,40,40),width=2)
    draw.line([(width-4,0),(width-4,height-1)],fill=(40,40,40),width=2)
    return np.asarray(im)

for printed in ('34','54','51.25'):
    result=ns['_border_isolated_length_evidence'](printed_length(printed))
    assert result['value']==float(printed),(printed,result)
    # Do not rely on repeating one Tesseract configuration or source.
    assert len(result['sources'])>=2,(printed,result)
blank=printed_length('')
assert ns['_border_isolated_length_evidence'](blank)['value'] is None

# Contradictory OCR treatments must not permit automatic update.
calls={'n':0}
def conflicting_ocr(im,config=''):
    label=('34' if calls['n']<2 else ('54' if calls['n']<4 else '5'))
    calls['n']+=1
    return label
ns['cached_ocr_string']=conflicting_ocr
conflict=ns['_border_isolated_length_evidence'](printed_length('34'))
assert conflict['value'] is None,conflict
print('Border-isolated length OCR: real rendered glyphs and disagreement fail-closed passed')
