from pathlib import Path
import shutil

SOURCE=Path('working_source/app/reno_scan_updater.py')
text=SOURCE.read_text(encoding='utf-8')

old_classify='''    _,arr,deg,txt,kind=max(candidates,key=lambda x:x[0])
    return arr,deg,txt,kind
'''
new_classify='''    best=max(candidates,key=lambda x:x[0])
    # Some rotated B&C scans have a crisp printed header but PSM-11 at the
    # lightweight 1.25x classification render reads only body rows. When that
    # fast pass cannot classify the page, make one high-resolution structured
    # header retry before later layout inference gets a chance to choose an
    # activity type by tie/order alone. This is intentionally limited to pages
    # still classified as other, so normal fast classification is unchanged.
    if best[4]=='other':
        hi=render_page(page,2.5)
        retry=[]
        for retry_deg in (0,270,90):
            retry_arr=hi if retry_deg==0 else np.array(Image.fromarray(hi).rotate(retry_deg,expand=True))
            header=retry_arr[:max(1,int(retry_arr.shape[0]*.35)),:]
            retry_txt=ocr_text(header,6); retry_low=retry_txt.lower()
            retry_norm=re.sub(r'[^a-z0-9]+',' ',retry_low)
            endpoint_score=(max(retry_norm.count('upstream'),retry_norm.count('up mh'))+
                            max(retry_norm.count('downstream'),retry_norm.count('dn mh')))
            cleaning_header=(
                'wheel wal' in retry_norm or 'wheelwalk' in retry_norm or
                'cleaning date' in retry_norm or
                ('wheel' in retry_norm and 'walk' in retry_norm) or
                ('cleaning' in retry_norm and 'date' in retry_norm)
            )
            if cleaning_header and ('project yea' in retry_norm or 'field crew' in retry_norm or endpoint_score):
                retry_kind='cleaning'; retry_score=25+endpoint_score
            elif ('manhole number' in retry_norm or
                  ('drainage area' in retry_norm and 'street' in retry_norm and 'date' in retry_norm)):
                retry_kind='manholes'; retry_score=20
            elif ('length surveyed' in retry_norm or 'surveyed length' in retry_norm) and endpoint_score:
                retry_kind='pipes'; retry_score=20+endpoint_score
            else:
                retry_kind='other'; retry_score=0
            retry.append((retry_score,retry_arr,retry_deg,retry_txt,retry_kind))
        retry_best=max(retry,key=lambda x:x[0])
        if retry_best[4]!='other':
            best=retry_best
    _,arr,deg,txt,kind=best
    return arr,deg,txt,kind
'''
assert text.count(old_classify)==1, 'classify_for_profile anchor changed'
text=text.replace(old_classify,new_classify,1)

anchor="\ndef parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):\n"
helper=r'''
def _unique_manhole_digit_match(cell_img, master_index):
    # Resolve a damaged Manhole prefix only from repeated exact PDF digits.
    # The full existing ID can come from the master only when the same numeric
    # body is observed in at least two independently framed views of this one
    # physical cell and uniquely identifies one master Manhole.
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return None
    by_number=master_index.get('manholes_by_number') or {}
    if not isinstance(by_number,dict) or not by_number:
        return None
    width=cell_img.shape[1]
    views=[cell_img]
    for ratio in (.025,.05):
        trim=max(1,int(round(width*ratio)))
        if width>trim*2+8:
            views.append(cell_img[:,trim:width-trim])
    support={}
    for view in views:
        seen=set()
        for raw in _ocr_digits(view,False,fast_plain=True):
            token=re.sub(r'\D','',str(raw or ''))
            if token:
                seen.add(token)
        for token in seen:
            support[token]=support.get(token,0)+1
    winners={}
    for token,count in support.items():
        if count<2:
            continue
        items=list(by_number.get(token) or [])
        if len(items)!=1:
            continue
        item=items[0]
        key=item.get('asset_key') or asset_key(item.get('asset'))
        if key:
            winners[key]=item
    return next(iter(winners.values())) if len(winners)==1 else None

'''
assert text.count(anchor)==1, 'parse_year15_manholes anchor changed'
text=text.replace(anchor,'\n'+helper+anchor.lstrip('\n'),1)

old_normal='''            if not observations: continue
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
                item,status=_resolve_full_asset(observations,known)
                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))
'''
new_normal='''            digit_item=None
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
'''
assert text.count(old_normal)==1, 'normal Manhole OCR block changed'
text=text.replace(old_normal,new_normal,1)

old_retry='''            if not observations: continue
            confirmed_suffixes=list(dict.fromkeys(_confirmed_suffix_asset_candidates(
                base,known,asset_format=asset_format)))
            if len(confirmed_suffixes)==1:
                item=None; status='NEW MANHOLE'; sid=confirmed_suffixes[0]
            else:
                item,status=_resolve_full_asset(observations,known)
                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))
            if item is None and status!='NEW MANHOLE': continue
'''
new_retry='''            digit_item=None
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
assert text.count(old_retry)==1, 'retry Manhole OCR block changed'
text=text.replace(old_retry,new_retry,1)

SOURCE.write_text(text,encoding='utf-8')

context=Path('PROJECT_CONTEXT.md')
doc=context.read_text(encoding='utf-8')
marker='## Released in v105 — preserve independently confirmed new Manhole suffixes\n'
pending='''## Pending after v105 — rotated Pipe classification and physical Manhole-row recovery

- A September 16 Phase 2 packet exposed two independent scan-orientation/OCR failures while production remains v105.
- A rotated Pipe table can have `Length Surveyed`, `Upstream MH`, and `Downstream MH` clearly printed while the lightweight PSM-11 classification pass reads only body rows. If the fast pass remains `other`, classification now performs one 2.5x PSM-6 structured-header retry across the supported orientations before pair-layout fallback; explicit `Length Surveyed` evidence therefore selects Pipe instead of an order-dependent Cleaning tie.
- A ruled Manhole table can contain a real physical row whose DN-/R2- prefix is damaged by the left grid rule even though its numeric body is repeatedly readable. The Manhole parser now retains that row only when the same exact numeric body survives at least two independently framed reads and maps to exactly one existing master Manhole. Ambiguous numeric bodies fail closed, and NEW/suffixed Manholes still require the established full-ID/suffix safeguards.
- Permanent regression: `working_source/tests/regression_post_v105_rotated_pipe_and_manhole_row.py`.
- The supplied customer PDF/master were used only for private diagnosis and remain uncommitted/unpackaged.

'''
assert marker in doc and '## Pending after v105 — rotated Pipe classification' not in doc
doc=doc.replace(marker,pending+marker,1)
context.write_text(doc,encoding='utf-8')

checklist=Path('RELEASE_CHECKLIST.md')
doc=checklist.read_text(encoding='utf-8')
active='The active baseline includes, at minimum:\n\n'
addition='- post-v105 rotated Pipe classification and physical Manhole-row recovery regression;\n'
assert active in doc and addition not in doc
doc=doc.replace(active,active+addition,1)
mh_marker='### Manholes\n\n'
mh_add='''- A physical B&C Manhole row whose full prefix is unreadable may use exact digit-body recovery only when that same numeric body is observed in at least two independently framed reads and identifies exactly one existing master Manhole; ambiguous numeric bodies remain unresolved.
'''
assert mh_marker in doc and mh_add not in doc
doc=doc.replace(mh_marker,mh_marker+mh_add,1)
checklist.write_text(doc,encoding='utf-8')

for name in ('PROJECT_CONTEXT.md','RELEASE_CHECKLIST.md'):
    shutil.copyfile(name,Path('working_source/docs')/name)

print('Applied post-v105 page 4/page 6 fix and docs')
