import ast
import re
from datetime import datetime
from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
wanted={'_parse_sheet_date_text_candidates','_choose_cleaning_length'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
ns={'datetime':datetime,'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)

expected=datetime(2026,8,11)
parse=ns['_parse_sheet_date_text_candidates']

# Tesseract actually produces these whitespace splits on the 8/11 fixture.
reads=parse('8/1 1/2026',expected)
assert reads and all(d==expected for d,_ in reads), reads
reads=parse('8/11/ 2026',expected)
assert reads and all(d==expected for d,_ in reads), reads
reads=parse('8/ 11/2026',expected)
assert reads and all(d==expected for d,_ in reads), reads

# Do not destroy the old no-separator fallback or a genuinely different date.
reads=parse('8 12 2026',expected)
assert any(d==datetime(2026,8,12) for d,_ in reads), reads
reads=parse('8/12/2026',expected)
assert any(d==datetime(2026,8,12) and strong for d,strong in reads), reads

choose=ns['_choose_cleaning_length']
# Model the extra gridless evidence seen on the supplied page: the clean reread
# must be able to overturn a border-distorted fast read, but only with values OCR
# actually observed.
assert choose([75,75,275,275,275,275,275],273.4)==275
assert choose([274,274,224,224,224,224,226],223.5)==224

assert "OCR_CACHE_VERSION = 'v3'" in text
assert 'consensus.extend(_ocr_gridless_number_candidates(value_cell,True))' in text
print('v75 8/11 cleaning OCR/cache/date regression safeguards passed.')
