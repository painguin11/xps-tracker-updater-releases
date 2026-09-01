from pathlib import Path
src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "APP_VERSION = '78'" in src
assert "OCR_CACHE_VERSION = 'v5'" in src
assert 'def _choose_cleaning_length' in src
assert 'def _ocr_gridless_number_candidates' in src
assert 'consensus.extend(_ocr_gridless_number_candidates(value_cell,True))' in src
assert 'def _simple_cleaning_length_candidates' not in src
assert 'def _fallback_cleaning_length_candidates' not in src
print('v78 known-good cleaning OCR rollback guard passed.')
