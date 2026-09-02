from pathlib import Path
import ast

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'mandatory_data_bands=set(range(int(header_band_index)+1,int(total_band_index)))' in src
assert 'mandatory_data_band=band_index in mandatory_data_bands' in src
assert 'if not mandatory_data_band and not match and not endpoint_signal:' in src
assert 'if d is None and not mandatory_data_band:' in src
assert "rec.setdefault('validation_warnings',[]).append('DUPLICATE IN PDF')" in src
assert "if key in seen and kind!='pipes': continue" not in src

# Exercise the production candidate selector without importing Windows-only deps.
tree=ast.parse(src)
names={'_valid_row_length_value','_select_independent_length_candidate'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'MAX_ROW_LENGTH':1700.0}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v85-length-votes>','exec'),ns)
select=ns['_select_independent_length_candidate']

# Grid strokes can make the wrong value win by raw vote count. A visibly observed
# master-plausible value must survive without the master manufacturing anything.
value,confident,source=select([774.0,77.4],[774.0,774.0],'Pipe',76.095994)
assert confident and value==77.4 and source=='sole master-plausible OCR value',(value,source)

# The expanded gray/threshold views can differ only in the final hundredth.
# High-resolution threshold wins this close, already-plausible disagreement.
value,confident,source=select([242.15],[242.16],'Pipe',242.12554)
assert confident and value==242.16 and source=='threshold-supported close disagreement',(value,source)

# Repeated correct observations still win normally.
value,confident,source=select([245.8,245.8],[58.0,285.8],'Pipe',245.343454)
assert confident and value==245.8,(value,source)

# If every OCR view genuinely disagrees and the master cannot safely narrow it,
# fail closed rather than inventing a result.
value,confident,source=select([100.0],[600.0],'Pipe',300.0)
assert not confident and value is None

print('v85 mandatory-row and independent-length-vote regression passed.')
