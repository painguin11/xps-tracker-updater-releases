from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app' / 'reno_scan_updater.py'
UPDATER = ROOT / 'app' / 'xps_update.py'
README = ROOT / 'app' / 'README_XPS_Tracker_Updater.txt'
TEST = ROOT / 'tests' / 'regression_v91_workorder_color_ocr.py'

src = APP.read_text(encoding='utf-8')

helper = r'''
def _workorder_magenta_variants(cell_img):
    """Return clean binary views of the machine-typed pink/magenta W/O number.

    Work-order numbers on these forms are not handwriting and are not black ink.
    Isolating pixels whose red/blue channels clearly exceed green removes the green
    form rules, black labels, and most scan noise before Tesseract ever sees them.
    Two conservative thresholds cover both saturated originals and faded scans.
    """
    if cell_img is None or getattr(cell_img, 'size', 0) == 0:
        return []
    if len(getattr(cell_img, 'shape', ())) < 3 or cell_img.shape[2] < 3:
        return []
    rgb = cell_img[:, :, :3].astype(np.int16)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    selections = (
        ((red-green) >= 28) & ((blue-green) >= 8) & (red >= 90) & (blue >= 60),
        ((red-green) >= 18) & ((blue-green) >= 4) & (red >= 75) & (blue >= 50) & (((red+blue)//2-green) >= 16),
    )
    variants=[]
    for selected in selections:
        ink=(selected.astype(np.uint8)*255)
        # Close tiny anti-aliasing gaps without using an opening operation that
        # could erase the thin strokes of a typed 1.
        ink=cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((2,2),np.uint8))
        ys,xs=np.where(ink>0)
        if len(xs)<8:
            continue
        pad_x=max(3,int(round((xs.max()-xs.min()+1)*.06)))
        pad_y=max(2,int(round((ys.max()-ys.min()+1)*.18)))
        x1=max(0,int(xs.min())-pad_x); x2=min(ink.shape[1],int(xs.max())+pad_x+1)
        y1=max(0,int(ys.min())-pad_y); y2=min(ink.shape[0],int(ys.max())+pad_y+1)
        binary=255-ink[y1:y2,x1:x2]
        if not getattr(binary,'size',0):
            continue
        binary=cv2.resize(binary,None,fx=4.0,fy=4.0,interpolation=cv2.INTER_NEAREST)
        binary=cv2.copyMakeBorder(binary,18,18,28,28,cv2.BORDER_CONSTANT,value=255)
        if not any(v.shape==binary.shape and np.array_equal(v,binary) for v in variants):
            variants.append(binary)
    return variants


def _workorder_magenta_candidates(cell_img):
    """OCR only five-digit values actually visible in the pink/magenta W/O ink."""
    found=[]
    for image in _workorder_magenta_variants(cell_img):
        for psm in (7,8,13,6):
            text=cached_ocr_string(
                image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789'
            ).strip()
            found.extend(re.findall(r'(?<!\d)\d{5}(?!\d)',text))
    return found
'''

marker='\ndef orient_and_classify(page):\n'
assert '_workorder_magenta_variants' not in src, 'magenta W/O helper already present'
assert marker in src, 'orient_and_classify marker not found'
src=src.replace(marker,'\n'+helper+marker,1)

old_classify=r'''    # Work-order form: check the fixed 5-digit number box independently of label OCR.
    wo_crop = base[int(h*.045):int(h*.135), int(w*.055):int(w*.36)]
    g = cv2.cvtColor(wo_crop, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=1.7, fy=1.7, interpolation=cv2.INTER_CUBIC)
    wo_hits = []
    for psm in (6,7,11,13):
        t = cached_ocr_string(g, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
        wo_hits.extend(re.findall(r'\d{5}', t))
    if wo_hits or 'work order number' in low_top or ('operator' in low_top and ('vehicle' in low_top or 'support' in low_top)):
        return base, 0, top_txt, 'workorder'
'''
new_classify=r'''    # Work-order form: the number is machine-typed in pink/magenta. Use that
    # color signal before grayscale OCR so green rules and black form text disappear.
    wo_color_crop=base[0:int(h*.12),int(w*.09):int(w*.34)]
    wo_hits=_workorder_magenta_candidates(wo_color_crop)
    if not wo_hits:
        # Fail-safe only: classification can still use the older grayscale box if
        # a scan is so faded that its pink channel separation has been destroyed.
        wo_crop=base[int(h*.045):int(h*.135),int(w*.055):int(w*.36)]
        g=cv2.cvtColor(wo_crop,cv2.COLOR_RGB2GRAY)
        g=cv2.resize(g,None,fx=1.7,fy=1.7,interpolation=cv2.INTER_CUBIC)
        for psm in (6,7,11,13):
            t=cached_ocr_string(g,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
            wo_hits.extend(re.findall(r'\d{5}',t))
    if wo_hits or 'work order number' in low_top or ('operator' in low_top and ('vehicle' in low_top or 'support' in low_top)):
        return base,0,top_txt,'workorder'
'''
assert old_classify in src, 'work-order classification block not found'
src=src.replace(old_classify,new_classify,1)

old_doc='''def ocr_workorder_guesses(page, master_index=None, expect_manhole_count=False):
    """Read the Work Order form and PRE-FILL the confirmation dialog.

    These forms contain handwriting, so OCR is only a best guess. The popup remains
    editable, but it should never force the user to retype values that OCR did find.
    """
'''
new_doc='''def ocr_workorder_guesses(page, master_index=None, expect_manhole_count=False):
    """Read the Work Order form and PRE-FILL the confirmation dialog.

    The W/O number is machine-typed in pink/magenta; Operator and Truck may still
    require handwriting OCR. The popup remains editable as the final safety check.
    """
'''
assert old_doc in src, 'ocr_workorder_guesses docstring not found'
src=src.replace(old_doc,new_doc,1)
src=src.replace('crop(.11,.070,.31,.105),  # Reno tight handwritten value','crop(.11,.070,.31,.105),  # Reno tight W/O value',1)
src=src.replace('crop(.11,.012,.31,.052),  # handwriting above the printed box','crop(.11,.012,.31,.052),  # upper W/O value position',1)

old_ocr=r'''    # Work order number: isolate the handwritten number, then use an ensemble.
    wo_crop=candidate_wo_crops[0]
    crop_results=[]
    for candidate_crop in candidate_wo_crops:
        gray=cv2.cvtColor(candidate_crop,cv2.COLOR_RGB2GRAY)
        gray=cv2.resize(gray,None,fx=2.4,fy=2.4,interpolation=cv2.INTER_CUBIC)
        hits=[]
        for psm in (6,7,8,11,13):
            t=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
            hits+=re.findall(r'\d{4,5}',t)
        valid=[x for x in hits if len(x) in (4,5)]
        if valid:
            winner=max(set(valid),key=lambda x:(valid.count(x),len(x)))
            crop_results.append((valid.count(winner),len(valid),len(winner),winner,candidate_crop))
    if crop_results:
        agreement,total,digits_count,wo,wo_crop=max(crop_results,key=lambda x:(x[0],x[1],x[2]))
    else:
        wo=''
    # A broader crop sometimes reads one or two digits that the tight crop misses.
    if not wo:
        broad = _best_ocr_text(crop(.05,.045,.36,.135), psms=(6,11,12,13),whitelist='0123456789')
        exact=re.findall(r'\d{4,5}',broad)
        wo=exact[0] if exact else ''
'''
new_ocr=r'''    # Work order number: isolate the machine-typed pink/magenta ink first.
    # Because the form itself is green/black, this leaves Tesseract almost nothing
    # except the five printed W/O digits. Fixed-position variants still handle scan shift.
    wo_crop=candidate_wo_crops[0]
    color_results=[]
    for candidate_crop in candidate_wo_crops:
        hits=_workorder_magenta_candidates(candidate_crop)
        if hits:
            winner=max(set(hits),key=lambda x:hits.count(x))
            color_results.append((hits.count(winner),len(hits),winner,candidate_crop))
    if color_results:
        agreement,total,wo,wo_crop=max(color_results,key=lambda x:(x[0],x[1]))
    else:
        # Preserve the established grayscale ensemble as a last-resort fallback for
        # unusually faded/desaturated scans. It is no longer the normal W/O path.
        crop_results=[]
        for candidate_crop in candidate_wo_crops:
            gray=cv2.cvtColor(candidate_crop,cv2.COLOR_RGB2GRAY)
            gray=cv2.resize(gray,None,fx=2.4,fy=2.4,interpolation=cv2.INTER_CUBIC)
            hits=[]
            for psm in (6,7,8,11,13):
                t=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
                hits+=re.findall(r'\d{4,5}',t)
            valid=[x for x in hits if len(x) in (4,5)]
            if valid:
                winner=max(set(valid),key=lambda x:(valid.count(x),len(x)))
                crop_results.append((valid.count(winner),len(valid),len(winner),winner,candidate_crop))
        if crop_results:
            agreement,total,digits_count,wo,wo_crop=max(crop_results,key=lambda x:(x[0],x[1],x[2]))
        else:
            wo=''
    # A broader grayscale crop remains only the final fail-safe if color isolation
    # and the tight-crop ensemble both fail completely.
    if not wo:
        broad=_best_ocr_text(crop(.05,.045,.36,.135),psms=(6,11,12,13),whitelist='0123456789')
        exact=re.findall(r'\d{4,5}',broad)
        wo=exact[0] if exact else ''
'''
assert old_ocr in src, 'work-order OCR block not found'
src=src.replace(old_ocr,new_ocr,1)

src=src.replace(
'''    # Small crops are carried into the confirmation dialog so the handwriting is visible
    # directly beside the editable OCR fields.  Keep the work-order preview independent
    # of the tight crop selected for OCR: shifted forms can place the first digits left
    # of an otherwise successful OCR crop (for example, 11976 appeared as 976 onscreen).
    # This wider value-box crop shows the complete handwritten number without changing
    # the OCR ensemble or its selected candidate.
''',
'''    # Small crops are carried into the confirmation dialog beside the editable fields.
    # Keep the W/O preview independent of the tight OCR crop: shifted scans can place
    # the first typed pink digits left of an otherwise successful OCR crop. This wider
    # value-box crop keeps the complete machine-typed W/O visible for confirmation.
''',1)

src,n=re.subn(r"^APP_VERSION\s*=\s*['\"]90['\"]", "APP_VERSION = '91'", src, count=1, flags=re.M)
assert n==1, 'APP_VERSION 90 marker not found exactly once'
APP.write_text(src,encoding='utf-8')

up=UPDATER.read_text(encoding='utf-8')
up,n=re.subn(r'^CURRENT_VERSION\s*=\s*[\"\']90[\"\']', 'CURRENT_VERSION = "91"', up, count=1, flags=re.M)
assert n==1, 'CURRENT_VERSION 90 marker not found exactly once'
UPDATER.write_text(up,encoding='utf-8')

readme=README.read_text(encoding='utf-8')
if 'Version 91 review, endpoint, and work-order OCR improvements' not in readme:
    readme += '''\n\nVersion 91 review, endpoint, and work-order OCR improvements\n-------------------------------------------------------------\n- Shows PDF ID image previews in the existing Yes / No approval popup for suffixed NEW PIPE and NEW MANHOLE assets.\n- Recovers a damaged Pipe/Cleaning endpoint only when numeric bodies were OCR-observed from both PDF cells and identify exactly one directional pipe in the master.\n- Keeps legitimate non-master printed pairs unresolved for Add to Master / Ignore review instead of force-matching them.\n- Reads the five-digit Work Order number as machine-typed pink/magenta text by isolating its color before OCR, removing green form rules and black labels from the primary OCR input.\n- Keeps the established editable W/O confirmation popup and grayscale OCR only as a fallback for unusually faded/desaturated scans.\n'''
README.write_text(readme,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast,re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
assert "APP_VERSION = '91'" in s
assert 'machine-typed pink/magenta' in s
assert '_workorder_magenta_candidates(candidate_crop)' in s

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

# The actual W/O selection path must try color OCR before entering grayscale fallback.
start=s.index('def ocr_workorder_guesses')
end=s.index('\ndef _row_length_token_value',start)
block=s[start:end]
assert block.index('_workorder_magenta_candidates(candidate_crop)') < block.index('gray=cv2.cvtColor(candidate_crop')
assert "re.findall(r'\\d{4,5}',t)" in block  # established fallback remains
print('v91 machine-typed pink work-order OCR regression passed')
''',encoding='utf-8')

print('Applied v91 machine-typed pink work-order OCR patch, version bump, README, and regression.')
