from pathlib import Path

APP = Path('working_source/app/reno_scan_updater.py')
text = APP.read_text(encoding='utf-8')

# OCR behavior has changed materially since the v2 cache was introduced.  Keep
# the old cache files intact, but stop reusing their stale Tesseract strings.
old = "OCR_CACHE_VERSION = 'v2'"
new = "OCR_CACHE_VERSION = 'v3'"
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit('Unexpected OCR_CACHE_VERSION')

# A date cell such as 8/11/2026 can be returned by Tesseract as
# "8/1 1/2026".  The old generic token walk then also saw the shifted triple
# 1/1/2026 and treated that accidental full-year candidate as strong.  Compact
# only a digit split *between two date separators* before tokenization; do not
# merge ordinary whitespace-separated dates.
old = """    expected_year=expected_date.year if isinstance(expected_date,datetime) else None
    tokens=re.findall(r'\\d+',str(text or ''))
"""
new = """    expected_year=expected_date.year if isinstance(expected_date,datetime) else None
    date_text=str(text or '')
    date_text=re.sub(r'(?<=[/-])\\s*(\\d)\\s+(\\d)\\s*(?=[/-])',r'\\1\\2',date_text)
    date_text=re.sub(r'\\s*([/-])\\s*',r'\\1',date_text)
    tokens=re.findall(r'\\d+',date_text)
"""
if old in text:
    text = text.replace(old, new, 1)
elif "date_text=re.sub(r'(?<=[/-])" not in text:
    raise SystemExit('Sheet-date tokenization block not found')

# Cleaning cells that disagree with the master already enter a slower consensus
# path.  Add the existing grid-rule removal OCR there as an independent reread;
# this is the same technique that reliably recovered the printed 4476 total.
old = """                for ratio in (.015,.030,.045,.060):
                    pad=max(2,int(round(width*ratio)))
                    if width>pad*2+4:
                        consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                value=_choose_cleaning_length(consensus,expected)
"""
new = """                for ratio in (.015,.030,.045,.060):
                    pad=max(2,int(round(width*ratio)))
                    if width>pad*2+4:
                        consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                # If a digit touches or is distorted by a table rule, horizontal
                # trimming alone can repeatedly agree on the same wrong value
                # (for example 275 -> 75 or 224 -> 274).  Remove grid rules and
                # add those OCR observations to the same printed-value vote.
                consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                value=_choose_cleaning_length(consensus,expected)
"""
if old in text:
    text = text.replace(old, new, 1)
elif 'consensus.extend(_ocr_gridless_number_candidates(value_cell,True))' not in text:
    raise SystemExit('Cleaning consensus block not found')

APP.write_text(text, encoding='utf-8')

TEST = Path('working_source/tests/regression_v75_811_ocr.py')
TEST.write_text(r'''import ast
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
''', encoding='utf-8')
