from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'/'reno_scan_updater.py'
UPDATER=ROOT/'app'/'xps_update.py'
README=ROOT/'app'/'README_XPS_Tracker_Updater.txt'
V91_TEST=ROOT/'tests'/'regression_v91_workorder_color_ocr.py'
V92_TEST=ROOT/'tests'/'regression_v92_workorder_4_or_5_digits.py'

src=APP.read_text(encoding='utf-8')
repls={
    '"""OCR only five-digit values actually visible in the pink/magenta W/O ink."""':'"""OCR only 4- or 5-digit values actually visible in the pink/magenta W/O ink."""',
    "found.extend(re.findall(r'(?<!\\d)\\d{5}(?!\\d)',text))":"found.extend(re.findall(r'(?<!\\d)\\d{4,5}(?!\\d)',text))",
    "words 'Work Order Number': a 5-digit value in the known upper-left W/O box is":"words 'Work Order Number': a 4- or 5-digit value in the known upper-left W/O box is",
    "wo_hits.extend(re.findall(r'\\d{5}',t))":"wo_hits.extend(re.findall(r'\\d{4,5}',t))",
    '# except the five printed W/O digits. Fixed-position variants still handle scan shift.':'# except the four or five printed W/O digits. Fixed-position variants still handle scan shift.',
}
for old,new in repls.items():
    assert old in src, f'marker not found: {old}'
    src=src.replace(old,new,1)
src,n=re.subn(r"^APP_VERSION\s*=\s*['\"]91['\"]", "APP_VERSION = '92'", src, count=1, flags=re.M)
assert n==1, 'APP_VERSION 91 marker not found exactly once'
APP.write_text(src,encoding='utf-8')

up=UPDATER.read_text(encoding='utf-8')
up,n=re.subn(r'^CURRENT_VERSION\s*=\s*[\"\']91[\"\']','CURRENT_VERSION = "92"',up,count=1,flags=re.M)
assert n==1, 'CURRENT_VERSION 91 marker not found exactly once'
UPDATER.write_text(up,encoding='utf-8')

readme=README.read_text(encoding='utf-8')
if 'Version 92 four- or five-digit Work Order correction' not in readme:
    readme += '''\n\nVersion 92 four- or five-digit Work Order correction\n------------------------------------------------------\n- Extends the v91 pink/magenta Work Order color-isolation path to accept both 4-digit and 5-digit machine-typed Work Order numbers.\n- Keeps the same color-first OCR design, editable confirmation popup, and grayscale fallback for faded/desaturated scans.\n- Preserves all v91 new-asset preview, conservative endpoint recovery, continuation, total-validation, and matching safeguards.\n'''
README.write_text(readme,encoding='utf-8')

if V91_TEST.exists():
    test=V91_TEST.read_text(encoding='utf-8')
    test=test.replace("assert \"APP_VERSION = '91'\" in s","assert re.search(r\"APP_VERSION = '(?:91|92)'\",s)")
    test=test.replace("assert '11871' in ns['_workorder_magenta_candidates'](img)","assert '11871' in ns['_workorder_magenta_candidates'](img)")
    V91_TEST.write_text(test,encoding='utf-8')

V92_TEST.write_text(r'''from pathlib import Path
import ast,re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
assert "APP_VERSION = '92'" in s
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
''',encoding='utf-8')
print('Applied v92 4-or-5-digit Work Order correction and version bump.')
