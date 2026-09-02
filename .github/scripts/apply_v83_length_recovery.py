from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
s=path.read_text(encoding='utf-8')

def rep(old,new,count=1):
    global s
    found=s.count(old)
    if found < count:
        raise SystemExit(f'missing patch marker ({found} < {count}): {old[:120]!r}')
    s=s.replace(old,new,count)

rep("LENGTH_DIFF_THRESHOLD = 4.5\n", "LENGTH_DIFF_THRESHOLD = 4.5\nMAX_ROW_LENGTH = 1700.0\nMAX_ROW_LENGTH_DECIMALS = 2\n")

marker="def _ocr_digits(cell_img, decimal=False, fast_plain=False):\n"
insert="""def _row_length_token_value(token):
    \"\"\"Parse one OCR row-length token without rounding or repairing it.\"\"\"
    raw=str(token or '').strip().replace(',','')
    if not re.fullmatch(rf'\\d+(?:\\.\\d{{1,{MAX_ROW_LENGTH_DECIMALS}}})?',raw):
        return None
    try:
        value=float(raw)
    except Exception:
        return None
    return value if 0 < value <= MAX_ROW_LENGTH else None


def _valid_row_length_value(value):
    try:
        numeric=float(value)
    except Exception:
        return False
    return 0 < numeric <= MAX_ROW_LENGTH


def _ocr_length_candidates(cell_img, fast_plain=False):
    \"\"\"OCR one Pipe/Cleaning measurement using the hard field-length rules.\"\"\"
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    gray=cv2.resize(gray,None,fx=1.8,fy=1.8,interpolation=cv2.INTER_CUBIC)
    variants=[gray,cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    if not fast_plain:
        try:
            green=cv2.normalize(cell_img[:,:,1],None,0,255,cv2.NORM_MINMAX)
            green=cv2.resize(green,None,fx=1.8,fy=1.8,interpolation=cv2.INTER_CUBIC)
            variants.extend(cv2.threshold(green,t,255,cv2.THRESH_BINARY)[1] for t in (120,140,160))
        except Exception:
            pass
    found=[]
    for image in variants:
        for psm in ((7,) if fast_plain else (7,6)):
            raw=cached_ocr_string(image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.').strip().replace(',','')
            for token in re.findall(r'\\d+(?:\\.\\d+)?',raw):
                value=_row_length_token_value(token)
                if value is not None:
                    found.append(value)
    return found


"""
if marker not in s: raise SystemExit('missing _ocr_digits marker')
s=s.replace(marker,insert+marker,1)

# Reno surveyed lengths are row measurements too.
s=s.replace("length_candidates=_ocr_digits(len_img,True)\n", "length_candidates=_ocr_length_candidates(len_img,fast_plain=False)\n",1)

# Add a row-length mode to gridless OCR, while leaving printed totals unrestricted.
rep("def _ocr_gridless_number_candidates(cell_img, decimal=False):\n", "def _ocr_gridless_number_candidates(cell_img, decimal=False, row_length=False):\n")
old="""            if decimal:
                for value in re.findall(r'\\d+(?:\\.\\d+)?',raw.replace(',','')):
                    try: found.append(float(value))
                    except Exception: pass
            else:
                found.extend(re.findall(r'\\d+',raw))
"""
new="""            if decimal:
                for token in re.findall(r'\\d+(?:\\.\\d+)?',raw.replace(',','')):
                    if row_length:
                        value=_row_length_token_value(token)
                        if value is not None: found.append(value)
                    else:
                        try: found.append(float(token))
                        except Exception: pass
            else:
                found.extend(re.findall(r'\\d+',raw))
"""
rep(old,new)

# All row-value selectors enforce the 1700-ft maximum. Decimal precision is
# enforced before float conversion by the OCR token readers above.
s=s.replace("if 0 < float(x) < 5000", "if _valid_row_length_value(x)")
s=s.replace("if 0<float(x)<5000", "if _valid_row_length_value(x)")
s=s.replace("if 0 < value < 5000", "if _valid_row_length_value(value)")
s=s.replace("if 0<value<5000", "if _valid_row_length_value(value)")
s=s.replace("if 0<numeric<5000", "if _valid_row_length_value(numeric)")

# Direct pipe OCR: reject 3+ decimals / >1700 before it can become a stable vote.
old="""        for token in re.findall(r'\\d+(?:\\.\\d+)?',raw):
            try:
                value=float(token)
                if _valid_row_length_value(value):
                    observed.append(value)
            except Exception:
                pass
"""
new="""        for token in re.findall(r'\\d+(?:\\.\\d+)?',raw):
            value=_row_length_token_value(token)
            if value is not None:
                observed.append(value)
"""
if old in s: s=s.replace(old,new,1)
else:
    old2="""        for token in re.findall(r'\\d+(?:\\.\\d+)?',raw):
            try:
                value=float(token)
                if 0<value<5000:
                    observed.append(value)
            except Exception:
                pass
"""
    rep(old2,new)

# Conservative cleaning reread must use row-length constraints, not generic numeric OCR.
rep("direct=_ocr_digits(cell_img,True,fast_plain=True)\n", "direct=_ocr_length_candidates(cell_img,fast_plain=True)\n",1)
rep("gridless=_ocr_gridless_number_candidates(cell_img,True)\n", "gridless=_ocr_gridless_number_candidates(cell_img,True,row_length=True)\n",1)

# Batch cleaning values also reject impossible OCR tokens before they reach the row.
old="""        for value in values:
            try:
                numeric=float(value)
                if _valid_row_length_value(numeric):
                    bucket.append(numeric)
            except Exception:
                pass
"""
new="""        for token in values:
            numeric=_row_length_token_value(token)
            if numeric is not None:
                bucket.append(numeric)
"""
if old in s: s=s.replace(old,new,1)
else:
    old2="""        for value in values:
            try:
                numeric=float(value)
                if 0<numeric<5000:
                    bucket.append(numeric)
            except Exception:
                pass
"""
    rep(old2,new)

# Year 15 row fallbacks use constrained row OCR. Printed-total OCR remains generic.
s=s.replace("value_candidates=_ocr_digits(value_cell,True,fast_plain=True)\n", "value_candidates=_ocr_length_candidates(value_cell,fast_plain=True)\n")
s=s.replace("if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)\n", "if not value_candidates: value_candidates=_ocr_length_candidates(value_cell,fast_plain=False)\n")
s=s.replace("consensus.extend(_ocr_gridless_number_candidates(value_cell,True))\n", "consensus.extend(_ocr_gridless_number_candidates(value_cell,True,row_length=True))\n")
s=s.replace("expanded=_ocr_digits(cut(val_box),True,fast_plain=False)\n", "expanded=_ocr_length_candidates(cut(val_box),fast_plain=False)\n")

# Store the exact and expanded PDF cells for mismatch recovery on both activities.
old="""        if kind=='cleaning':
            rec['_cleaning_value_cell']=value_cell.copy() if getattr(value_cell,'size',0) else None
            rec['_cleaning_first_candidates']=list(value_candidates or [])
"""
new="""        rec['_length_value_cell']=value_cell.copy() if getattr(value_cell,'size',0) else None
        expanded_value_cell=cut(val_box,vertical_bleed=2)
        rec['_length_expanded_cell']=expanded_value_cell.copy() if getattr(expanded_value_cell,'size',0) else None
        rec['_length_first_candidates']=list(value_candidates or [])
        if kind=='cleaning':
            # Retain the older names for compatibility with existing cleaning
            # reread logic/tests while all activities use the shared cells above.
            rec['_cleaning_value_cell']=rec['_length_value_cell']
            rec['_cleaning_first_candidates']=list(value_candidates or [])
"""
rep(old,new)

# Independent views used only after a work-order total fails. Pipe thresholded
# views are deliberately separate from the normal grayscale first pass; the
# attached 8-26 scan shows this recovers 242.16/372.28/360.3 without rounding.
marker="def _conservative_cleaning_reread(cell_img):\n"
insert="""def _independent_row_length_read(cell_img,expanded_img=None,kind='Pipe'):
    \"\"\"Cross-check a row from independent OCR views without inventing a value.\"\"\"
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return {'value':None,'confident':False,'candidates':[],'source':'no cell'}
    views=[cell_img]
    if expanded_img is not None and getattr(expanded_img,'size',0):
        views.append(expanded_img)
    gray_values=[]; threshold_values=[]
    for view in views:
        gray=cv2.cvtColor(view,cv2.COLOR_RGB2GRAY)
        normal=cv2.resize(gray,None,fx=3.0,fy=3.0,interpolation=cv2.INTER_CUBIC)
        threshold_base=cv2.resize(gray,None,fx=4.0,fy=4.0,interpolation=cv2.INTER_CUBIC)
        thresholded=cv2.threshold(threshold_base,200,255,cv2.THRESH_BINARY)[1]
        for psm in (7,6):
            for image,bucket in ((normal,gray_values),(thresholded,threshold_values)):
                raw=cached_ocr_string(image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.').strip().replace(',','')
                for token in re.findall(r'\\d+(?:\\.\\d+)?',raw):
                    value=_row_length_token_value(token)
                    if value is not None: bucket.append(value)
    threshold_value,threshold_stable=_stable_numeric_vote(threshold_values,2)
    gray_value,gray_stable=_stable_numeric_vote(gray_values,2)
    if kind=='Pipe' and threshold_stable:
        return {'value':threshold_value,'confident':True,'candidates':gray_values+threshold_values,
                'source':'independent threshold views'}
    if gray_stable:
        return {'value':gray_value,'confident':True,'candidates':gray_values+threshold_values,
                'source':'independent grayscale views'}
    if threshold_stable:
        return {'value':threshold_value,'confident':True,'candidates':gray_values+threshold_values,
                'source':'independent threshold views'}
    return {'value':None,'confident':False,'candidates':gray_values+threshold_values,'source':'independent views disagree'}


"""
if marker not in s: raise SystemExit('missing conservative reread marker')
s=s.replace(marker,insert+marker,1)

# Replace cleaning-only mismatch recovery with a shared two-stage recovery.
start=s.index("    def _retry_cleaning_total_mismatch(self,check,force=False):\n")
end=s.index("\n    def refresh_total_check(self,check,redraw=True):",start)
new_block="""    def _retry_length_total_mismatch(self,check,all_rows=False,force=False):
        \"\"\"Reread suspect rows first; if requested, cross-check the whole activity.\"\"\"
        indexed=self._total_check_records(check)
        if not indexed: return False
        expected_total=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')
        rows=[record for _,record in indexed]
        if _length_total_result(rows,expected_total).get('matches'): return False
        suspects=[]
        for index,record in indexed:
            if record.get('_length_user_edited'): continue
            if record.get('_length_crosscheck_attempted') and not force: continue
            current=record.get('video_length'); master=record.get('master_length')
            invalid_current=(current is None or not _valid_row_length_value(current))
            far_from_master=(current is not None and master not in (None,0) and
                             abs(float(current)-float(master))>LENGTH_DIFF_THRESHOLD)
            if all_rows or invalid_current or far_from_master:
                priority=float('inf') if invalid_current else (abs(float(current)-float(master)) if master not in (None,0) else 0.0)
                suspects.append((priority,index,record))
        suspects.sort(key=lambda item:item[0],reverse=True)
        changed=False
        for _priority,index,record in suspects:
            record['_length_crosscheck_attempted']=True
            kind=record.get('kind') or check.get('kind')
            if kind=='Cleaning' and not all_rows:
                reread=_conservative_cleaning_reread(record.get('_length_value_cell') or record.get('_cleaning_value_cell'))
            else:
                reread=_independent_row_length_read(record.get('_length_value_cell'),record.get('_length_expanded_cell'),kind)
            record['_length_crosscheck_source']=reread.get('source')
            new_value=reread.get('value') if reread.get('confident') else None
            if new_value is None or not _valid_row_length_value(new_value):
                continue
            old_value=record.get('video_length')
            if old_value is not None and float(old_value)==float(new_value):
                continue
            # Cleaning's aligned-column first pass is intentionally conservative.
            # During the all-row audit, a conflicting isolated-cell read is review
            # evidence, not permission to overwrite an already valid batch value.
            if kind=='Cleaning' and all_rows and _valid_row_length_value(old_value):
                record['_length_crosscheck_conflict']=new_value
                continue
            record['video_length']=float(new_value)
            refresh_length_status(record); changed=True
            current_rows=[r for _,r in self._total_check_records(check)]
            if _length_total_result(current_rows,expected_total).get('matches'):
                break
        return changed

    def _retry_cleaning_total_mismatch(self,check,force=False):
        \"\"\"Compatibility wrapper for the established cleaning recovery hook.\"\"\"
        if check.get('kind')!='Cleaning': return False
        return self._retry_length_total_mismatch(check,all_rows=False,force=force)
"""
s=s[:start]+new_block+s[end:]

# A mismatch now gets the requested two-stage recovery before prompting.
old="""            self.refresh_total_check(check)
            if not check.get('passed') and kind=='Cleaning':
                if self._retry_cleaning_total_mismatch(check):
                    self.refresh_total_check(check)
            if not check.get('passed'): self.prompt_total_check(check)
"""
new="""            self.refresh_total_check(check)
            if not check.get('passed'):
                if self._retry_length_total_mismatch(check,all_rows=False):
                    self.refresh_total_check(check)
            if not check.get('passed'):
                if self._retry_length_total_mismatch(check,all_rows=True):
                    self.refresh_total_check(check)
            if not check.get('passed'): self.prompt_total_check(check)
"""
rep(old,new)

# After the user corrects a printed total, rerun both recovery stages against the
# new target before asking them to manually edit row values.
old="""        if check.get('kind')=='Cleaning':
            self._retry_cleaning_total_mismatch(check,force=True)
        passed=self.refresh_total_check(check)
"""
new="""        self._retry_length_total_mismatch(check,all_rows=False,force=True)
        self.refresh_total_check(check)
        if not check.get('passed'):
            self._retry_length_total_mismatch(check,all_rows=True,force=True)
        passed=self.refresh_total_check(check)
"""
rep(old,new)

# Manual row edits obey the same physical row-length ceiling; totals remain unrestricted.
old="""                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())
                if r.get('kind')=='Cleaning' and old_length!=r.get('video_length'):
"""
new="""                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())
                if r.get('kind') in ('Pipe','Cleaning') and r.get('video_length') is not None and not _valid_row_length_value(r.get('video_length')):
                    raise ValueError(f'Individual activity length must be greater than 0 and no more than {MAX_ROW_LENGTH:g} ft.')
                if r.get('kind')=='Cleaning' and old_length!=r.get('video_length'):
"""
rep(old,new)

path.write_text(s,encoding='utf-8')

# Add a focused regression for the new constraints/recovery flow.
test=Path('working_source/tests/regression_v83_length_recovery.py')
test.write_text(r'''from pathlib import Path
import ast,re

p=Path('working_source/app/reno_scan_updater.py')
s=p.read_text(encoding='utf-8')
assert 'MAX_ROW_LENGTH = 1700.0' in s
assert 'MAX_ROW_LENGTH_DECIMALS = 2' in s
assert 'def _row_length_token_value(token):' in s
assert 'def _ocr_length_candidates(cell_img, fast_plain=False):' in s
assert 'def _independent_row_length_read(cell_img,expanded_img=None,kind=' in s
assert 'cv2.threshold(threshold_base,200,255,cv2.THRESH_BINARY)' in s
assert "kind=='Pipe' and threshold_stable" in s
assert 'def _retry_length_total_mismatch(self,check,all_rows=False,force=False):' in s
assert 'self._retry_length_total_mismatch(check,all_rows=False)' in s
assert 'self._retry_length_total_mismatch(check,all_rows=True)' in s
assert s.index('self._retry_length_total_mismatch(check,all_rows=False)') < s.index('self._retry_length_total_mismatch(check,all_rows=True)')
assert "rec['_length_value_cell']" in s and "rec['_length_expanded_cell']" in s
assert '_ocr_gridless_number_candidates(cell_img,True,row_length=True)' in s
# Printed work-order/page totals deliberately remain allowed above 1700.
block=s[s.index('def _read_pair_table_printed_total'):s.index('def _resolve_printed_total_sources')]
assert '_ocr_digits(cell,True,fast_plain=True)' in block
assert 'row_length=True' not in block

# Execute only the pure token helper plus constants.
tree=ast.parse(s)
nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('MAX_ROW_LENGTH','MAX_ROW_LENGTH_DECIMALS') for t in node.targets): nodes.append(node)
    if isinstance(node,ast.FunctionDef) and node.name in ('_row_length_token_value','_valid_row_length_value'): nodes.append(node)
ns={}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<helpers>','exec'),ns)
parse=ns['_row_length_token_value']
assert parse('100.99') == 100.99
assert parse('100.9') == 100.9
assert parse('100') == 100.0
assert parse('399.021') is None
assert parse('1700') == 1700.0
assert parse('1700.01') is None
assert parse('2401') is None
print('v83 length recovery regression passed')
''',encoding='utf-8')
print('patched',path)
