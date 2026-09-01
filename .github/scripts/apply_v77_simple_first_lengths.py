from pathlib import Path

APP = Path('working_source/app/reno_scan_updater.py')
TEST = Path('working_source/tests/regression_v77_simple_first.py')
text = APP.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'{label}: expected source block not found; refusing broad edit')
    text = text.replace(old, new, 1)


def replace_between(start, end, replacement, label):
    global text
    a = text.find(start)
    if a < 0:
        raise SystemExit(f'{label}: start marker not found')
    b = text.find(end, a)
    if b < 0:
        raise SystemExit(f'{label}: end marker not found')
    text = text[:a] + replacement + text[b:]


# New OCR behavior must not reuse v3 cached strings produced by the old pipeline.
replace_once("OCR_CACHE_VERSION = 'v3'", "OCR_CACHE_VERSION = 'v4'", 'OCR cache namespace')


helpers = r'''def _simple_cleaning_length_candidates(cell_img):
    """Primary Wheel Walk OCR: one conservative read of the printed cell.

    Normal processing intentionally starts here and stops here when the printed
    work-order total reconciles.  No morphology, candidate search, master-based
    selection, or arithmetic correction is allowed on the primary path.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    height,width=cell_img.shape[:2]
    # Remove only a tiny amount of the ruled-cell edge.  This keeps the complete
    # digit strokes while preventing the border itself from touching a numeral.
    xpad=max(1,int(round(width*.012)))
    ypad=max(1,int(round(height*.06)))
    sample=cell_img[ypad:height-ypad,xpad:width-xpad] if height>ypad*2+4 and width>xpad*2+4 else cell_img
    gray=cv2.cvtColor(sample,cv2.COLOR_RGB2GRAY)
    gray=cv2.resize(gray,None,fx=3.0,fy=3.0,interpolation=cv2.INTER_CUBIC)
    raw=cached_ocr_string(gray,config='--psm 7 -c tessedit_char_whitelist=0123456789.').strip()
    out=[]
    for value in re.findall(r'\d+(?:\.\d+)?',raw.replace(',','')):
        try:
            numeric=float(value)
            if 0<numeric<5000: out.append(numeric)
        except Exception:
            pass
    return out


def _fallback_cleaning_length_candidates(cell_img):
    """Conservative second-pass OCR used only after total validation fails.

    Multiple small crops/configurations are used so a replacement must be seen
    repeatedly.  This deliberately avoids the wide v76 candidate spray that
    allowed mathematically convenient garbage values to win.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    found=[]; height,width=cell_img.shape[:2]

    def collect(image, psm):
        raw=cached_ocr_string(image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.').strip()
        for value in re.findall(r'\d+(?:\.\d+)?',raw.replace(',','')):
            try:
                numeric=float(value)
                if 0<numeric<5000: found.append(numeric)
            except Exception:
                pass

    # A few conservative edge trims.  Each trim supplies independent support,
    # but all preserve almost the entire printed cell.
    for xratio in (.012,.025,.040):
        xpad=max(1,int(round(width*xratio)))
        ypad=max(1,int(round(height*.06)))
        sample=cell_img[ypad:height-ypad,xpad:width-xpad] if height>ypad*2+4 and width>xpad*2+4 else cell_img
        gray=cv2.cvtColor(sample,cv2.COLOR_RGB2GRAY)
        enlarged=cv2.resize(gray,None,fx=3.0,fy=3.0,interpolation=cv2.INTER_CUBIC)
        collect(enlarged,7)
        collect(enlarged,6)
        otsu=cv2.threshold(enlarged,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
        collect(otsu,7)

    # One controlled rule-removal view is the final fallback for a digit actually
    # touching a printed table line.  Unlike v76, this is not repeated over many
    # thresholds/scales/PSMs.
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    inv=cv2.threshold(gray,210,255,cv2.THRESH_BINARY_INV)[1]
    hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(8,int(width*.45)),1))
    vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(8,int(height*.45))))
    rules=cv2.bitwise_or(cv2.morphologyEx(inv,cv2.MORPH_OPEN,hk),
                         cv2.morphologyEx(inv,cv2.MORPH_OPEN,vk))
    clean=255-cv2.subtract(inv,rules)
    clean=cv2.resize(clean,None,fx=3.0,fy=3.0,interpolation=cv2.INTER_CUBIC)
    collect(clean,7)
    collect(clean,6)
    return found


def _find_cleaning_total_reconciliation(records,target_total,max_changes=3,min_support=3):
    """Safely reconcile only strongly supported OCR alternatives to a PDF total.

    The total is a validator/tie-breaker, never a license to choose arbitrary OCR
    output.  A changed value must have repeated OCR support, the solution must use
    no more than ``max_changes`` rows, and equally good ambiguous solutions fail
    closed instead of silently choosing one.
    """
    try: target_cents=int(round(float(target_total)*100))
    except Exception: return {'matched':False,'changes':[]}
    if target_cents<=0: return {'matched':False,'changes':[]}

    current_cents=[]; adjustable=[]
    for index,record in enumerate(records or []):
        value=record.get('video_length')
        if value is None: return {'matched':False,'changes':[]}
        try: current=int(round(float(value)*100))
        except Exception: return {'matched':False,'changes':[]}
        current_cents.append(current)
        if record.get('_length_user_edited'):
            continue

        votes={}
        evidence=list(record.get('_length_ocr_candidates',[]) or [])
        evidence+=list(record.get('_length_fallback_candidates',[]) or [])
        for raw in evidence:
            try:
                candidate=round(float(raw),2)
                if 0<candidate<5000: votes[candidate]=votes.get(candidate,0)+1
            except Exception:
                pass
        current_value=round(float(value),2)
        if current_value not in votes:
            votes[current_value]=1

        options=[(current_value,votes.get(current_value,1))]
        for candidate,vote_count in votes.items():
            if candidate==current_value: continue
            if vote_count>=int(min_support):
                options.append((candidate,vote_count))
        # Keep only genuinely supported alternatives.  Garbage seen once or twice
        # can never be selected merely because its arithmetic is convenient.
        options=sorted(set(options),key=lambda item:(item[0],-item[1]))
        adjustable.append((index,current,options))

    base_total=sum(current_cents); needed=target_cents-base_total
    if needed==0:
        return {'matched':True,'changes':[]}
    if not adjustable:
        return {'matched':False,'changes':[]}

    # delta -> (score, choices, ambiguous).  Fewest changed rows is the primary
    # criterion; OCR vote penalty and total numeric movement are secondary.
    states={0:((0,0,0),[],False)}
    for index,current,options in adjustable:
        max_vote=max(v for _,v in options)
        next_states={}
        for old_delta,(old_score,old_choices,old_ambiguous) in states.items():
            for candidate,vote_count in options:
                cents=int(round(candidate*100))
                changed=0 if cents==current else 1
                if old_score[0]+changed>int(max_changes):
                    continue
                delta=old_delta+(cents-current)
                score=(old_score[0]+changed,
                       old_score[1]+(0 if not changed else max_vote-vote_count),
                       old_score[2]+(0 if not changed else abs(cents-current)))
                choices=old_choices+[(index,candidate)]
                previous=next_states.get(delta)
                if previous is None or score<previous[0]:
                    next_states[delta]=(score,choices,old_ambiguous)
                elif score==previous[0] and choices!=previous[1]:
                    next_states[delta]=(previous[0],previous[1],True)
        states=next_states
        if not states:
            return {'matched':False,'changes':[]}

    winner=states.get(needed)
    if winner is None or winner[2]:
        return {'matched':False,'changes':[]}
    changes=[]
    for index,candidate in winner[1]:
        old=round(float(records[index].get('video_length')),2)
        if abs(candidate-old)>.001:
            changes.append((index,old,candidate))
    if len(changes)>int(max_changes):
        return {'matched':False,'changes':[]}
    return {'matched':True,'changes':changes}


'''
replace_between('def _aggressive_cleaning_length_candidates(cell_img):\n',
                'def _choose_printed_total(cands):\n',
                helpers,
                'length OCR helpers')


# Replace the eager cleaning consensus.  Cleaning starts with one simple read;
# complicated OCR is now impossible until total validation actually fails.
start = """        value_cell=cut(val_box)\n"""
end = """        date_evidence=date_reads.get(band_index,{'date':None,'strong':False,'candidates':[],'votes':{},'strong_votes':{}})\n"""
new_parser = r'''        value_cell=cut(val_box)
        expected=match.get('expected') if match else None
        if kind=='cleaning':
            # Simple first: trust one clean printed-number read and let the
            # independent PDF total decide whether any fallback work is needed.
            value_candidates=_simple_cleaning_length_candidates(value_cell)
            length_ocr_candidates=list(value_candidates)
            value=value_candidates[0] if value_candidates else None
        else:
            value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
            if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
            length_ocr_candidates=list(value_candidates)
            value=_choose_length(value_candidates,expected)
        if (kind!='cleaning' and value is not None and expected not in (None,0) and
                abs(float(value)-float(expected))>max(100,float(expected)*1.5)):
            # Keep the established pipe-video fallback unchanged.  Cleaning does
            # not escalate here; it waits for independent total validation.
            expanded=_ocr_digits(cut(val_box),True,fast_plain=False)
            if expanded:
                value=_choose_length(list(value_candidates)+list(expanded),expected)
'''
replace_between(start, end, new_parser, 'simple-first cleaning parser')


# Replace v76's broad retry method with conservative fallback OCR and safe
# reconciliation.  Re-running after a user-corrected total overwrites, rather
# than duplicates, fallback evidence so cached OCR calls cannot inflate votes.
method_start = """    def retry_total_length_ocr(self,check,target_total):\n"""
method_end = """    def prompt_total_check(self,check):\n"""
new_method = r'''    def retry_total_length_ocr(self,check,target_total):
        if check.get('kind')!='Cleaning' or target_total is None:
            return {'attempted':False,'matched':False,'changes':[]}
        indexed=self._total_check_records(check); rows=[record for _,record in indexed]
        if not rows:
            return {'attempted':False,'matched':False,'changes':[]}

        def fallback_read(record):
            if record.get('_length_user_edited'): return
            cell=record.get('_length_ocr_cell')
            if cell is None or getattr(cell,'size',0)==0: return
            # Replace prior fallback evidence. Re-running after a corrected total
            # must not multiply identical cached OCR votes.
            record['_length_fallback_candidates']=_fallback_cleaning_length_candidates(cell)
            record['_length_retry_done']=True

        suspicious=[]
        for record in rows:
            try: diff=float(record.get('length_diff') or 0)
            except Exception: diff=0
            if record.get('video_length') is None or diff>LENGTH_DIFF_THRESHOLD:
                suspicious.append(record)
        for record in suspicious:
            fallback_read(record)

        result=_find_cleaning_total_reconciliation(rows,target_total)
        if not result.get('matched'):
            # Only after the suspect-only retry fails do we inspect the remaining
            # cells.  The reconciler still requires repeated OCR support and no
            # more than three automatic row changes.
            for record in rows:
                if record not in suspicious and not record.get('_length_user_edited'):
                    fallback_read(record)
            result=_find_cleaning_total_reconciliation(rows,target_total)

        changed=[]
        if result.get('matched'):
            for row_index,old,new in result.get('changes',[]):
                record=rows[row_index]
                record['video_length']=float(new)
                record['ocr_total_reconciled']=True
                refresh_length_status(record)
                note='OCR LENGTH CORRECTED AFTER TOTAL CHECK'
                if note not in record.setdefault('warnings',[]): record['warnings'].append(note)
                changed.append((old,new))
            for index,_ in indexed: self.show_summary_record(index)
        check['ocr_retry_attempted']=True
        check['ocr_retry_changes']=len(changed)
        return {'attempted':True,'matched':bool(result.get('matched')),'changes':changed}

'''
replace_between(method_start, method_end, new_method, 'safe total retry method')

APP.write_text(text, encoding='utf-8')

TEST.write_text(r'''import ast
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
''',encoding='utf-8')

print('Applied v77 simple-first cleaning-length patch.')
