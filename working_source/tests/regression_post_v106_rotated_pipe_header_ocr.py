from pathlib import Path
import ast
import re
import numpy as np
import cv2
from PIL import Image

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

def node(name):
    return next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name),None)

helper_node=node('_line_suppressed_table_header_image')
classify_node=node('classify_for_profile')
assert helper_node is not None
assert classify_node is not None

# The OCR-only helper should erase long ruled-table geometry without erasing
# short glyph-like marks. The original rendered image remains untouched for
# table geometry.
helper_ns={'cv2':cv2,'np':np}
exec(compile(ast.Module(body=[helper_node],type_ignores=[]),str(SOURCE),'exec'),helper_ns)
canvas=np.full((220,700,3),255,dtype=np.uint8)
cv2.line(canvas,(0,40),(699,40),(0,0,0),2)
cv2.line(canvas,(350,0),(350,219),(0,0,0),2)
cv2.rectangle(canvas,(80,90),(92,108),(0,0,0),-1)
clean=helper_ns['_line_suppressed_table_header_image'](canvas,1.0)
assert clean[40,120].min()>240,'expected long horizontal rule to be suppressed'
assert clean[120,350].min()>240,'expected long vertical rule to be suppressed'
assert clean[98,86].min()<40,'expected short glyph-like mark to survive line suppression'

# Model the real failure mode: the fast pass and the normal high-resolution
# ruled-header pass both remain unreadable, but the line-suppressed high-res
# header reveals a complete Pipe header at the 90-degree orientation.
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
    if psm==6 and marker==99:
        return (
            'Section No Drainage Area Upstream MH Downstream MH '
            'Street Date Length Surveyed'
        )
    return 'scan text without a readable activity header'

def synthetic_line_suppressed(image,height_ratio=.35):
    marker=int(image[0,0,0]) if getattr(image,'size',0) else 0
    out=np.full((20,20,3),255,dtype=np.uint8)
    if marker==20:  # PIL rotate(90) moves the original top-right marker here.
        out[0,0]=99
    else:
        out[0,0]=marker
    return out

ns={
    'render_page':synthetic_render,
    'ocr_text':synthetic_ocr,
    '_ocr_digits':lambda *args,**kwargs:[],
    '_line_suppressed_table_header_image':synthetic_line_suppressed,
    're':re,
    'np':np,
    'Image':Image,
}
exec(compile(ast.Module(body=[classify_node],type_ignores=[]),str(SOURCE),'exec'),ns)

_oriented,deg,_text,kind=ns['classify_for_profile'](object(),'phase2_year1')
assert kind=='pipes',f'expected line-suppressed header fallback to classify as pipes; got {kind!r} at {deg}°'
assert deg==90,f'expected line-suppressed header fallback to preserve 90° orientation; got {deg}°'

print('post-v106 line-suppressed rotated Pipe header OCR regression passed')
