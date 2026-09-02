from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
src=path.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global src
    if old not in src:
        raise SystemExit(f'missing patch target: {label}')
    src=src.replace(old,new,1)

replace_once(
"from datetime import datetime\n",
"from datetime import datetime\nfrom decimal import Decimal, InvalidOperation\n",
'decimal import')

replace_once(
"""def parse_float(s):
    if s is None: return None
    s = str(s).strip().replace(',', '')
    m = re.search(r'\\d+(?:\\.\\d+)?', s)
    return float(m.group()) if m else None


def parse_date_text(text):
""",
"""def parse_float(s):
    if s is None: return None
    s = str(s).strip().replace(',', '')
    m = re.search(r'\\d+(?:\\.\\d+)?', s)
    return float(m.group()) if m else None


def _pdf_decimal(value):
    \"\"\"Convert an OCR/user numeric value to base-10 without rounding it.\"\"\"
    if value is None: return None
    try: return Decimal(str(value).replace(',','').strip())
    except (InvalidOperation,ValueError,TypeError): return None


def _format_pdf_number(value):
    \"\"\"Display a PDF numeric value without changing its numeric precision.\"\"\"
    number=_pdf_decimal(value)
    if number is None: return ''
    text=format(number,'f')
    if '.' in text: text=text.rstrip('0').rstrip('.')
    return text or '0'


def parse_date_text(text):
""",
'exact PDF numeric helpers')

replace_once(
"""    rounded=[round(float(x),2) for x in cands if 0<float(x)<5000]
    if not rounded: return None
    counts={value:rounded.count(value) for value in set(rounded)}
""",
"""    values=[float(x) for x in cands if 0<float(x)<5000]
    if not values: return None
    counts={value:values.count(value) for value in set(values)}
""",
'cleaning vote no rounding')

replace_once(
"""    rounded=[round(float(x),2) for x in (cands or []) if 0<float(x)<5000]
    if not rounded: return None,False
    counts={value:rounded.count(value) for value in set(rounded)}
""",
"""    values=[float(x) for x in (cands or []) if 0<float(x)<5000]
    if not values: return None,False
    counts={value:values.count(value) for value in set(values)}
""",
'stable numeric vote no rounding')

replace_once(
"""    rounded=[round(float(x),2) for x in cands if 0<float(x)<1000000]
    if not rounded: return None,False
    counts={value:rounded.count(value) for value in set(rounded)}
""",
"""    values=[float(x) for x in cands if 0<float(x)<1000000]
    if not values: return None,False
    counts={value:values.count(value) for value in set(values)}
""",
'printed total vote no rounding')

replace_once(
"""    values=[]; confident=True
    for source in found:
        info=source.get('info') or {}
        value=info.get('value')
        if value is not None: values.append(float(value))
        if not info.get('confident'): confident=False
    pages=[source.get('page') for source in found if source.get('page') is not None]
    if len(found)==1 and len(values)==1:
        total=round(values[0],2); mode='single printed work-order total'
    elif len(found)==len(sources) and len(values)==len(found):
        total=round(sum(values),2); mode='sum of printed page totals'
    elif values:
        total=round(sum(values),2); mode='partial printed page totals'; confident=False
""",
"""    values=[]; confident=True
    for source in found:
        info=source.get('info') or {}
        value=_pdf_decimal(info.get('value'))
        if value is not None: values.append(value)
        if not info.get('confident'): confident=False
    pages=[source.get('page') for source in found if source.get('page') is not None]
    if len(found)==1 and len(values)==1:
        total=float(values[0]); mode='single printed work-order total'
    elif len(found)==len(sources) and len(values)==len(found):
        total=float(sum(values,Decimal('0'))); mode='sum of printed page totals'
    elif values:
        total=float(sum(values,Decimal('0'))); mode='partial printed page totals'; confident=False
""",
'printed source totals exact decimal')

replace_once(
"""def _length_total_result(records,expected_total):
    \"\"\"Compare exactly what is visible in the summary with a verified PDF total.\"\"\"
    values=[]; missing=0
    for record in records:
        value=record.get('video_length')
        if value is None: missing+=1
        else:
            try: values.append(float(value))
            except Exception: missing+=1
    summary_total=round(sum(values),2)
    expected=None if expected_total is None else round(float(expected_total),2)
    difference=None if expected is None else round(summary_total-expected,2)
    matches=expected is not None and missing==0 and abs(difference)<=.01
    return {'summary_total':summary_total,'expected_total':expected,
            'difference':difference,'missing':missing,'matches':matches}
""",
"""def _length_total_result(records,expected_total):
    \"\"\"Compare exact base-10 PDF values; never round rows or totals to reconcile.\"\"\"
    values=[]; missing=0
    for record in records:
        value=_pdf_decimal(record.get('video_length'))
        if value is None: missing+=1
        else: values.append(value)
    summary_decimal=sum(values,Decimal('0'))
    expected_decimal=_pdf_decimal(expected_total)
    difference_decimal=None if expected_decimal is None else summary_decimal-expected_decimal
    matches=expected_decimal is not None and missing==0 and difference_decimal==Decimal('0')
    return {'summary_total':float(summary_decimal),
            'expected_total':None if expected_decimal is None else float(expected_decimal),
            'difference':None if difference_decimal is None else float(difference_decimal),
            'missing':missing,'matches':matches}
""",
'exact total reconciliation')

replace_once(
"""        def cut(box,right_bleed=False):
            x1=max(0,int(left+box[0]*tw)); x2=min(w,int(left+box[1]*tw))
            if right_bleed and x2>x1:
                x2=min(w,x2+max(2,int(round((x2-x1)*.02))))
            return img[y1:y2,x1:x2]
""",
"""        def cut(box,right_bleed=False,vertical_bleed=0):
            x1=max(0,int(left+box[0]*tw)); x2=min(w,int(left+box[1]*tw))
            if right_bleed and x2>x1:
                x2=min(w,x2+max(2,int(round((x2-x1)*.02))))
            bleed=max(0,int(vertical_bleed or 0))
            yy1=max(0,y1-bleed); yy2=min(h,y2+bleed)
            return img[yy1:yy2,x1:x2]
""",
'vertical bleed crop')

replace_once(
"""        else:
            # Pair-table video lengths get one non-destructive full-cell read
            # before the established transformed OCR fallback. This prevents
            # ruled-cell edge cleanup from clipping digits or decimal points.
            value_candidates=_direct_pair_length_candidates(value_cell)
            if not value_candidates:
                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
            value=_choose_length(value_candidates,expected)
""",
"""        else:
            # Pair-table video lengths start with the exact detected row band.
            # If that untouched cell is missing or wildly implausible against the
            # master, independently reread a view with two pixels of vertical
            # breathing room. Both values remain OCR-observed; nothing is rounded
            # or manufactured from the master/printed total.
            value_candidates=_direct_pair_length_candidates(value_cell)
            direct_value=_choose_length(value_candidates,None) if value_candidates else None
            needs_vertical_retry=(not value_candidates)
            if (not needs_vertical_retry and expected not in (None,0) and direct_value is not None):
                needs_vertical_retry=(abs(float(direct_value)-float(expected))/max(float(expected),1.0) >= .35)
            if needs_vertical_retry:
                expanded_candidates=_direct_pair_length_candidates(cut(val_box,vertical_bleed=2))
                for candidate in expanded_candidates:
                    if candidate not in value_candidates: value_candidates.append(candidate)
            if not value_candidates:
                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
            value=_choose_length(value_candidates,expected)
""",
'pipe vertical retry')

replace_once(
"distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}",
"distinct={float(x) for x in value_candidates if 0<float(x)<5000}",
'cleaning distinct no rounding')

replace_once(
"""        values=(r['kind'],r['display_asset'],'' if r['video_length'] is None else f\"{r['video_length']:.1f}\",
""",
"""        values=(r['kind'],r['display_asset'],_format_pdf_number(r.get('video_length')),
""",
'summary exact number display')

replace_once(
"""        values=('Trouble',ticket.get('pipe_id',''),
                '' if ticket.get('map_length') is None else f\"{ticket['map_length']:.1f}\",
""",
"""        values=('Trouble',ticket.get('pipe_id',''),
                _format_pdf_number(ticket.get('map_length')),
""",
'ticket exact number display')

replace_once(
"initial='' if expected is None else f'{float(expected):g}'",
"initial=_format_pdf_number(expected)",
'total dialog initial exact')

replace_once(
"f\"PDF total read: {initial or 'UNREADABLE'}\\n\"\n                 f\"Summary length total: {check.get('summary_total',0):g}\\n\"",
"f\"PDF total read: {initial or 'UNREADABLE'}\\n\"\n                 f\"Summary length total: {_format_pdf_number(check.get('summary_total',0))}\\n\"",
'total dialog summary exact')

replace_once(
"details+=f\"Difference: {abs(check.get('difference') or 0):g} ft\\n\"",
"details+=f\"Difference: {_format_pdf_number(abs(check.get('difference') or 0))} ft\\n\"",
'total dialog difference exact')

replace_once(
"""                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, \"
                         f\"SUMMARY {result['summary_total']:g}; {result['missing']} LENGTH(S) MISSING\")
""",
"""                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {_format_pdf_number(expected)}, \"
                         f\"SUMMARY {_format_pdf_number(result['summary_total'])}; {result['missing']} LENGTH(S) MISSING\")
""",
'total missing warning exact')

replace_once(
"""                warning=(f\"TOTAL LENGTH NEEDS VERIFICATION — PDF TOTAL {expected:g}, \"
                         f\"SUMMARY {result['summary_total']:g}\")
""",
"""                warning=(f\"TOTAL LENGTH NEEDS VERIFICATION — PDF TOTAL {_format_pdf_number(expected)}, \"
                         f\"SUMMARY {_format_pdf_number(result['summary_total'])}\")
""",
'total untrusted warning exact')

replace_once(
"""                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, \"
                         f\"SUMMARY {result['summary_total']:g}, DIFF {abs(result['difference']):g} FT\")
""",
"""                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {_format_pdf_number(expected)}, \"
                         f\"SUMMARY {_format_pdf_number(result['summary_total'])}, DIFF {_format_pdf_number(abs(result['difference']))} FT\")
""",
'total mismatch warning exact')

replace_once(
"f\"Work Order {check.get('wo','')} {check.get('kind','')} now reconciles exactly at {verified:g} ft.\"",
"f\"Work Order {check.get('wo','')} {check.get('kind','')} now reconciles exactly at {_format_pdf_number(verified)} ft.\"",
'verified success exact display')

replace_once(
"f\"The verified PDF total is {verified:g} ft, but the summary currently totals {check.get('summary_total',0):g} ft.\\n\\n\"",
"f\"The verified PDF total is {_format_pdf_number(verified)} ft, but the summary currently totals {_format_pdf_number(check.get('summary_total',0))} ft.\\n\\n\"",
'verified mismatch exact display')

path.write_text(src,encoding='utf-8')

reg=Path('working_source/tests/regression_v83_exact_pdf_numbers.py')
reg.write_text(r'''from pathlib import Path
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
''',encoding='utf-8')
print('v83 exact PDF numbers and pipe retry patch applied')
