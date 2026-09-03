from pathlib import Path
import ast,re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
assert re.search(r"APP_VERSION = '(?:91|92|93|94)'",s)
assert 'machine-typed pink/magenta' in s
assert '_workorder_confident_magenta_candidate(candidate_crop)' in s

# Execute the color isolation helpers without importing the Windows-only app.
tree=ast.parse(s)
ns={'np':np,'cv2':cv2,'re':re,'cached_ocr_string':lambda *_a,**_k:'11871'}
for name in ('_workorder_magenta_variants','_workorder_magenta_candidates'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

# Synthetic form crop: green rule + black label + machine-typed pink W/O.
img=np.full((90,280,3),245,dtype=np.uint8)
cv2.rectangle(img,(4,4),(275,84),(70,145,105),2)
cv2.putText(img,'WORK ORDER',(8,26),cv2.FONT_HERSHEY_SIMPLEX,.45,(25,25,25),1,cv2.LINE_AA)
cv2.putText(img,'11871',(82,66),cv2.FONT_HERSHEY_SIMPLEX,1.25,(190,55,120),3,cv2.LINE_AA)
variants=ns['_workorder_magenta_variants'](img)
assert variants and all(v.ndim==2 for v in variants)
assert all(np.any(v<128) for v in variants)
assert '11871' in ns['_workorder_magenta_candidates'](img)

# Green/black form content by itself must not become a magenta W/O image.
plain=np.full((90,280,3),245,dtype=np.uint8)
cv2.rectangle(plain,(4,4),(275,84),(70,145,105),2)
cv2.putText(plain,'WORK ORDER 11871',(8,52),cv2.FONT_HERSHEY_SIMPLEX,.65,(25,25,25),2,cv2.LINE_AA)
assert ns['_workorder_magenta_variants'](plain)==[]

# The actual W/O selection path must try the confidence-gated color OCR before
# entering the conservative grayscale fallback.
start=s.index('def ocr_workorder_guesses')
end=s.index('\ndef _row_length_token_value',start)
block=s[start:end]
assert block.index('_workorder_confident_magenta_candidate(candidate_crop)') < block.index('gray=cv2.cvtColor(candidate_crop')
assert "re.findall(r'(?<!\\d)\\d{4,5}(?!\\d)',t)" in block  # established fallback remains, now boundary-safe
print('v91 machine-typed pink work-order OCR regression passed')
