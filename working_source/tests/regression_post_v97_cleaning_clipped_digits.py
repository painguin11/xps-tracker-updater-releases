from pathlib import Path
import sys, types
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
win32com=types.ModuleType('win32com'); win32client=types.ModuleType('win32com.client'); win32com.client=win32client
sys.modules['win32com']=win32com; sys.modules['win32com.client']=win32client
pythoncom=types.ModuleType('pythoncom'); pythoncom.CoInitialize=lambda:None; pythoncom.CoUninitialize=lambda:None; pythoncom.PumpWaitingMessages=lambda:None
sys.modules['pythoncom']=pythoncom
pywintypes=types.ModuleType('pywintypes'); sys.modules['pywintypes']=pywintypes
import reno_scan_updater as xps

# Exact OCR observations reproduced from the two bad 8-26 page-12 Wheel Walk
# cells. Complete values must be independently observed; master data only breaks
# the tie between PDF-observed alternatives.
assert xps._cleaning_clipped_digit_recovery(
    [34.0,3.0,32.0,2.0,9.0],
    [3.0,32.0,32.0,3.0,34.0,2.0,2.0,3.0,9.0,9.0],
    3.0,33.669735)==34.0
assert xps._cleaning_clipped_digit_recovery(
    [54.0,5.0],
    [54.0,5.0,5.0,54.0,5.0,5.0,5.0,5.0],
    5.0,53.969313)==54.0

# No cross-source observation means no correction. An unrelated nearby master
# value also cannot manufacture a new measurement.
assert xps._cleaning_clipped_digit_recovery([34.0,3.0],[3.0,3.0],3.0,33.7) is None
assert xps._cleaning_clipped_digit_recovery([34.0,7.0],[34.0,7.0,7.0],7.0,33.7) is None
assert xps._cleaning_clipped_digit_recovery([34.5,3.0],[34.5,3.0,3.0],3.0,34.5) is None

cell=np.zeros((20,80,3),dtype=np.uint8)
orig_len=xps._ocr_length_candidates
orig_grid=xps._ocr_gridless_number_candidates
try:
    xps._ocr_length_candidates=lambda *_a,**_k: []
    xps._ocr_gridless_number_candidates=lambda *_a,**_k: [54.0,5.0,5.0,54.0,5.0,5.0,5.0]
    result=xps._conservative_cleaning_reread(cell,53.969313,[54.0,5.0])
    assert result['confident'] and result['value']==54.0,result
    assert result['source']=='cross-observed clipped digit',result
finally:
    xps._ocr_length_candidates=orig_len
    xps._ocr_gridless_number_candidates=orig_grid

source=(ROOT/'app'/'reno_scan_updater.py').read_text(encoding='utf-8')
assert "record.get('_cleaning_first_candidates')" in source
assert "record.get('master_length'),first_candidates" in source
print('Post-v97 Cleaning clipped-digit recovery regression passed.')
