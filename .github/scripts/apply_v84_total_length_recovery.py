from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
src=path.read_text(encoding='utf-8')


def insert_before(anchor,text):
    global src
    marker=text.strip().splitlines()[0]
    if marker in src:
        return
    pos=src.index(anchor)
    src=src[:pos]+text+src[pos:]


# 1) Printed totals use an untouched high-resolution read. The old generic 1.8x
# reader repeatedly read the actual 6720.58 total on 8-26-2026 as 6720.53.
total_helper=r'''def _high_res_printed_total_candidates(cell_img):
    """Read printed activity totals at 4x without row-length limits or rounding."""
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    enlarged=cv2.resize(gray,None,fx=4.0,fy=4.0,interpolation=cv2.INTER_CUBIC)
    variants=(enlarged,cv2.threshold(enlarged,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1])
    found=[]
    for image in variants:
        for psm in (7,6):
            raw=cached_ocr_string(
                image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.'
            ).strip().replace(',','')
            # A total may exceed 1700, but PDF measurements still never use more
            # than two decimal places. Reject a longer decimal instead of truncating it.
            for token in re.findall(r'(?<![\d.])\d+(?:\.\d{1,2})?(?![\d.])',raw):
                try:
                    value=float(token)
                except Exception:
                    continue
                if 0<value<1000000:
                    found.append(value)
    return found


'''
insert_before('def _printed_total_value_is_plausible',total_helper)
old="        direct=_ocr_digits(cell,True,fast_plain=True)"
new="        direct=_high_res_printed_total_candidates(cell)"
if old in src:
    src=src.replace(old,new,1)
elif new not in src:
    raise SystemExit('printed total high-resolution anchor not found')


# 2) Independent row rereads use evidence strength, not one preferred transform.
# Master length may break a remaining tie only between values OCR actually observed.
start=src.index('def _independent_row_length_read(')
end=src.index('def _conservative_cleaning_reread',start)
independent=r'''def _select_independent_length_candidate(gray_values,threshold_values,kind='Pipe',expected=None):
    """Select only among OCR-observed values; never round or manufacture a length."""
    gray=[float(v) for v in (gray_values or []) if _valid_row_length_value(v)]
    threshold=[float(v) for v in (threshold_values or []) if _valid_row_length_value(v)]
    values=gray+threshold
    if not values:
        return None,False,'no valid OCR values'
    counts={value:values.count(value) for value in set(values)}
    # A reread must have at least two independent observations of the same value.
    eligible={value:count for value,count in counts.items() if count>=2}
    if not eligible:
        return None,False,'independent views disagree'
    strongest=max(eligible.values())
    winners=[value for value,count in eligible.items() if count==strongest]
    if len(winners)==1:
        return winners[0],True,'strongest independent support'
    if kind=='Pipe':
        # On this B&C scan grayscale can preserve a damaged grid-connected glyph
        # while the 4x threshold view resolves it (242.15 -> 242.16, 260.3 -> 360.3).
        threshold_counts={value:threshold.count(value) for value in winners}
        best_threshold=max(threshold_counts.values()) if threshold_counts else 0
        threshold_winners=[value for value,count in threshold_counts.items()
                           if count==best_threshold and count>=2]
        if len(threshold_winners)==1:
            return threshold_winners[0],True,'threshold-supported tie break'
    if expected not in (None,0):
        # The master may only choose between equally supported OCR observations.
        distances={value:abs(value-float(expected)) for value in winners}
        nearest=min(distances.values())
        nearest_values=[value for value,distance in distances.items() if distance==nearest]
        if len(nearest_values)==1:
            return nearest_values[0],True,'master tie break between OCR values'
    return None,False,'independent views remain tied'


def _independent_row_length_read(cell_img,expanded_img=None,kind='Pipe',expected=None):
    """Cross-check a row from independent OCR views without inventing a value."""
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
                raw=cached_ocr_string(
                    image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789.'
                ).strip().replace(',','')
                for token in re.findall(r'\d+(?:\.\d+)?',raw):
                    value=_row_length_token_value(token)
                    if value is not None:
                        bucket.append(value)
    value,confident,source=_select_independent_length_candidate(
        gray_values,threshold_values,kind,expected)
    return {'value':value if confident else None,'confident':confident,
            'candidates':gray_values+threshold_values,'source':source}


'''
src=src[:start]+independent+src[end:]


# 3) Three pixels of vertical breathing room proved sufficient on the real page-4
# cells without changing the detected row itself.
src=src.replace(
    "expanded_value_cell=cut(val_box,vertical_bleed=2)",
    "expanded_value_cell=cut(val_box,vertical_bleed=3)"
)


# 4) Keep the OCR evidence for every physical part of a split/MSA pipe.
snapshot_helper=r'''def _length_part_snapshot(record):
    """Retain one physical PDF row so split-pipe rereads stay part-by-part."""
    return {'value':record.get('video_length'),
            'cell':record.get('_length_value_cell'),
            'expanded':record.get('_length_expanded_cell')}


def _independent_split_pipe_read(record):
    """Reread every physical split-pipe part, then recombine exact observed values."""
    parts=list(record.get('_length_part_reads',[]))
    if not parts:
        return {'value':None,'confident':False,'part_values':[],
                'source':'split-pipe OCR evidence unavailable'}
    values=[]; sources=[]
    for part in parts:
        reread=_independent_row_length_read(
            part.get('cell'),part.get('expanded'),'Pipe',None)
        new_value=reread.get('value') if reread.get('confident') else None
        # If a new independent read cannot resolve the part, preserve the original
        # OCR-observed part rather than dropping or replacing the combined survey.
        chosen=new_value if new_value is not None else part.get('value')
        if chosen is None or not _valid_row_length_value(chosen):
            return {'value':None,'confident':False,'part_values':values,
                    'source':'split-pipe part unresolved'}
        part['value']=float(chosen)
        values.append(float(chosen)); sources.append(reread.get('source',''))
    total=sum((Decimal(str(value)) for value in values),Decimal('0'))
    return {'value':float(total),'confident':True,'part_values':values,
            'source':'split parts: '+'; '.join(source for source in sources if source)}


'''
insert_before('def combine_split_pipe_records',snapshot_helper)
old='''    parts.append(additional.get('video_length'))
    existing['part_lengths']=parts
    existing['part_count']=len(parts)
'''
new='''    parts.append(additional.get('video_length'))
    part_reads=list(existing.get('_length_part_reads',[]))
    if not part_reads:
        part_reads=[_length_part_snapshot(existing)]
    part_reads.append(_length_part_snapshot(additional))
    existing['_length_part_reads']=part_reads
    existing['part_lengths']=parts
    existing['part_count']=len(parts)
'''
if old in src:
    src=src.replace(old,new,1)
elif "existing['_length_part_reads']=part_reads" not in src:
    raise SystemExit('split-pipe part evidence anchor not found')


# 5) Total mismatch recovery: first suspect rows by master difference, then every
# row. Split pipes are always reread as their physical parts and recombined.
start=src.index('    def _retry_length_total_mismatch(self,check,all_rows=False,force=False):')
end=src.index('    def _retry_cleaning_total_mismatch',start)
retry=r'''    def _retry_length_total_mismatch(self,check,all_rows=False,force=False):
        """Reread suspect rows first; if unresolved cross-check the whole activity."""
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
                priority=float('inf') if invalid_current else (
                    abs(float(current)-float(master)) if master not in (None,0) else 0.0)
                suspects.append((priority,index,record))
        suspects.sort(key=lambda item:item[0],reverse=True)
        changed=False
        for _priority,index,record in suspects:
            record['_length_crosscheck_attempted']=True
            kind=record.get('kind') or check.get('kind')
            if kind=='Pipe' and int(record.get('part_count') or 0)>1:
                reread=_independent_split_pipe_read(record)
            elif kind=='Cleaning' and not all_rows:
                cell=record.get('_length_value_cell')
                if cell is None:
                    cell=record.get('_cleaning_value_cell')
                reread=_conservative_cleaning_reread(cell)
            else:
                reread=_independent_row_length_read(
                    record.get('_length_value_cell'),record.get('_length_expanded_cell'),
                    kind,record.get('master_length'))
            record['_length_crosscheck_source']=reread.get('source')
            new_value=reread.get('value') if reread.get('confident') else None
            if new_value is None or not _valid_row_length_value(new_value):
                continue
            old_value=record.get('video_length')
            if old_value is not None and float(old_value)==float(new_value):
                continue
            # Cleaning's aligned-column first pass is intentionally conservative.
            # During the all-row audit, conflicting isolated OCR remains review
            # evidence rather than silently replacing a valid batch-column value.
            if kind=='Cleaning' and all_rows and _valid_row_length_value(old_value):
                record['_length_crosscheck_conflict']=new_value
                continue
            if kind=='Pipe' and int(record.get('part_count') or 0)>1:
                part_values=reread.get('part_values') or []
                if part_values:
                    record['part_lengths']=list(part_values)
            record['video_length']=float(new_value)
            refresh_length_status(record); changed=True
            current_rows=[r for _,r in self._total_check_records(check)]
            if _length_total_result(current_rows,expected_total).get('matches'):
                break
        return changed

'''
src=src[:start]+retry+src[end:]


# 6) The second stage must truly inspect every row, including rows already touched
# in the master-difference stage.
old="                if self._retry_length_total_mismatch(check,all_rows=True):"
new="                if self._retry_length_total_mismatch(check,all_rows=True,force=True):"
if old in src:
    src=src.replace(old,new,1)
elif new not in src:
    raise SystemExit('all-row forced audit anchor not found')

if "prepared['printed_total_info']=printed_total_info" not in src:
    raise SystemExit('printed total is not persisted to layout')

path.write_text(src,encoding='utf-8')
print('patched',path)
