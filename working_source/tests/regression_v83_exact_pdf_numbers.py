from pathlib import Path
import ast
from decimal import Decimal, InvalidOperation

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

# PDF-derived measurements must never be deliberately rounded for voting,
# display, total aggregation, or reconciliation.
assert 'def _pdf_decimal(value):' in src
assert 'def _format_pdf_number(value):' in src
assert "f\"{r['video_length']:.1f}\"" not in src
assert "f\"{ticket['map_length']:.1f}\"" not in src
assert 'rounded=[round(float(x),2)' not in src
assert 'summary_total=round(sum(values),2)' not in src
assert 'expected=None if expected_total is None else round(float(expected_total),2)' not in src
assert "difference_decimal==Decimal('0')" in src
assert 'distinct={float(x) for x in value_candidates' in src

# The pipe retry may expose more of the original PDF cell, but it may only add
# OCR-observed candidates. It cannot synthesize, round, or substitute a value.
assert 'def cut(box,right_bleed=False,vertical_bleed=0):' in src
assert 'expanded_candidates=_direct_pair_length_candidates(cut(val_box,vertical_bleed=2))' in src
assert 'if candidate not in value_candidates: value_candidates.append(candidate)' in src
assert 'value=_choose_length(value_candidates,expected)' in src

# Exercise exact display and exact base-10 total reconciliation without Tk.
tree=ast.parse(src)
names={'_pdf_decimal','_format_pdf_number','_length_total_result'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'Decimal':Decimal,'InvalidOperation':InvalidOperation}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<exact-pdf-numbers>','exec'),ns)
fmt=ns['_format_pdf_number']; total=ns['_length_total_result']
assert fmt(410.96)=='410.96'
assert fmt(77.4)=='77.4'
assert fmt(242.15)=='242.15'
assert fmt(4614.0)=='4614'
assert total([{'video_length':410.96},{'video_length':77.4}],488.36)['matches'] is True
assert total([{'video_length':410.96},{'video_length':77.4}],488.35)['matches'] is False
assert total([{'video_length':0.1},{'video_length':0.2}],0.3)['matches'] is True

print('v83 exact PDF numeric precision regression passed.')
