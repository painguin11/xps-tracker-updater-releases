from pathlib import Path
import re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert re.search(r"APP_VERSION = ['\"]\d+['\"]",src)
cache_match=re.search(r"OCR_CACHE_VERSION = ['\"]v(\d+)['\"]",src)
assert cache_match and int(cache_match.group(1))>=5
assert 'def _batch_cleaning_length_candidates' in src
assert '_batch_cleaning_length_candidates(img,bands,table,val_box,total_band_index)' in src
assert 'value_candidates=list(batch_cleaning_values.get(band_index,[]))' in src
# The rollback invariant remains: Cleaning does not use total-driven value
# invention. The gridless fallback is still independent OCR, now with the newer
# row-length validator so >1700 ft and >2 decimal places are rejected.
assert 'consensus.extend(_ocr_gridless_number_candidates(value_cell,True,row_length=True))' in src
assert 'MAX_ROW_LENGTH = 1700.0' in src
assert 'MAX_ROW_LENGTH_DECIMALS = 2' in src
assert "if (kind!='cleaning' and value is not None" in src
assert 'def _simple_cleaning_length_candidates' not in src
assert 'def _fallback_cleaning_length_candidates' not in src
assert 'def retry_total_length_ocr' not in src
assert 'OCR LENGTH RESELECTED USING VERIFIED PDF TOTAL' not in src
# Saved layouts still remain fail-closed: only complete, in-range saved role maps
# are auto-applied; otherwise the user confirmation dialog remains available.
assert "if saved and all(k in saved for k in ('up','down','value','date'))" in src
assert "apply_confirmed_layout(layout,saved)" in src
assert "LayoutConfirmDialog(self,layout,pi+1)" in src
print('v78 cleaning OCR rollback + fail-closed total guard passed.')
