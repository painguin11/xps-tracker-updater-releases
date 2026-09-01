from pathlib import Path

path = Path('working_source/app/reno_scan_updater.py')
text = path.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'{label}: expected source block not found; refusing broad edit')
    text = text.replace(old, new, 1)


# 1) A saved layout is already user-confirmed.  apply_confirmed_layout() raises it
# to 100%, so do not immediately show the same dialog again.
replace_once(
"""                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                            dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                            if dlg.result is None:
                                self.status.set('Analysis cancelled.'); return
                            confirmed_layouts[fingerprint]=dlg.result
                            apply_confirmed_layout(layout,dlg.result)
                            save_layout_profile(fingerprint,layout,dlg.result)
""",
"""                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                                if dlg.result is None:
                                    self.status.set('Analysis cancelled.'); return
                                confirmed_layouts[fingerprint]=dlg.result
                                apply_confirmed_layout(layout,dlg.result)
                                save_layout_profile(fingerprint,layout,dlg.result)
""",
'saved-layout confirmation gate')


# 2) Add an aggressive, retry-only OCR ensemble and a pure arithmetic reconciler.
marker = """def _choose_printed_total(cands):
"""
if marker not in text:
    raise SystemExit('helper insertion marker not found')
helpers = r'''def _aggressive_cleaning_length_candidates(cell_img):
    """Retry a cleaning length with larger, border-trimmed numeric OCR variants.

    This deliberately runs only after total validation fails.  It produces OCR
    observations only; the verified PDF total may select among those observations
    but may never manufacture a value or pull one from the master workbook.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    found=[]; height,width=cell_img.shape[:2]
    for xratio in (0,.02,.04):
        xpad=max(0,int(round(width*xratio)))
        sample=cell_img[:,xpad:width-xpad] if xpad and width>xpad*2+4 else cell_img
        ypad=max(1,int(round(sample.shape[0]*.05)))
        if sample.shape[0]>ypad*2+4:
            sample=sample[ypad:sample.shape[0]-ypad,:]
        gray=cv2.cvtColor(sample,cv2.COLOR_RGB2GRAY)
        for scale in (2.5,3.5):
            enlarged=cv2.resize(gray,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
            variants=(enlarged,cv2.threshold(enlarged,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1])
            for variant in variants:
                for psm in (7,6,11):
                    raw=cached_ocr_string(
                        variant,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.').strip()
                    for value in re.findall(r'\d+(?:\.\d+)?',raw.replace(',','')):
                        try:
                            numeric=float(value)
                            if 0<numeric<5000: found.append(numeric)
                        except Exception:
                            pass
    # Keep the v75 rule-removal evidence in the retry pool as well.
    for value in _ocr_gridless_number_candidates(cell_img,True):
        try:
            numeric=float(value)
            if 0<numeric<5000: found.append(numeric)
        except Exception:
            pass
    return found


def _find_cleaning_total_reconciliation(records,target_total):
    """Find the least-cost OCR-observed length combination matching a PDF total."""
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
        for raw in record.get('_length_ocr_candidates',[]) or []:
            try:
                candidate=round(float(raw),2)
                if 0<candidate<5000: votes[candidate]=votes.get(candidate,0)+1
            except Exception:
                pass
        current_value=round(float(value),2)
        if current_value not in votes:
            # The current automatic value came from OCR before candidate tracking
            # existed in this row; preserve it as one observed option.
            votes[current_value]=1
        ranked=sorted(votes.items(),key=lambda item:(-item[1],abs(item[0]-current_value),item[0]))[:12]
        adjustable.append((index,current,ranked))

    base_total=sum(current_cents); needed=target_cents-base_total
    if needed==0:
        return {'matched':True,'changes':[]}
    if not adjustable:
        return {'matched':False,'changes':[]}

    # delta -> (vote_penalty, changed_rows, movement_cents, choices)
    states={0:(0,0,0,[])}
    for index,current,ranked in adjustable:
        max_vote=max(v for _,v in ranked)
        next_states={}
        for old_delta,(old_vote_penalty,old_changes,old_move,old_choices) in states.items():
            for candidate,vote_count in ranked:
                cents=int(round(candidate*100)); delta=old_delta+(cents-current)
                score=(old_vote_penalty+(max_vote-vote_count),
                       old_changes+(0 if cents==current else 1),
                       old_move+abs(cents-current))
                previous=next_states.get(delta)
                if previous is None or score<previous[:3]:
                    next_states[delta]=score+(old_choices+[(index,candidate)],)
        # Real tables produce only a modest number of distinct sums.  Keep a
        # bounded safety valve for pathological OCR without sacrificing sums near
        # the required correction.
        if len(next_states)>100000:
            best_keys=sorted(next_states,key=lambda delta:(abs(delta-needed),next_states[delta][:3]))[:50000]
            next_states={delta:next_states[delta] for delta in best_keys}
        states=next_states

    winner=states.get(needed)
    if winner is None:
        return {'matched':False,'changes':[]}
    changes=[]
    for index,candidate in winner[3]:
        old=round(float(records[index].get('video_length')),2)
        if abs(candidate-old)>.001:
            changes.append((index,old,candidate))
    return {'matched':True,'changes':changes}


'''
text = text.replace(marker, helpers + marker, 1)


# 3) Retain each cleaning cell plus all OCR observations so a failed total can
# trigger a real second OCR pass after all rows are known.
replace_once(
"""        if kind=='cleaning':
            value=_choose_cleaning_length(value_candidates,expected)
            distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}
            needs_consensus=(not value_candidates or value is None or len(distinct)>1 or
                (value is not None and expected not in (None,0) and
                 abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))
            if needs_consensus:
                # Re-read inside several small horizontal margins.  This removes
                # the vertical grid rules that caused 2 -> 7 and 224 -> 22 while
                # retaining the full digit string.  New crop pixels also avoid
                # reusing a stale OCR-cache result from the border-touching crop.
                consensus=list(value_candidates)
                width=value_cell.shape[1]
                for ratio in (.015,.030,.045,.060):
                    pad=max(2,int(round(width*ratio)))
                    if width>pad*2+4:
                        consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                # If a digit touches or is distorted by a table rule, horizontal
                # trimming alone can repeatedly agree on the same wrong value
                # (for example 275 -> 75 or 224 -> 274).  Remove grid rules and
                # add those OCR observations to the same printed-value vote.
                consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                value=_choose_cleaning_length(consensus,expected)
        else:
            value=_choose_length(value_candidates,expected)
""",
"""        length_ocr_candidates=list(value_candidates)
        if kind=='cleaning':
            value=_choose_cleaning_length(value_candidates,expected)
            distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}
            needs_consensus=(not value_candidates or value is None or len(distinct)>1 or
                (value is not None and expected not in (None,0) and
                 abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))
            if needs_consensus:
                # Re-read inside several small horizontal margins.  This removes
                # the vertical grid rules that caused 2 -> 7 and 224 -> 22 while
                # retaining the full digit string.  New crop pixels also avoid
                # reusing a stale OCR-cache result from the border-touching crop.
                consensus=list(value_candidates)
                width=value_cell.shape[1]
                for ratio in (.015,.030,.045,.060):
                    pad=max(2,int(round(width*ratio)))
                    if width>pad*2+4:
                        consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                # If a digit touches or is distorted by a table rule, horizontal
                # trimming alone can repeatedly agree on the same wrong value
                # (for example 275 -> 75 or 224 -> 274).  Remove grid rules and
                # add those OCR observations to the same printed-value vote.
                consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                length_ocr_candidates=consensus
                value=_choose_cleaning_length(consensus,expected)
        else:
            value=_choose_length(value_candidates,expected)
""",
'cleaning OCR candidate retention')

replace_once(
"""        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe','asset':asset,
             'up':up,'down':down,'video_length':value,'row_date':d,'status':status}
        if not match: rec['skip_update']=True
""",
"""        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe','asset':asset,
             'up':up,'down':down,'video_length':value,'row_date':d,'status':status}
        if kind=='cleaning':
            rec['_length_ocr_candidates']=list(length_ocr_candidates)
            rec['_length_ocr_cell']=value_cell.copy()
        if not match: rec['skip_update']=True
""",
'cleaning OCR retry state')


# 4) Add the application-level retry.  First re-OCR suspicious rows, attempt an
# exact OCR-only reconciliation, then widen the retry to remaining rows if needed.
method_marker = """    def prompt_total_check(self,check):
"""
if method_marker not in text:
    raise SystemExit('prompt_total_check marker not found')
method = r'''    def retry_total_length_ocr(self,check,target_total):
        if check.get('kind')!='Cleaning' or target_total is None:
            return {'attempted':False,'matched':False,'changes':[]}
        indexed=self._total_check_records(check); rows=[record for _,record in indexed]
        if not rows:
            return {'attempted':False,'matched':False,'changes':[]}

        def add_retry_candidates(record):
            if record.get('_length_user_edited'): return
            cell=record.get('_length_ocr_cell')
            if cell is None or getattr(cell,'size',0)==0: return
            extra=_aggressive_cleaning_length_candidates(cell)
            if extra:
                record.setdefault('_length_ocr_candidates',[]).extend(extra)
                record['_length_retry_done']=True

        suspicious=[]
        for record in rows:
            try: diff=float(record.get('length_diff') or 0)
            except Exception: diff=0
            distinct=set()
            for raw in record.get('_length_ocr_candidates',[]) or []:
                try:
                    value=round(float(raw),2)
                    if 0<value<5000: distinct.add(value)
                except Exception: pass
            if record.get('video_length') is None or diff>LENGTH_DIFF_THRESHOLD or len(distinct)>1:
                suspicious.append(record)
        for record in suspicious: add_retry_candidates(record)

        result=_find_cleaning_total_reconciliation(rows,target_total)
        if not result.get('matched'):
            for record in rows:
                if not record.get('_length_retry_done') and not record.get('_length_user_edited'):
                    add_retry_candidates(record)
            result=_find_cleaning_total_reconciliation(rows,target_total)

        changed=[]
        if result.get('matched'):
            for row_index,old,new in result.get('changes',[]):
                record=rows[row_index]
                record['video_length']=float(new)
                record['ocr_total_reconciled']=True
                refresh_length_status(record)
                note='OCR LENGTH RESELECTED USING VERIFIED PDF TOTAL'
                if note not in record.setdefault('warnings',[]): record['warnings'].append(note)
                changed.append((old,new))
            for index,_ in indexed: self.show_summary_record(index)
        check['ocr_retry_attempted']=True
        check['ocr_retry_changes']=len(changed)
        return {'attempted':True,'matched':bool(result.get('matched')),'changes':changed}

'''
text = text.replace(method_marker, method + method_marker, 1)


# 5) A confidently OCRed printed total gets one automatic retry before the user is
# interrupted.  If the user edits the total, rerun the same process against the
# corrected target before declaring the mismatch unresolved.
replace_once(
"""            self.total_validations.append(check)
            self.refresh_total_check(check)
            if not check.get('passed'): self.prompt_total_check(check)
""",
"""            self.total_validations.append(check)
            self.refresh_total_check(check)
            if (not check.get('passed') and check.get('pdf_total_confident') and
                    check.get('pdf_total') is not None):
                self.retry_total_length_ocr(check,check.get('pdf_total'))
                self.refresh_total_check(check)
            if not check.get('passed'): self.prompt_total_check(check)
""",
'automatic total-driven OCR retry')

replace_once(
"""            check['verified_total']=verified; check['manual_verified']=True
            passed=self.refresh_total_check(check)
            if passed:
                messagebox.showinfo('Total Length Verified',
                    f\"Work Order {check.get('wo','')} {check.get('kind','')} now reconciles exactly at {verified:g} ft.\",parent=self)
""",
"""            check['verified_total']=verified; check['manual_verified']=True
            retry=self.retry_total_length_ocr(check,verified)
            passed=self.refresh_total_check(check)
            if passed:
                retry_note=(f\" OCR retry corrected {len(retry.get('changes',[]))} row length(s) using only values read from the PDF.\"
                            if retry.get('changes') else '')
                messagebox.showinfo('Total Length Verified',
                    f\"Work Order {check.get('wo','')} {check.get('kind','')} now reconciles exactly at {verified:g} ft.\"+retry_note,parent=self)
""",
'user-corrected total OCR retry')


# 6) Manual row edits are authoritative and must not be silently changed later by
# total-driven OCR reconciliation.
replace_once(
"""                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())
                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()
""",
"""                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())
                if r.get('kind') in ('Pipe','Cleaning'): r['_length_user_edited']=True
                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()
""",
'manual length protection')

path.write_text(text,encoding='utf-8')
print('Applied v76 saved-layout + total-driven OCR retry patch.')
