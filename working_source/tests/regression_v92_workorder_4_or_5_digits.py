from pathlib import Path
import ast,re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
assert re.search(r"APP_VERSION = '(?:92|93)'",s)
assert "\\d{4,5}" in s

tree=ast.parse(s)
ns={'np':np,'cv2':cv2,'re':re}
# Stub OCR output is swapped below to prove both lengths enter the color path.
ns['cached_ocr_string']=lambda *_a,**_k:'11871'
for name in ('_workorder_magenta_variants','_workorder_magenta_candidates'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

def synthetic(number):
    img=np.full((90,280,3),245,dtype=np.uint8)
    cv2.rectangle(img,(4,4),(275,84),(70,145,105),2)
    cv2.putText(img,'WORK ORDER',(8,26),cv2.FONT_HERSHEY_SIMPLEX,.45,(25,25,25),1,cv2.LINE_AA)
    cv2.putText(img,number,(82,66),cv2.FONT_HERSHEY_SIMPLEX,1.25,(190,55,120),3,cv2.LINE_AA)
    return img

five=synthetic('11871')
ns['cached_ocr_string']=lambda *_a,**_k:'11871'
assert '11871' in ns['_workorder_magenta_candidates'](five)

four=synthetic('9876')
ns['cached_ocr_string']=lambda *_a,**_k:'9876'
assert '9876' in ns['_workorder_magenta_candidates'](four)

# 3- and 6-digit OCR strings must not be accepted as W/O candidates.
for bad in ('123','123456'):
    ns['cached_ocr_string']=lambda *_a,_bad=bad,**_k:_bad
    assert ns['_workorder_magenta_candidates'](four)==[]

# Primary color path and classifier fallback both permit 4 or 5 digits.
assert "re.findall(r'(?<!\\d)\\d{4,5}(?!\\d)',text)" in s
assert "wo_hits.extend(re.findall(r'\\d{4,5}',t))" in s
print('v92 4-or-5-digit pink Work Order OCR regression passed')
