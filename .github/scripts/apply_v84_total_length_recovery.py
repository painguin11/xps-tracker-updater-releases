from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
src=path.read_text(encoding='utf-8')


def insert_before(anchor,text):
    global src
    if text.strip().splitlines()[0] in src:
        return
    pos=src.index(anchor)
    src=src[:pos]+text+src[pos:]


# 1) Printed totals: use multiple untouched high-resolution views instead of the
# generic 1.8x numeric OCR. The latter can repeatedly turn 6720.58 into 6720.53.
total_helper='''def _direct_printed_total_candidates(cell_img):
    """Read a printed activity total from untouched high-resolution views.

    Totals are validation evidence, not individual row lengths, so they are not
    capped at MAX_ROW_LENGTH. Multiple scales/segmentation modes must observe the
    number; no master value or row arithmetic participates in this OCR.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    found=[]
    for scale in (3.0,4.0):
        enlarged=cv2.resize(gray,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
        variants=(enlarged,cv2.threshold(enlarged,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1])
        for image in variants:
            for psm in (7,6):
                raw=cached_ocr_string(
                    image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.'
                ).strip().replace(',','')
                for token in re.findall(r'\\d+(?:\\.\\d+)?',raw):
                    try:
                        value=float(token)
                        if 0<value<1000000:
                            found.append(value)
                    except Exception:
                        pass
    return found


'''
insert_before('def _printed_total_value_is_plausible',total_helper)
old="        direct=_ocr_digits(cell,True,fast_plain=True)"
new="        direct=_direct_printed_total_candidates(cell)"
if old in src:
    src=src.replace(old,new,1)
elif new not in src:
    raise SystemExit('printed total direct OCR anchor not found')

# 2) Whole-column Pipe cross-check. This is only used during a failed-total audit;
# stable repeated observations may correct subtle per-cell OCR errors.
batch_pipe_helper='''def _batch_pair_length_candidates(img,bands,table,value_box,skip_band_index=None):
    """Cross-check Pipe lengths by OCRing the complete value column as one image.

    Every row keeps its own candidate bucket. A later caller requires repeated
    support before this source may replace a per-cell value, so ambiguous/singleton
    reads simply fall back to the independent per-cell audit.
    """
    if img is None or not bands or not table or not value_box:
        return {}
    left,right=table; h,w=img.shape[:2]; tw=max(1,right-left)
    x1=max(0,int(left+value_box[0]*tw)); x2=min(w,int(left+value_box[1]*tw))
    if x2-x1<8:
        return {}
    heights=[max(1,b-a) for a,b in bands]
    typical=float(np.median(heights)) if heights else 1.0
    tiles=[]; tile_indices=[]
    for band_index,(y1,y2) in enumerate(bands):
        if skip_band_index is not None and band_index==skip_band_index:
            continue
        if (y2-y1)>typical*1.45:
            continue
        cell=img[max(0,y1-2):min(h,y2+2),x1:x2]
        if cell.size==0:
            continue
        gray=cv2.cvtColor(cell,cv2.COLOR_RGB2GRAY)
        enlarged=cv2.resize(gray,None,fx=4.0,fy=4.0,interpolation=cv2.INTER_CUBIC)
        thresholded=cv2.threshold(enlarged,200,255,cv2.THRESH_BINARY)[1]
        thresholded=cv2.copyMakeBorder(thresholded,8,8,20,20,cv2.BORDER_CONSTANT,value=255)
        tiles.append(thresholded); tile_indices.append(band_index)
    if not tiles:
        return {}
    width=max(tile.shape[1] for tile in tiles)
    padded=[]; spans=[]; cursor=0
    for band_index,tile in zip(tile_indices,tiles):
        if tile.shape[1]<width:
            tile=cv2.copyMakeBorder(tile,0,0,0,width-tile.shape[1],cv2.BORDER_CONSTANT,value=255)
        padded.append(tile); spans.append((band_index,cursor,cursor+tile.shape[0])); cursor+=tile.shape[0]
    stack=np.vstack(padded); found={}
    for psm in (6,11):
        try:
            data=pytesseract.image_to_data(
                stack,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.',
                output_type=pytesseract.Output.DICT)
        except Exception:
            continue
        for i,raw in enumerate(data.get('text',[])):
            try:
                yc=float(data['top'][i])+float(data['height'][i])/2.0
            except Exception:
                continue
            band_index=min(spans,key=lambda span:abs(yc-(span[1]+span[2])/2.0))[0]
            for token in re.findall(r'\\d+(?:\\.\\d+)?',str(raw or '').strip().replace(',','')):
                value=_row_length_token_value(token)
                if value is not None:
                    found.setdefault(band_index,[]).append(value)
    return found


'''
insert_before('def _choose_printed_total',batch_pipe_helper)

# 3) A common evidence reader. Pipe all-row audits prefer a repeated whole-column
# observation and fall back to the existing independent per-cell views.
crosscheck_helper='''def _crosscheck_length_evidence(evidence,kind,all_rows=False):
    """Reread one stored row/part without using master or total arithmetic."""
    if kind=='Pipe' and all_rows:
        batch_value,batch_stable=_stable_numeric_vote(evidence.get('_length_batch_candidates',[]),2)
        if batch_stable and batch_value is not None:
            return {'value':batch_value,'confident':True,
                    'candidates':list(evidence.get('_length_batch_candidates',[])),
                    'source':'stable whole-column cross-check'}
    if kind=='Cleaning' and not all_rows:
        cell=evidence.get('_length_value_cell')
        if cell is None:
            cell=evidence.get('_cleaning_value_cell')
        return _conservative_cleaning_reread(cell)
    return _independent_row_length_read(
        evidence.get('_length_value_cell'),evidence.get('_length_expanded_cell'),kind)


'''
insert_before('def _batch_cleaning_length_candidates',crosscheck_helper)

# 4) Persist printed-total evidence on the same prepared layout object that the
# analyze() loop later adds to total_sources; v83 read the total but dropped it.
old='''    printed_total_info=_read_pair_table_printed_total(
        img,bands,table,val_box,up_box,dn_box,date_box)
    total_band_index=printed_total_info.get('band_index')
    batch_cleaning_values=(
        _batch_cleaning_length_candidates(img,bands,table,val_box,total_band_index)
        if kind=='cleaning' else {})
'''
new='''    printed_total_info=_read_pair_table_printed_total(
        img,bands,table,val_box,up_box,dn_box,date_box)
    # analyze() builds work-order total validation from this same prepared layout.
    # Keep the OCR result (including its preview crop) instead of dropping it after
    # the parser returns.
    prepared['printed_total_info']=printed_total_info
    total_band_index=printed_total_info.get('band_index')
    batch_pipe_values=(
        _batch_pair_length_candidates(img,bands,table,val_box,total_band_index)
        if kind=='pipes' else {})
    batch_cleaning_values=(
        _batch_cleaning_length_candidates(img,bands,table,val_box,total_band_index)
        if kind=='cleaning' else {})
'''
if old in src:
    src=src.replace(old,new,1)
elif "prepared['printed_total_info']=printed_total_info" not in src:
    raise SystemExit('pair total persistence anchor not found')

old="        rec['_length_first_candidates']=list(value_candidates or [])\n        if kind=='cleaning':"
new="""        rec['_length_first_candidates']=list(value_candidates or [])
        rec['_length_batch_candidates']=list(
            batch_cleaning_values.get(band_index,[]) if kind=='cleaning'
            else batch_pipe_values.get(band_index,[]))
        if kind=='cleaning':"""
if old in src:
    src=src.replace(old,new,1)
elif "rec['_length_batch_candidates']" not in src:
    raise SystemExit('row batch evidence anchor not found')

# 5) Split/MSA rows must retain each physical PDF cell. A combined master length
# must never be overwritten by OCR from only the first part.
snapshot_helper='''def _length_evidence_snapshot(record):
    """Retain the OCR inputs for one physical PDF length row."""
    return {'video_length':record.get('video_length'),
            '_length_value_cell':record.get('_length_value_cell'),
            '_length_expanded_cell':record.get('_length_expanded_cell'),
            '_length_batch_candidates':list(record.get('_length_batch_candidates',[]))}


'''
insert_before('def combine_split_pipe_records',snapshot_helper)
old="""    parts.append(additional.get('video_length'))
    existing['part_lengths']=parts
    existing['part_count']=len(parts)
"""
new="""    parts.append(additional.get('video_length'))
    evidence=list(existing.get('_split_length_evidence',[]))
    if not evidence:
        evidence=[_length_evidence_snapshot(existing)]
    evidence.append(_length_evidence_snapshot(additional))
    existing['_split_length_evidence']=evidence
    existing['part_lengths']=parts
    existing['part_count']=len(parts)
"""
if old in src:
    src=src.replace(old,new,1)
elif "existing['_split_length_evidence']=evidence" not in src:
    raise SystemExit('split evidence anchor not found')

# 6) Total mismatch recovery: stage-specific attempt flags, safe split-part rereads,
# and stable whole-column Pipe evidence during the all-row audit.
start=src.index('    def _retry_length_total_mismatch(self,check,all_rows=False,force=False):')
end=src.index('    def _retry_cleaning_total_mismatch',start)
method='''    def _retry_length_total_mismatch(self,check,all_rows=False,force=False):
        """Reread suspect rows first; then independently cross-check the activity."""
        indexed=self._total_check_records(check)
        if not indexed: return False
        expected_total=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')
        rows=[record for _,record in indexed]
        if _length_total_result(rows,expected_total).get('matches'): return False
        stage_flag='_length_allrow_attempted' if all_rows else '_length_targeted_attempted'
        suspects=[]
        for index,record in indexed:
            if record.get('_length_user_edited'): continue
            # Targeted and all-row checks use different evidence, so a row touched
            # in stage 1 must still be eligible for stage 2.
            if record.get(stage_flag) and not force: continue
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
            record[stage_flag]=True
            record['_length_crosscheck_attempted']=True  # retained for diagnostics/backward compatibility
            kind=record.get('kind') or check.get('kind')

            split_parts=list(record.get('_split_length_evidence',[]))
            if kind=='Pipe' and int(record.get('part_count') or 0)>1:
                if not split_parts:
                    # Never replace a combined/MSA length with OCR from one part.
                    record['_length_crosscheck_source']='split-pipe evidence unavailable; aggregate preserved'
                    continue
                part_values=[]; part_sources=[]
                for part in split_parts:
                    reread=_crosscheck_length_evidence(part,kind,all_rows)
                    part_sources.append(reread.get('source',''))
                    new_value=reread.get('value') if reread.get('confident') else None
                    old_value=part.get('video_length')
                    chosen=old_value
                    if new_value is not None and _valid_row_length_value(new_value):
                        chosen=float(new_value)
                    part['video_length']=chosen
                    part['_length_crosscheck_source']=reread.get('source')
                    part_values.append(chosen)
                if any(value is None or not _valid_row_length_value(value) for value in part_values):
                    continue
                new_total=sum(float(value) for value in part_values)
                old_total=record.get('video_length')
                record['_length_crosscheck_source']='split parts: '+'; '.join(x for x in part_sources if x)
                if old_total is None or float(old_total)!=float(new_total):
                    record['part_lengths']=list(part_values)
                    record['video_length']=float(new_total)
                    refresh_length_status(record); changed=True
                current_rows=[r for _,r in self._total_check_records(check)]
                if _length_total_result(current_rows,expected_total).get('matches'):
                    break
                continue

            reread=_crosscheck_length_evidence(record,kind,all_rows)
            record['_length_crosscheck_source']=reread.get('source')
            new_value=reread.get('value') if reread.get('confident') else None
            if new_value is None or not _valid_row_length_value(new_value):
                continue
            old_value=record.get('video_length')
            if old_value is not None and float(old_value)==float(new_value):
                continue
            # Cleaning's aligned-column first pass remains conservative. During an
            # all-row audit, a conflicting isolated-cell read is evidence for review,
            # not permission to overwrite an otherwise valid Wheel Walk value.
            if kind=='Cleaning' and all_rows and _valid_row_length_value(old_value):
                record['_length_crosscheck_conflict']=new_value
                continue
            record['video_length']=float(new_value)
            refresh_length_status(record); changed=True
            current_rows=[r for _,r in self._total_check_records(check)]
            if _length_total_result(current_rows,expected_total).get('matches'):
                break
        return changed

'''
src=src[:start]+method+src[end:]

path.write_text(src,encoding='utf-8')
print('patched',path)
