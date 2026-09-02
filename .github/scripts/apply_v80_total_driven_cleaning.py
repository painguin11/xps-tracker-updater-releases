from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')


def replace_once(text,old,new,label):
    if old not in text:
        raise SystemExit(f'{label}: expected source block not found; refusing broad edit')
    return text.replace(old,new,1)


text=APP.read_text(encoding='utf-8')

# The Wheel Walk values are right aligned and can overlap the thick/skewed right
# grid rule by a couple of pixels. Keep a tiny amount of the neighboring blank
# margin instead of erasing the right edge of the numeric cell.
old="""    x1=max(0,int(left+value_box[0]*tw)); x2=min(w,int(left+value_box[1]*tw))
    if x2-x1<8:
        return {}
"""
new="""    x1=max(0,int(left+value_box[0]*tw)); x2=min(w,int(left+value_box[1]*tw))
    if x2-x1<8:
        return {}
    # Scanned B&C tables can put the final printed digit partly across the thick
    # right grid stroke. A ~2% bleed is enough to retain that digit while staying
    # well inside the neighboring date cell's text margin.
    right_bleed=max(2,int(round((x2-x1)*.02)))
    x2=min(w,x2+right_bleed)
"""
text=replace_once(text,old,new,'batch right bleed')
old="""        # Keep the right-aligned final digit intact. Erase only the final ~1.5%
        # containing the vertical grid stroke instead of cropping the right side.
        edge=max(1,int(round(sample.shape[1]*.015)))
        sample[:,-edge:]=255
"""
new="""        # Do not blank the right edge. On slightly skewed scans that stroke can
        # pass through the final digit itself (for example 366 -> 36). The small
        # crop bleed above preserves the complete printed glyph instead.
"""
text=replace_once(text,old,new,'remove destructive batch edge erase')

# Give only cleaning numeric cells the same tiny right bleed. Endpoint/date crops
# keep their existing exact geometry.
old="""        def cut(box): return img[y1:y2,max(0,int(left+box[0]*tw)):min(w,int(left+box[1]*tw))]
"""
new="""        def cut(box,right_bleed=False):
            x1=max(0,int(left+box[0]*tw)); x2=min(w,int(left+box[1]*tw))
            if right_bleed and x2>x1:
                x2=min(w,x2+max(2,int(round((x2-x1)*.02))))
            return img[y1:y2,x1:x2]
"""
text=replace_once(text,old,new,'row crop helper')
text=replace_once(text,"        value_cell=cut(val_box)\n","        value_cell=cut(val_box,right_bleed=(kind=='cleaning'))\n",'cleaning value bleed')

# First pass means first pass: if the aligned column reader produced a value, use
# it untouched. Only missing/ambiguous first reads can escalate during extraction.
# Master-length disagreement no longer triggers extra OCR before total validation.
old="""        if kind=='cleaning':
            value_candidates=list(batch_cleaning_values.get(band_index,[]))
            if value_candidates:
                value=_choose_cleaning_length(value_candidates,expected)
                batch_suspect=(value is None or (expected not in (None,0) and
                    abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))
                if batch_suspect:
                    # The batch column reader is normally the cleanest source, but
                    # a dropped digit can produce a single plausible-looking value.
                    # Verify only that suspicious cell; do not use the total to
                    # manufacture a replacement and do not rewrite unrelated rows.
                    cell_candidates=_ocr_digits(value_cell,True,fast_plain=True)
                    if not cell_candidates:
                        cell_candidates=_ocr_digits(value_cell,True,fast_plain=False)
                    consensus=list(value_candidates)+list(cell_candidates)
                    cell_distinct={round(float(x),2) for x in cell_candidates if 0<float(x)<5000}
                    if not cell_candidates or len(cell_distinct)>1:
                        consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                    if consensus:
                        value_candidates=consensus
                        value=_choose_cleaning_length(consensus,expected)
            else:
                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
                value=_choose_cleaning_length(value_candidates,expected)
                distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}
                needs_consensus=(not value_candidates or value is None or len(distinct)>1 or
                    (value is not None and expected not in (None,0) and
                     abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))
                if needs_consensus:
                    consensus=list(value_candidates)
                    width=value_cell.shape[1]
                    for ratio in (.015,.030,.045,.060):
                        pad=max(2,int(round(width*ratio)))
                        if width>pad*2+4:
                            consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                    consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                    value=_choose_cleaning_length(consensus,expected)
"""
new="""        if kind=='cleaning':
            value_candidates=list(batch_cleaning_values.get(band_index,[]))
            if value_candidates:
                # Clean aligned-column OCR is authoritative for the first pass.
                # Do not re-read a row merely because it differs from the master.
                value=_choose_cleaning_length(value_candidates,None)
            else:
                # Missing batch OCR may fall back immediately because there is no
                # usable first-pass value. Extra transforms are allowed only when
                # the direct cell read is missing or internally ambiguous.
                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
                value=_choose_cleaning_length(value_candidates,None)
                distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}
                needs_consensus=(not value_candidates or value is None or len(distinct)>1)
                if needs_consensus:
                    consensus=list(value_candidates)
                    consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                    if consensus:
                        value_candidates=consensus
                        value=_choose_cleaning_length(consensus,None)
"""
text=replace_once(text,old,new,'simple-first cleaning branch')

# Retain the original cell image/candidates only in memory so a failed work-order
# total can target suspect rows without rerendering or touching unrelated rows.
old="""        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe','asset':asset,
             'up':up,'down':down,'video_length':value,'row_date':d,'status':status}
        if not match: rec['skip_update']=True
"""
new="""        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe','asset':asset,
             'up':up,'down':down,'video_length':value,'row_date':d,'status':status}
        if kind=='cleaning':
            rec['_cleaning_value_cell']=value_cell.copy() if getattr(value_cell,'size',0) else None
            rec['_cleaning_first_candidates']=list(value_candidates or [])
        if not match: rec['skip_update']=True
"""
text=replace_once(text,old,new,'store cleaning reread evidence')

# Pure helpers for a conservative targeted reread. The master can tell us which
# rows deserve another look, but it cannot supply a value and the PDF total never
# chooses among OCR candidates.
marker="""def _batch_cleaning_length_candidates(img,bands,table,value_box,skip_band_index=None):
"""
insert="""def _stable_numeric_vote(cands,min_votes=2):
    rounded=[round(float(x),2) for x in (cands or []) if 0<float(x)<5000]
    if not rounded: return None,False
    counts={value:rounded.count(value) for value in set(rounded)}
    most=max(counts.values()); winners=[value for value,count in counts.items() if count==most]
    if len(winners)!=1 or most<int(min_votes): return None,False
    return winners[0],True


def _conservative_cleaning_reread(cell_img):
    \"\"\"Reread one suspect cleaning cell without master/total arithmetic.\"\"\"
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return {'value':None,'confident':False,'source':'no cell','candidates':[]}
    direct=_ocr_digits(cell_img,True,fast_plain=True)
    value,confident=_stable_numeric_vote(direct,2)
    if confident:
        return {'value':value,'confident':True,'source':'direct cell','candidates':direct}
    gridless=_ocr_gridless_number_candidates(cell_img,True)
    value,confident=_stable_numeric_vote(gridless,3)
    if confident:
        return {'value':value,'confident':True,'source':'gridless cell','candidates':gridless}
    return {'value':None,'confident':False,'source':'unresolved','candidates':list(direct)+list(gridless)}


"""+marker
text=replace_once(text,marker,insert,'targeted reread helpers')

# Add work-order-level targeted retry just before total comparison. Only rows with
# their own master-length discrepancy (or a missing value) are re-read, and only
# a stable OCR result can replace the first-pass value.
marker="""    def refresh_total_check(self,check,redraw=True):
"""
insert="""    def _retry_cleaning_total_mismatch(self,check,force=False):
        if check.get('kind')!='Cleaning': return False
        indexed=self._total_check_records(check)
        if not indexed: return False
        expected_total=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')
        rows=[record for _,record in indexed]
        if _length_total_result(rows,expected_total).get('matches'): return False
        suspects=[]
        for index,record in indexed:
            if record.get('_length_user_edited'): continue
            if record.get('_cleaning_reread_attempted') and not force: continue
            cell=record.get('_cleaning_value_cell')
            if cell is None or getattr(cell,'size',0)==0: continue
            current=record.get('video_length'); master=record.get('master_length')
            if current is None:
                score=float('inf')
            elif master not in (None,0):
                score=abs(float(current)-float(master))
                if score<=LENGTH_DIFF_THRESHOLD: continue
            else:
                continue
            suspects.append((score,index,record))
        suspects.sort(key=lambda item:item[0],reverse=True)
        changed=False
        for _score,index,record in suspects[:6]:
            record['_cleaning_reread_attempted']=True
            reread=_conservative_cleaning_reread(record.get('_cleaning_value_cell'))
            record['_cleaning_reread_source']=reread.get('source')
            if not reread.get('confident') or reread.get('value') is None:
                continue
            new_value=float(reread['value']); old_value=record.get('video_length')
            if old_value is not None and abs(float(old_value)-new_value)<=.01:
                continue
            record['video_length']=new_value
            refresh_length_status(record)
            changed=True
            current_rows=[r for _,r in self._total_check_records(check)]
            if _length_total_result(current_rows,expected_total).get('matches'):
                break
        return changed

"""+marker
text=replace_once(text,marker,insert,'targeted work-order retry')

old="""            self.total_validations.append(check)
            self.refresh_total_check(check)
            if not check.get('passed'): self.prompt_total_check(check)
"""
new="""            self.total_validations.append(check)
            self.refresh_total_check(check)
            if not check.get('passed') and kind=='Cleaning':
                if self._retry_cleaning_total_mismatch(check):
                    self.refresh_total_check(check)
            if not check.get('passed'): self.prompt_total_check(check)
"""
text=replace_once(text,old,new,'retry only after total mismatch')

old="""            check['verified_total']=verified; check['manual_verified']=True
            passed=self.refresh_total_check(check)
"""
new="""            check['verified_total']=verified; check['manual_verified']=True
            # A corrected total is a new validation target. Give the same suspect
            # cells one conservative reread before asking the user to edit rows.
            if check.get('kind')=='Cleaning':
                self._retry_cleaning_total_mismatch(check,force=True)
            passed=self.refresh_total_check(check)
"""
text=replace_once(text,old,new,'manual total retry')

# Manual row edits are authoritative; later automatic total retries must not
# silently overwrite them.
old="""                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())
                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()
"""
new="""                old_length=r.get('video_length')
                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())
                if r.get('kind')=='Cleaning' and old_length!=r.get('video_length'):
                    r['_length_user_edited']=True
                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()
"""
text=replace_once(text,old,new,'manual cleaning edit authority')

APP.write_text(text,encoding='utf-8')
print('Applied v80 total-driven cleaning OCR refactor.')
