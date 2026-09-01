from pathlib import Path

source=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'def _year15_compact_grid_bands' in source
assert "geometry_source='compact table grid'" in source
assert 'hh>=bh*.18' in source
assert 'rule[2]-rule[1]>=max_span*.85' in source
assert "if not bands:\n        bands,table,column_bounds=_year15_compact_grid_bands(img)" in source
assert source.index('_year15_compact_grid_bands(img)') < source.index("_year15_all_row_bands(img,.04,.90)")
print('Compact Year 15 table fallback guard passed.')
