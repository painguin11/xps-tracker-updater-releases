from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'working_source/app/reno_scan_updater.py'
TEST=ROOT/'working_source/tests/regression_post_v97_cleaning_clipped_digits.py'
CONTEXT=ROOT/'PROJECT_CONTEXT.md'
CHECKLIST=ROOT/'RELEASE_CHECKLIST.md'


def replace_once(path,old,new):
    text=path.read_text(encoding='utf-8')
    if new in text:
        return False
    if old not in text:
        raise RuntimeError(f'Patch anchor missing in {path}: {old[:120]!r}')
    path.write_text(text.replace(old,new,1),encoding='utf-8')
    return True

old_func='''def _conservative_cleaning_reread(cell_img):
    """Reread one suspect cleaning cell without master/total arithmetic."""
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return {'value':None,'confident':False,'source':'no cell','candidates':[]}
    direct=_ocr_length_candidates(cell_img,fast_plain=True)
    value,confident=_stable_numeric_vote(direct,2)
    if confident:
        return {'value':value,'confident':True,'source':'direct cell','candidates':direct}
    gridless=_ocr_gridless_number_candidates(cell_img,True,row_length=True)
    value,confident=_stable_numeric_vote(gridless,3)
    if confident:
        return {'value':value,'confident':True,'source':'gridless cell','candidates':gridless}
    return {'value':None,'confident':False,'source':'unresolved','candidates':list(direct)+list(gridless)}
'''
new_func='''def _cleaning_clipped_digit_recovery(prior_candidates,reread_candidates,current,expected):
    """Recover a clipped trailing digit only from independent PDF observations.

    Some right-aligned Wheel Walk values sit directly against the cell rule. One
    OCR view can repeatedly keep only the first digit (34 -> 3, 54 -> 5) while the
    stacked-column read and a gridless cell read both still observe the complete
    value. The master may break a tie only between those independently observed
    candidates; it never supplies or manufactures the replacement value.
    """
    if current is None or expected in (None,0): return None
    try: current_value=float(current); expected_value=float(expected)
    except Exception: return None
    if abs(current_value-expected_value)<=LENGTH_DIFF_THRESHOLD: return None

    def valid_unique(values):
        out=[]
        for raw in values or []:
            if not _valid_row_length_value(raw): continue
            value=round(float(raw),2)
            if value not in out: out.append(value)
        return out
    prior=valid_unique(prior_candidates); reread=valid_unique(reread_candidates)
    if not prior or not reread: return None
    current_rounded=round(current_value,2)
    # Deliberately limited to integer-like values where the bad observation is a
    # strict leading substring of a longer independently observed value. This does
    # not guess missing decimals or arbitrary nearby measurements.
    if abs(current_rounded-round(current_rounded))>.001: return None
    current_digits=str(abs(int(round(current_rounded))))
    if not current_digits: return None
    candidates=[]
    for value in prior:
        if value not in reread or value==current_rounded: continue
        if abs(value-round(value))>.001: continue
        digits=str(abs(int(round(value))))
        if len(digits)<=len(current_digits) or not digits.startswith(current_digits): continue
        if abs(value-expected_value)/max(abs(expected_value),1.0)>=.35: continue
        if abs(value-expected_value)>=abs(current_value-expected_value): continue
        candidates.append(value)
    if not candidates: return None
    return min(candidates,key=lambda value:(abs(value-expected_value),value))


def _conservative_cleaning_reread(cell_img,expected=None,prior_candidates=None):
    """Reread one suspect cleaning cell without total arithmetic."""
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return {'value':None,'confident':False,'source':'no cell','candidates':[]}
    direct=_ocr_length_candidates(cell_img,fast_plain=True)
    value,confident=_stable_numeric_vote(direct,2)
    if confident:
        recovered=_cleaning_clipped_digit_recovery(prior_candidates,direct,value,expected)
        if recovered is not None:
            return {'value':recovered,'confident':True,'source':'cross-observed clipped digit','candidates':direct}
        return {'value':value,'confident':True,'source':'direct cell','candidates':direct}
    gridless=_ocr_gridless_number_candidates(cell_img,True,row_length=True)
    value,confident=_stable_numeric_vote(gridless,3)
    if confident:
        recovered=_cleaning_clipped_digit_recovery(prior_candidates,gridless,value,expected)
        if recovered is not None:
            return {'value':recovered,'confident':True,'source':'cross-observed clipped digit','candidates':gridless}
        return {'value':value,'confident':True,'source':'gridless cell','candidates':gridless}
    return {'value':None,'confident':False,'source':'unresolved','candidates':list(direct)+list(gridless)}
'''
replace_once(APP,old_func,new_func)

old_retry='''            elif kind=='Cleaning' and not all_rows:
                cell=record.get('_length_value_cell')
                if cell is None:
                    cell=record.get('_cleaning_value_cell')
                reread=_conservative_cleaning_reread(cell)
'''
new_retry='''            elif kind=='Cleaning' and not all_rows:
                cell=record.get('_length_value_cell')
                if cell is None:
                    cell=record.get('_cleaning_value_cell')
                first_candidates=(record.get('_cleaning_first_candidates') or
                                  record.get('_length_first_candidates') or [])
                reread=_conservative_cleaning_reread(
                    cell,record.get('master_length'),first_candidates)
'''
replace_once(APP,old_retry,new_retry)

TEST.write_text('''from pathlib import Path\nimport sys, types\nimport numpy as np\n\nROOT=Path(__file__).resolve().parents[1]\nsys.path.insert(0,str(ROOT/'app'))\nwin32com=types.ModuleType('win32com'); win32client=types.ModuleType('win32com.client'); win32com.client=win32client\nsys.modules['win32com']=win32com; sys.modules['win32com.client']=win32client\npythoncom=types.ModuleType('pythoncom'); pythoncom.CoInitialize=lambda:None; pythoncom.CoUninitialize=lambda:None; pythoncom.PumpWaitingMessages=lambda:None\nsys.modules['pythoncom']=pythoncom\npywintypes=types.ModuleType('pywintypes'); sys.modules['pywintypes']=pywintypes\nimport reno_scan_updater as xps\n\n# Exact OCR observations reproduced from the two bad 8-26 page-12 Wheel Walk\n# cells. Complete values must be independently observed; master data only breaks\n# the tie between PDF-observed alternatives.\nassert xps._cleaning_clipped_digit_recovery(\n    [34.0,3.0,32.0,2.0,9.0],\n    [3.0,32.0,32.0,3.0,34.0,2.0,2.0,3.0,9.0,9.0],\n    3.0,33.669735)==34.0\nassert xps._cleaning_clipped_digit_recovery(\n    [54.0,5.0],\n    [54.0,5.0,5.0,54.0,5.0,5.0,5.0,5.0],\n    5.0,53.969313)==54.0\n\n# No cross-source observation means no correction. An unrelated nearby master\n# value also cannot manufacture a new measurement.\nassert xps._cleaning_clipped_digit_recovery([34.0,3.0],[3.0,3.0],3.0,33.7) is None\nassert xps._cleaning_clipped_digit_recovery([34.0,7.0],[34.0,7.0,7.0],7.0,33.7) is None\nassert xps._cleaning_clipped_digit_recovery([34.5,3.0],[34.5,3.0,3.0],3.0,34.5) is None\n\ncell=np.zeros((20,80,3),dtype=np.uint8)\norig_len=xps._ocr_length_candidates\norig_grid=xps._ocr_gridless_number_candidates\ntry:\n    xps._ocr_length_candidates=lambda *_a,**_k: []\n    xps._ocr_gridless_number_candidates=lambda *_a,**_k: [54.0,5.0,5.0,54.0,5.0,5.0,5.0]\n    result=xps._conservative_cleaning_reread(cell,53.969313,[54.0,5.0])\n    assert result['confident'] and result['value']==54.0,result\n    assert result['source']=='cross-observed clipped digit',result\nfinally:\n    xps._ocr_length_candidates=orig_len\n    xps._ocr_gridless_number_candidates=orig_grid\n\nsource=(ROOT/'app'/'reno_scan_updater.py').read_text(encoding='utf-8')\nassert "record.get('_cleaning_first_candidates')" in source\nassert "record.get('master_length'),first_candidates" in source\nprint('Post-v97 Cleaning clipped-digit recovery regression passed.')\n''',encoding='utf-8')

context=CONTEXT.read_text(encoding='utf-8')
if '### Unreleased post-v97 Cleaning clipped-digit safeguard' not in context:
    anchor='''- Permanent regression: `working_source/tests/regression_post_v96_msa_editable_fields.py`.\n\nPublic v96 release:\n'''
    insert='''- Permanent regression: `working_source/tests/regression_post_v96_msa_editable_fields.py`.\n\n### Unreleased post-v97 Cleaning clipped-digit safeguard\n\n- 8-26 page 12 exposed two right-aligned Wheel Walk cells where the first pass\n  retained clipped single digits and the whole-table audit could degrade both to 7.\n- Printed `DN-1789 -> DN-2305` is **34 ft** and printed\n  `DN-2306 -> DN-887` is **54 ft**; the page must finish at **8 rows / 1700**.\n- Recovery is allowed only when the complete integer value was observed both in\n  the earlier stacked-column OCR and an independent row-cell OCR pass, and the bad\n  value is a strict leading substring of that longer observation.\n- Master length may break a tie only among those independently PDF-observed\n  candidates. It never supplies or manufactures a Cleaning measurement.\n- Local real-PDF checks passed for 8-26 Cleaning page 10 = 16 / 4614 and page 12\n  = 8 / 1700, plus the affected Cleaning regression matrix pages.\n- Permanent regression: `working_source/tests/regression_post_v97_cleaning_clipped_digits.py`.\n\nPublic v96 release:\n'''
    if anchor not in context: raise RuntimeError('PROJECT_CONTEXT v97 anchor missing')
    context=context.replace(anchor,insert,1)
context=context.replace('''  total reconciliation; Manholes page 6 = 10; Cleaning page 10 = 16 rows / 4614;\n  Cleaning page 12 = 8 rows / 1700.\n''','''  total reconciliation; Manholes page 6 = 10; Cleaning page 10 = 16 rows / 4614;\n  Cleaning page 12 = 8 rows / 1700, including `DN-1789 -> DN-2305 = 34` and\n  `DN-2306 -> DN-887 = 54`.\n''',1)
CONTEXT.write_text(context,encoding='utf-8')

checklist=CHECKLIST.read_text(encoding='utf-8')
if '- post-v97 Cleaning clipped-digit recovery regression;' not in checklist:
    checklist=checklist.replace('''The active baseline includes, at minimum:\n\n- post-v96 editable MSA field / 8-26 OCR regression;\n''','''The active baseline includes, at minimum:\n\n- post-v97 Cleaning clipped-digit recovery regression;\n- post-v96 editable MSA field / 8-26 OCR regression;\n''',1)
if '`working_source/tests/regression_post_v97_cleaning_clipped_digits.py`' not in checklist:
    checklist=checklist.replace('''The current unreleased regressions are:\n\n- `working_source/tests/regression_post_v96_msa_editable_fields.py`\n''','''The current unreleased regressions are:\n\n- `working_source/tests/regression_post_v97_cleaning_clipped_digits.py`\n- `working_source/tests/regression_post_v96_msa_editable_fields.py`\n''',1)
if 'strict leading substring' not in checklist:
    checklist=checklist.replace('''- Cleaning disagreement handling retains competing batch/independent OCR as\n  actual PDF observations; the master may break ties only between observed values.\n''','''- Cleaning disagreement handling retains competing batch/independent OCR as\n  actual PDF observations; the master may break ties only between observed values.\n- A clipped Cleaning digit may be restored only when the longer integer was\n  observed by both stacked-column and independent row-cell OCR, the clipped token\n  is a strict leading substring, and the master only breaks the tie between those\n  PDF-observed candidates.\n''',1)
if 'DN-1789 -> DN-2305 = 34' not in checklist:
    checklist=checklist.replace('''The 8-24 packet is a key continuation/final-total/Manhole-count target, and page 4\nis a key suffix-ID target. The 8-26 packet is a key two-part MSA plus total-reread\ntarget. The 8-28 page-4 table is a key complete-suffix-ID target.\n''','''The 8-24 packet is a key continuation/final-total/Manhole-count target, and page 4\nis a key suffix-ID target. The 8-26 packet is a key two-part MSA plus total-reread\ntarget. On 8-26 page 12, `DN-1789 -> DN-2305 = 34` and\n`DN-2306 -> DN-887 = 54`, and the 8 Cleaning rows total 1700. The 8-28 page-4\ntable is a key complete-suffix-ID target.\n''',1)
CHECKLIST.write_text(checklist,encoding='utf-8')

print('Applied post-v97 Cleaning clipped-digit fix and documentation updates.')
