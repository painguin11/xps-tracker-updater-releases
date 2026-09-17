from pathlib import Path
import shutil

SOURCE=Path('working_source/app/reno_scan_updater.py')
text=SOURCE.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global text
    count=text.count(old)
    assert count==1,f'{label}: expected one anchor, found {count}'
    text=text.replace(old,new,1)

# Pair-table rows: once the printed header identifies where data begins, every
# physical grid band after it is reviewable data unless a printed total band was
# positively identified. Matching controls automatic update, never row existence.
old='''    mandatory_data_bands=set()
    if (header_band_index is not None and total_band_index is not None and
            int(total_band_index)>int(header_band_index)):
        # Once both structural anchors are known, every physical grid band between
        # the printed header and total is a real table row. OCR failure may make the
        # row review-only, but it must never make the row disappear from the summary
        # or from total-length arithmetic.
        mandatory_data_bands=set(range(int(header_band_index)+1,int(total_band_index)))
'''
new='''    mandatory_data_bands=set()
    if header_band_index is not None:
        # The confirmed printed header is enough to establish the start of the
        # physical data table. A printed total, when positively identified, still
        # terminates it. Matching/OCR success is never allowed to decide whether an
        # otherwise-confirmed physical Pipe/Cleaning row exists in Live Summary.
        start_band=int(header_band_index)+1
        stop_band=(int(total_band_index)
                   if total_band_index is not None and int(total_band_index)>int(header_band_index)
                   else len(bands))
        mandatory_data_bands=set(range(start_band,stop_band))
'''
replace_once(old,new,'pair mandatory physical rows')

# Manhole column detection now carries the physical header-band index so the row
# parser can distinguish structural header/title bands from data without using
# successful asset matching as a row-existence filter.
replace_once(
    "    fallback={'asset':(0.0,.27),'date':(.74,1.0),'source':'legacy'}\n",
    "    fallback={'asset':(0.0,.27),'date':(.74,1.0),'source':'legacy','header_band_index':None}\n",
    'manhole fallback header index')
replace_once(
    "    for y1,y2 in list(bands)[:4]:\n",
    "    for header_band_index,(y1,y2) in enumerate(list(bands)[:4]):\n",
    'manhole header enumeration')
replace_once(
    "        return {'asset':asset_box,'date':date_box,'source':'header'}\n",
    "        return {'asset':asset_box,'date':date_box,'source':'header','header_band_index':header_band_index}\n",
    'manhole header return')

# Scope the remaining replacements to the normal B&C Manhole parser.
start=text.index('def parse_year15_manholes(')
end=text.index('\ndef _retry_year15_manhole_rows(',start)
func=text[start:end]

def freplace(old,new,label):
    global func
    count=func.count(old)
    assert count==1,f'{label}: expected one parser anchor, found {count}'
    func=func.replace(old,new,1)

# Positioned OCR duplicates are separate physical observations. Keep both and
# mark the repeated identity review-only instead of deleting the later row.
freplace(
    "            if unique_key in seen: continue\n",
    "            duplicate_identity=unique_key in seen\n",
    'token duplicate discard')
freplace(
'''            if item is None: rec['skip_update']=True
            seen.add(unique_key); token_out.append(rec)
''',
'''            if item is None: rec['skip_update']=True
            if duplicate_identity:
                rec.setdefault('validation_warnings',[]).append('DUPLICATE IN PDF')
                rec['skip_update']=True
            rec['_physical_row_center']=int(yc)
            seen.add(unique_key); token_out.append(rec)
''',
    'token duplicate retention')

freplace(
'''        column_boxes=_year15_manhole_column_boxes(img,bands,table)
        asset_box=column_boxes['asset']; date_box=column_boxes['date']
''',
'''        column_boxes=_year15_manhole_column_boxes(img,bands,table)
        asset_box=column_boxes['asset']; date_box=column_boxes['date']
        header_band_index=column_boxes.get('header_band_index')
''',
    'grid header index')
freplace(
    "        for y1,y2 in bands:\n            if on_progress: on_progress()\n",
    "        for band_index,(y1,y2) in enumerate(bands):\n            if header_band_index is not None and band_index<=int(header_band_index):\n                continue\n            if on_progress: on_progress()\n",
    'grid band enumeration')

old_block='''            digit_item=None
            if not observations:
                # A physical Manhole row must not disappear merely because grid
                # contact damages DN-/R2- while its printed numeric body remains
                # independently readable. Recover only an exact numeric body that
                # uniquely identifies one existing master Manhole.
                digit_item=_unique_manhole_digit_match(id_img,master_index)
                if digit_item:
                    observations=[digit_item.get('asset') or '']
            if not observations: continue
            # A real one-letter NEW MANHOLE may be read both with and without its
            # final suffix across OCR variants. Exact-first matching would otherwise
            # collapse that mixed evidence back to the existing base manhole. Require
            # the suffix to survive independent physical-cell crops before it can
            # override an observed base ID.
            confirmed_suffixes=list(dict.fromkeys(_confirmed_suffix_asset_candidates(
                id_img,known,asset_format=asset_format)))
            if len(confirmed_suffixes)==1:
                item=None; status='NEW MANHOLE'; sid=confirmed_suffixes[0]
            elif digit_item is not None:
                item=digit_item; status='Matched'; sid=item['asset']
            else:
                item,status=_resolve_full_asset(observations,known)
                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))
            date_img=img[y1:y2,date_left:date_right]
            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',
                 'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}
'''
new_block='''            date_img=img[y1:y2,date_left:date_right]
            row_date=_parse_sheet_date(date_img)
            numeric_hints=[]
            if not observations:
                # Keep numeric-only OCR as a visible edit hint. It is PDF evidence
                # that a row exists, but it is NOT permission to borrow a missing
                # prefix/identity from the master and silently declare a match.
                for raw in _ocr_digits(id_img,False,fast_plain=True):
                    token=re.sub(r'\\D','',str(raw or ''))
                    if token and token not in numeric_hints:
                        numeric_hints.append(token)
            physical_data_band=(header_band_index is not None and band_index>int(header_band_index))
            if not observations and not numeric_hints and row_date is None and not physical_data_band:
                continue
            # A real one-letter NEW MANHOLE may be read both with and without its
            # final suffix across OCR variants. Exact-first matching would otherwise
            # collapse that mixed evidence back to the existing base manhole. Require
            # the suffix to survive independent physical-cell crops before it can
            # override an observed base ID.
            confirmed_suffixes=list(dict.fromkeys(_confirmed_suffix_asset_candidates(
                id_img,known,asset_format=asset_format)))
            if len(confirmed_suffixes)==1:
                item=None; status='NEW MANHOLE'; sid=confirmed_suffixes[0]
            else:
                item,status=(_resolve_full_asset(observations,known)
                             if observations else (None,'NOT MATCHED'))
                if item:
                    sid=item['asset']
                elif observations:
                    sid=_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0])
                elif numeric_hints:
                    sid=numeric_hints[0]
                else:
                    sid='?'
            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',
                 'video_length':None,'row_date':row_date,'status':status}
'''
freplace(old_block,new_block,'manhole unmatched physical row retention')

freplace(
'''            if item is None: rec['skip_update']=True
            if rec['asset'] in seen: continue
            seen.add(rec['asset']); grid_out.append(rec)
''',
'''            if item is None: rec['skip_update']=True
            rec['_physical_row_center']=int((int(y1)+int(y2))//2)
            duplicate_key=asset_key(rec.get('asset'))
            if duplicate_key and duplicate_key in seen:
                rec.setdefault('validation_warnings',[]).append('DUPLICATE IN PDF')
                rec['skip_update']=True
            if duplicate_key: seen.add(duplicate_key)
            grid_out.append(rec)
''',
    'grid duplicate retention')

text=text[:start]+func+text[end:]

# The slower count-mismatch reread must not silently convert digits into a master
# identity either. It remains conservative supplemental recovery: complete IDs
# and confirmed new suffixes can be returned; unresolved physical rows are already
# kept by the primary parser for user editing.
start=text.index('def _retry_year15_manhole_rows(')
end=text.index('\ndef master_workbook_lock_reason(',start)
retry=text[start:end]
old_retry='''            digit_item=None
            if not observations:
                digit_item=_unique_manhole_digit_match(base,master_index)
                if digit_item:
                    observations=[digit_item.get('asset') or '']
            if not observations: continue
            confirmed_suffixes=list(dict.fromkeys(_confirmed_suffix_asset_candidates(
                base,known,asset_format=asset_format)))
            if len(confirmed_suffixes)==1:
                item=None; status='NEW MANHOLE'; sid=confirmed_suffixes[0]
            elif digit_item is not None:
                item=digit_item; status='Matched'; sid=item['asset']
            else:
                item,status=_resolve_full_asset(observations,known)
                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))
            if item is None and status!='NEW MANHOLE':
                digit_item=_unique_manhole_digit_match(base,master_index)
                if digit_item:
                    item=digit_item; status='Matched'; sid=item['asset']
            if item is None and status!='NEW MANHOLE': continue
'''
new_retry='''            if not observations: continue
            confirmed_suffixes=list(dict.fromkeys(_confirmed_suffix_asset_candidates(
                base,known,asset_format=asset_format)))
            if len(confirmed_suffixes)==1:
                item=None; status='NEW MANHOLE'; sid=confirmed_suffixes[0]
            else:
                item,status=_resolve_full_asset(observations,known)
                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))
            if item is None and status!='NEW MANHOLE': continue
'''
count=retry.count(old_retry)
assert count==1,f'retry digit auto-match anchor: expected one, found {count}'
retry=retry.replace(old_retry,new_retry,1)
text=text[:start]+retry+text[end:]

SOURCE.write_text(text,encoding='utf-8')

# Documentation: row existence comes from confirmed table structure; matching is
# only an automatic-update decision. Correct the previous pending note that had
# described numeric-body master recovery as the desired behavior.
context=Path('PROJECT_CONTEXT.md')
doc=context.read_text(encoding='utf-8')
old_section='''## Pending after v105 — rotated Pipe classification and physical Manhole-row recovery

- A September 16 Phase 2 packet exposed two independent scan-orientation/OCR failures while production remains v105.
- A rotated Pipe table can have `Length Surveyed`, `Upstream MH`, and `Downstream MH` clearly printed while the lightweight PSM-11 classification pass reads only body rows. If the fast pass remains `other`, classification now performs one 2.5x PSM-6 structured-header retry across the supported orientations before pair-layout fallback; explicit `Length Surveyed` evidence therefore selects Pipe instead of an order-dependent Cleaning tie.
- A ruled Manhole table can contain a real physical row whose DN-/R2- prefix is damaged by the left grid rule even though its numeric body is repeatedly readable. The Manhole parser now retains that row only when the same exact numeric body survives at least two independently framed reads and maps to exactly one existing master Manhole. Ambiguous numeric bodies fail closed, and NEW/suffixed Manholes still require the established full-ID/suffix safeguards.
- Permanent regression: `working_source/tests/regression_post_v105_rotated_pipe_and_manhole_row.py`.
- The supplied customer PDF/master were used only for private diagnosis and remain uncommitted/unpackaged.
'''
new_section='''## Pending after v105 — rotated Pipe classification and never-discard physical rows

- A September 16 Phase 2 packet exposed two independent scan-orientation/OCR failures while production remains v105.
- A rotated Pipe table can have `Length Surveyed`, `Upstream MH`, and `Downstream MH` clearly printed while the lightweight PSM-11 classification pass reads only body rows. If the fast pass remains `other`, classification performs one 2.5x PSM-6 structured-header retry across the supported orientations; explicit `Length Surveyed` evidence selects Pipe instead of an order-dependent Cleaning tie.
- More importantly, table geometry now owns **row existence** while OCR/master matching owns only **automatic update eligibility**. Once a Pipe, Cleaning, or Manhole data row is structurally established, failed ID OCR or a failed master match may not silently remove it from Live Summary.
- Unmatched physical rows remain visible and review-only with the available PDF field previews and any safe OCR hint (`?` when identity is unreadable). `Edit Selected` uses the existing `apply_manual_asset_edit` path, so correcting a Manhole asset or Pipe/Cleaning endpoints immediately reruns matching and makes the row updateable when it resolves.
- Numeric-only Manhole OCR may be shown as an edit hint, but the program no longer supplies a missing `DN-`/`R2-` prefix from the master merely to create a match. A repeated OCR identity is likewise retained as a separate physical row and marked `DUPLICATE IN PDF` for review instead of being deleted.
- A confirmed printed header establishes the first data band for B&C Pipe/Cleaning tables even when the printed total cannot be read; a positively identified total band is still excluded. Header/title/known-total bands remain structural metadata, not summary rows.
- Permanent regressions: `working_source/tests/regression_post_v105_rotated_pipe_and_manhole_row.py` and `working_source/tests/regression_post_v105_physical_rows_never_discarded.py`.
- The supplied customer PDF/master were used only for private diagnosis and remain uncommitted/unpackaged.
'''
assert old_section in doc,'pending context section changed'
doc=doc.replace(old_section,new_section,1)
context.write_text(doc,encoding='utf-8')

check=Path('RELEASE_CHECKLIST.md')
doc=check.read_text(encoding='utf-8')
doc=doc.replace(
    '- post-v105 rotated Pipe classification and physical Manhole-row recovery regression;\n',
    '- post-v105 physical Pipe/Cleaning/Manhole row-retention + manual re-match regression;\n- post-v105 rotated Pipe classification and visible Manhole-row regression;\n',1)
old_mh='''- A physical B&C Manhole row whose full prefix is unreadable may use exact digit-body recovery only when that same numeric body is observed in at least two independently framed reads and identifies exactly one existing master Manhole; ambiguous numeric bodies remain unresolved.
'''
new_mh='''- Once B&C table structure establishes a physical Manhole data row, failed asset OCR or a failed master match must never delete that row from Live Summary. Keep it review-only with the available PDF preview and any OCR hint, and let `Edit Selected` rerun matching after the user corrects the Asset.
- Numeric-only Manhole OCR is an edit hint only; the master must not supply a missing prefix/identity to turn that partial observation into an automatic match. Repeated OCR identities remain separate physical rows and are marked `DUPLICATE IN PDF` for review.
'''
assert old_mh in doc,'Manhole checklist anchor changed'
doc=doc.replace(old_mh,new_mh,1)
length_anchor='''- Confirmed physical rows remain represented even when a field needs review.
'''
length_add='''- Confirmed physical rows remain represented even when a field needs review. Matching failure changes the row to review-only; it never authorizes silently removing a Pipe, Cleaning, or Manhole row from the summary.
'''
assert length_anchor in doc
doc=doc.replace(length_anchor,length_add,1)
check.write_text(doc,encoding='utf-8')

for name in ('PROJECT_CONTEXT.md','RELEASE_CHECKLIST.md'):
    shutil.copyfile(name,Path('working_source/docs')/name)

print('Applied physical-row retention and review semantics')
