from pathlib import Path

APP = Path('working_source/app/reno_scan_updater.py')
TEST = Path('working_source/tests/regression_v82_pair_video_lengths.py')
text = APP.read_text(encoding='utf-8')

helper_marker = 'def _stable_numeric_vote'
if helper_marker not in text:
    raise SystemExit('stable numeric vote helper marker not found')

if 'def _direct_pair_length_candidates' not in text:
    helper = r'''def _direct_pair_length_candidates(cell_img):
    """Conservative first-pass OCR for pair-table video-length cells.

    Read the untouched ruled cell before any edge trimming, morphology, or grid
    removal can clip a leading/trailing digit or decimal point. Two segmentation
    modes must agree; otherwise the established OCR fallback remains in control.
    Master length is never used here.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    try:
        gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    except Exception:
        return []
    enlarged=cv2.resize(gray,None,fx=3.0,fy=3.0,interpolation=cv2.INTER_CUBIC)
    observed=[]
    for psm in (7,6):
        raw=cached_ocr_string(
            enlarged,
            config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.'
        ).strip().replace(',','')
        for token in re.findall(r'\d+(?:\.\d+)?',raw):
            try:
                value=float(token)
                if 0<value<5000:
                    observed.append(value)
            except Exception:
                pass
    value,stable=_stable_numeric_vote(observed,2)
    return [value] if stable and value is not None else []


'''
    pos = text.index(helper_marker)
    text = text[:pos] + helper + text[pos:]

old = """        else:
            value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
            if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
            value=_choose_length(value_candidates,expected)
"""
new = """        else:
            # Pair-table video lengths get one non-destructive full-cell read
            # before the established transformed OCR fallback. This prevents
            # ruled-cell edge cleanup from clipping digits or decimal points.
            value_candidates=_direct_pair_length_candidates(value_cell)
            if not value_candidates:
                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
            value=_choose_length(value_candidates,expected)
"""
if old not in text:
    raise SystemExit('expected non-cleaning pair-length parser block not found')
text = text.replace(old, new, 1)
APP.write_text(text, encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'def _direct_pair_length_candidates' in src
assert 'value_candidates=_direct_pair_length_candidates(value_cell)' in src
assert "for psm in (7,6):" in src
assert "tessedit_char_whitelist=0123456789." in src
assert "value,stable=_stable_numeric_vote(observed,2)" in src
assert "if not value_candidates:\n                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)" in src

helper=src[src.index('def _direct_pair_length_candidates'):src.index('def _stable_numeric_vote')]
assert 'expected' not in helper
assert '_choose_length' not in helper
assert 'cv2.morphologyEx' not in helper

tree=ast.parse(src)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_stable_numeric_vote')
ns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<stable-vote>','exec'),ns)
vote=ns['_stable_numeric_vote']
assert vote([410.96,410.96],2)==(410.96,True)
assert vote([420.54,420.54],2)==(420.54,True)
assert vote([267.19,267.19],2)==(267.19,True)
assert vote([164.99,164.99],2)==(164.99,True)
assert vote([77.4,77.4],2)==(77.4,True)
assert vote([242.15,242.15],2)==(242.15,True)
assert vote([164.99,164.39],2)==(None,False)

print('v82 non-destructive pair-video length OCR regression passed.')
''', encoding='utf-8')

print('Applied v82 non-destructive pair-video length OCR.')
