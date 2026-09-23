from pathlib import Path
import ast
import re
import numpy as np
from PIL import Image

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

classify_node=next(
    (n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='classify_for_profile'),
    None,
)
assert classify_node is not None

# A real rotated B&C Pipe scan can OCR the printed header approximately as:
#   "Secon No ... Upstrean WH ... Downstream MH ... Street ... Date ... Tength Surveyed"
# The page is still structurally a Pipe table. Preserve the 90-degree orientation
# rather than dropping it as "other" solely because the first letter of Length and
# part of Upstream MH were damaged by OCR.
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
    if psm==11 and marker==20:
        return (
            'Secon No Drainage rea Upstrean WH Downstream MH '
            'Street Date Tength Surveyed'
        )
    return 'scan text without a readable activity header'

ns={
    'render_page':synthetic_render,
    'ocr_text':synthetic_ocr,
    '_ocr_digits':lambda *args,**kwargs:[],
    're':re,
    'np':np,
    'Image':Image,
}
exec(compile(ast.Module(body=[classify_node],type_ignores=[]),str(SOURCE),'exec'),ns)

_oriented,deg,_text,kind=ns['classify_for_profile'](object(),'phase2_year1')
assert kind=='pipes',f'expected damaged rotated survey header to classify as pipes; got {kind!r} at {deg}°'
assert deg==90,f'expected damaged rotated survey header to preserve 90° orientation; got {deg}°'

print('post-v106 damaged rotated Pipe survey-header OCR regression passed')
