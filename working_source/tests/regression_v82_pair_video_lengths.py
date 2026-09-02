from pathlib import Path
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
