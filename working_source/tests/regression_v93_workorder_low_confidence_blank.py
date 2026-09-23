from pathlib import Path
import ast,re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
version_match=re.search(r"APP_VERSION = '(\d+)'",s)
assert version_match and int(version_match.group(1))>=93
assert 'def _workorder_confident_magenta_candidate' in s
assert 'def _workorder_magenta_structure_count' in s

tree=ast.parse(s)
ns={'np':np,'cv2':cv2,'re':re,'cached_ocr_string':lambda *_a,**_k:'11871'}
for name in ('_workorder_magenta_variants','_workorder_magenta_structure_count','_workorder_confident_magenta_candidate'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

def clean(number):
    img=np.full((90,280,3),245,dtype=np.uint8)
    cv2.rectangle(img,(4,4),(275,84),(70,145,105),2)
    cv2.putText(img,'WORK ORDER',(8,26),cv2.FONT_HERSHEY_SIMPLEX,.45,(25,25,25),1,cv2.LINE_AA)
    cv2.putText(img,number,(82,66),cv2.FONT_HERSHEY_SIMPLEX,1.25,(190,55,120),3,cv2.LINE_AA)
    return img

# Clean 5-digit and 4-digit pink values should still prefill.
ns['cached_ocr_string']=lambda *_a,**_k:'11871'
value,seen=ns['_workorder_confident_magenta_candidate'](clean('11871'))
assert seen and value=='11871', (seen,value)
ns['cached_ocr_string']=lambda *_a,**_k:'9876'
value,seen=ns['_workorder_confident_magenta_candidate'](clean('9876'))
assert seen and value=='9876', (seen,value)

# Simulate the user's barely-legible case: only the first and last digit retain
# strong magenta structure, while OCR nevertheless hallucinates a complete 4-digit value.
# The structural confidence gate must reject that prefill but still report that pink ink exists.
weak=np.full((90,280,3),245,dtype=np.uint8)
cv2.rectangle(weak,(4,4),(275,84),(70,145,105),2)
x=82
for ch,color in [('1',(190,55,120)),('1',(250,232,242)),('7',(250,232,242)),('3',(190,55,120))]:
    cv2.putText(weak,ch,(x,66),cv2.FONT_HERSHEY_SIMPLEX,1.25,color,3,cv2.LINE_AA)
    x+=28
ns['cached_ocr_string']=lambda *_a,**_k:'1173'
value,seen=ns['_workorder_confident_magenta_candidate'](weak)
assert seen and value=='', (seen,value)

# No pink/magenta signal is distinct from low-confidence pink. Only the former may
# use the conservative grayscale fallback for a desaturated scan.
plain=np.full((90,280,3),245,dtype=np.uint8)
cv2.putText(plain,'9876',(82,66),cv2.FONT_HERSHEY_SIMPLEX,1.25,(35,35,35),3,cv2.LINE_AA)
value,seen=ns['_workorder_confident_magenta_candidate'](plain)
assert not seen and value=='', (seen,value)

start=s.index('def ocr_workorder_guesses')
end=s.index('\ndef _row_length_token_value',start)
block=s[start:end]
assert 'magenta_seen' in block
assert "elif magenta_seen:\n        wo=''" in block
assert '# A fully desaturated/black-and-white scan can destroy the color signal.' in block
assert 'broad=_best_ocr_text' not in block, 'single broad OCR read must not prefill a low-confidence W/O'
print('v93 low-confidence Work Order blank-prefill regression passed')
