import ast
from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
src=SOURCE.read_text(encoding='utf-8')
assert "OCR_CACHE_VERSION = 'v4'" in src, 'v77 must use a fresh OCR cache namespace'
assert 'def _simple_cleaning_length_candidates' in src
assert 'def _fallback_cleaning_length_candidates' in src
assert "value_candidates=_simple_cleaning_length_candidates(value_cell)" in src
assert "note='OCR LENGTH CORRECTED AFTER TOTAL CHECK'" in src

# The normal cleaning parser must not run advanced candidate generation before
# independent total validation fails.
parser=src[src.index('def parse_year15_pair_list'):src.index('def parse_year15_manholes')]
initial=parser[parser.index('value_cell=cut(val_box)'):parser.index('date_evidence=date_reads.get')]
assert '_simple_cleaning_length_candidates(value_cell)' in initial
assert '_fallback_cleaning_length_candidates' not in initial
assert '_ocr_gridless_number_candidates' not in initial

# Exercise the safe arithmetic selector without importing Windows-only modules.
tree=ast.parse(src)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_find_cleaning_total_reconciliation')
ns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
reconcile=ns['_find_cleaning_total_reconciliation']

correct=[369,369,314,2,313,72,268,400,78,345,320,291,366,350,275,224,120]
assert sum(correct)==4476

# Representative pre-fallback errors. Strong fallback evidence supports only the
# real printed corrections. Singleton/two-vote garbage must never be eligible.
wrong=correct.copy(); wrong[14]=75; wrong[15]=294
records=[{'video_length':v,'_length_ocr_candidates':[v]} for v in wrong]
records[14]['_length_fallback_candidates']=[75,275,275,275,275,65,975]
records[15]['_length_fallback_candidates']=[294,224,224,224,224,24,190]
result=reconcile(records,4476)
assert result['matched'],result
assert result['changes']==[(14,75.0,275.0),(15,294.0,224.0)],result

# Weak OCR garbage cannot be selected even when it would make arithmetic work.
weak=[{'video_length':100,'_length_ocr_candidates':[100]} for _ in range(3)]
weak[0]['_length_fallback_candidates']=[200,200]  # only two votes: below threshold
assert not reconcile(weak,400)['matched']

# More than three automatic changes is intentionally fail-closed.
many=[{'video_length':100,'_length_ocr_candidates':[100],
       '_length_fallback_candidates':[101,101,101,101]} for _ in range(4)]
assert not reconcile(many,404)['matched']

# User edits remain authoritative.
records[14]['_length_user_edited']=True
assert not reconcile(records,4476)['matched']

print('v77 simple-first and fail-closed total reconciliation safeguards passed.')
