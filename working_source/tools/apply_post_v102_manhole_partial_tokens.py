from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')

NEW_FUNCTION=r"""def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):
    asset_format=master_index.get('asset_format')
    img=_year15_oriented(page,'manholes',preferred_deg=orientation_deg); h,w=img.shape[:2]
    known=master_index['manholes']
    # This portrait report OCRs reliably as positioned words on many scans, but a
    # ruled grid can also make whole-page Tesseract skip most rows. Keep the
    # positioned-token path, then compare it with the physical row-grid path and
    # use whichever preserves more distinct printed Manhole rows.
    token_rows=[]; token_dates=[]
    for psm in (6,11):
        if on_progress: on_progress()
        gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
        data=pytesseract.image_to_data(gray,config=f'--psm {psm}',output_type=pytesseract.Output.DICT)
        for i,txt in enumerate(data.get('text',[])):
            x=int(data['left'][i]); y=int(data['top'][i]); hh=int(data['height'][i])
            parsed_date=parse_date_text(str(txt))
            if x>w*.62 and parsed_date:
                token_dates.append((y+hh//2,parsed_date))
            if x>w*.36: continue
            raw=str(txt)
            formatted=_printed_asset_tokens(raw,asset_format)
            if not formatted: continue
            item,status=_resolve_full_asset(formatted,known)
            token_rows.append((y+hh//2,item,status,formatted[0]))

    token_out=[]
    if token_rows:
        token_rows.sort(key=lambda x:x[0]); clustered=[]
        for row in token_rows:
            if clustered and abs(row[0]-clustered[-1][0])<h*.012:
                # Prefer a matched reading over an ambiguous reading of the same row.
                if clustered[-1][1] is None and row[1] is not None: clustered[-1]=row
            else: clustered.append(row)
        seen=set()
        for yc,item,status,raw in clustered:
            if on_progress: on_progress()
            sid=item['asset'] if item else (_best_observed_asset_id([raw],known) or canonical_asset_id(raw))
            unique_key=item['asset_key'] if item else f'row-{yc}'
            if unique_key in seen: continue
            row_date=None
            near=[x for x in token_dates if abs(x[0]-yc)<h*.025]
            if near: row_date=min(near,key=lambda x:abs(x[0]-yc))[1]
            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',
                 'video_length':None,'row_date':row_date,'status':status}
            preview_half=max(8,int(round(h*.018)))
            asset_preview=img[max(0,int(yc)-preview_half):min(h,int(yc)+preview_half),0:int(w*.38)]
            date_preview=img[max(0,int(yc)-preview_half):min(h,int(yc)+preview_half),int(w*.60):w]
            rec['_field_previews']={
                'asset':asset_preview.copy() if getattr(asset_preview,'size',0) else None,
                'date':date_preview.copy() if getattr(date_preview,'size',0) else None}
            if item is None: rec['skip_update']=True
            seen.add(unique_key); token_out.append(rec)

    grid_out=[]
    bands,table=_table_row_bands(img,.04,.72)
    if bands and table:
        left,right=table; tw=max(1,right-left); seen=set()
        for y1,y2 in bands:
            if on_progress: on_progress()
            id_img=img[y1:y2,left:min(w,int(left+.27*tw))]
            observations=_ocr_asset_candidates(id_img,asset_format=asset_format)
            if not observations:
                # Some B&C scans put the first ID glyph directly against the left
                # vertical rule. Tight-cell OCR can then attach that rule as a
                # leading I/J/L-like character, which makes the otherwise-complete
                # ID fail the strict project-format token check. Retry only this
                # Manhole ID cell with a few pixels of left-rule trim and slightly
                # less right-side street bleed; do not loosen the global ID parser.
                left_trim=max(2,min(8,int(round(tw*.004))))
                retry_left=max(0,left+left_trim)
                retry_right=min(w,int(left+.245*tw))
                if retry_right>retry_left:
                    retry_img=img[y1:y2,retry_left:retry_right]
                    observations=_ocr_asset_candidates(
                        retry_img,fast_plain=True,asset_format=asset_format)
            if not observations: continue
            item,status=_resolve_full_asset(observations,known)
            sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))
            date_img=img[y1:y2,int(left+.74*tw):right]
            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',
                 'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}
            rec['_field_previews']={
                'asset':id_img.copy() if getattr(id_img,'size',0) else None,
                'date':date_img.copy() if getattr(date_img,'size',0) else None}
            if item is None: rec['skip_update']=True
            if rec['asset'] in seen: continue
            seen.add(rec['asset']); grid_out.append(rec)

    out=grid_out if len(grid_out)>len(token_out) else token_out
    for rec in out:
        if on_row: on_row(rec)
    return out
"""

def replace_function(text):
    start=text.find('def parse_year15_manholes(')
    end=text.find('\ndef master_workbook_lock_reason(',start)
    if start<0 or end<0:
        raise SystemExit('Could not locate parse_year15_manholes boundaries')
    current=text[start:end]
    if 'token_out=[]' in current and 'left_trim=max(2,min(8,int(round(tw*.004))))' in current:
        return text
    if 'if token_rows:' not in current or "_table_row_bands(img,.04,.72)" not in current:
        raise SystemExit('parse_year15_manholes no longer matches expected v102 baseline; refusing broad replacement')
    return text[:start]+NEW_FUNCTION.rstrip()+'\n\n'+text[end+1:]

def patch_project_context(path):
    text=path.read_text(encoding='utf-8')
    marker='## Pending after v102 — Manhole partial-token recovery'
    if marker in text:
        return
    anchor='## Released in v95\n'
    if anchor not in text:
        raise SystemExit(f'Could not locate PROJECT_CONTEXT insertion point in {path}')
    section="""## Pending after v102 — Manhole partial-token recovery

- A supplied B&C Small Diameter Phase 2 Year 1 Manhole scan contains 21 printed
  rows, but whole-page positioned-token OCR can see only a small subset because
  the ruled table interferes with Tesseract segmentation.
- The Manhole parser now keeps the positioned-token result and also evaluates the
  existing physical row-grid path, then returns whichever preserves more distinct
  printed Manhole rows. This is Manhole-only and does not change Pipe/Cleaning
  matching or global asset-ID rules.
- When a ruled Manhole row produces no valid ID, one narrow retry trims a few
  pixels of the left grid rule and reduces right-side street bleed before using
  the existing strict asset parser. This recovers complete IDs without weakening
  prefix/dash/suffix safeguards.
- The supplied private PDF was used locally for diagnosis and recovered all
  21/21 printed Manhole IDs with this row-grid/narrow-cell path. The customer PDF
  remains private and uncommitted.
- Permanent synthetic regression:
  `working_source/tests/regression_post_v102_manhole_partial_tokens.py`.

"""
    path.write_text(text.replace(anchor,section+anchor,1),encoding='utf-8')

def patch_release_checklist(path):
    text=path.read_text(encoding='utf-8')
    bullet='- post-v102 Manhole partial-token/grid-row recovery regression;\n'
    if bullet not in text:
        anchor='The active baseline includes, at minimum:\n\n'
        if anchor not in text:
            raise SystemExit(f'Could not locate RELEASE_CHECKLIST baseline list in {path}')
        text=text.replace(anchor,anchor+bullet,1)
    named='- `working_source/tests/regression_post_v102_manhole_partial_tokens.py`\n'
    if named not in text:
        anchor2='The following post-version-named regressions are already released and remain required:\n\n'
        if anchor2 not in text:
            raise SystemExit(f'Could not locate named regression list in {path}')
        text=text.replace(anchor2,anchor2+named,1)
    path.write_text(text,encoding='utf-8')

src=SOURCE.read_text(encoding='utf-8')
patched=replace_function(src)
if patched!=src:
    SOURCE.write_text(patched,encoding='utf-8')

for doc in (Path('PROJECT_CONTEXT.md'),Path('working_source/docs/PROJECT_CONTEXT.md')):
    patch_project_context(doc)
for doc in (Path('RELEASE_CHECKLIST.md'),Path('working_source/docs/RELEASE_CHECKLIST.md')):
    patch_release_checklist(doc)

print('Applied targeted post-v102 Manhole partial-token recovery.')
