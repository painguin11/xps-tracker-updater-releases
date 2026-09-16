from pathlib import Path

path=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=path.read_text(encoding='utf-8')

marker='def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):\n'
helper='''def _year15_manhole_column_boxes(img,bands,table):
    """Locate Manhole Number and Date cells from the printed header order.

    B&C Manhole sheets exist in at least two four-column layouts: the released
    layout starts with Manhole Number and ends with Date, while another layout
    starts with Date and places Manhole Number second. Header token positions
    select the physical cells without weakening asset-ID matching. If header OCR
    is unusable, preserve the established v103 first-ID / last-Date fallback.
    """
    fallback={'asset':(0.0,.27),'date':(.74,1.0),'source':'legacy'}
    if not bands or not table:
        return fallback
    left,right=map(int,table); tw=max(1,right-left); h,w=img.shape[:2]
    for y1,y2 in list(bands)[:4]:
        crop=img[max(0,int(y1)):min(h,int(y2)),max(0,left):min(w,right)]
        if not getattr(crop,'size',0):
            continue
        gray=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
        try:
            data=pytesseract.image_to_data(gray,config='--psm 7',output_type=pytesseract.Output.DICT)
        except Exception:
            continue
        starts={}; width=max(1,crop.shape[1])
        for i,raw in enumerate(data.get('text',[])):
            token=re.sub(r'[^a-z]','',str(raw or '').lower())
            if not token:
                continue
            rel=max(0.0,min(1.0,float(data['left'][i])/width))
            if 'manhole' in token and 'asset' not in starts:
                starts['asset']=rel
            elif 'street' in token and 'street' not in starts:
                starts['street']=rel
            elif 'drainage' in token and 'drainage' not in starts:
                starts['drainage']=rel
            elif (token=='date' or (token.endswith('ate') and token[:1] in ('d','v','o'))) and 'date' not in starts:
                starts['date']=rel
        if 'asset' not in starts or 'date' not in starts or len(starts)<3:
            continue
        ordered=sorted((position,role) for role,position in starts.items())
        role_index={role:index for index,(_,role) in enumerate(ordered)}
        margin=.004
        def role_box(role):
            index=role_index[role]
            start=max(0.0,ordered[index][0]-margin)
            if index==0 and start<.03:
                start=0.0
            end=1.0 if index==len(ordered)-1 else max(start+.04,ordered[index+1][0]-margin)
            return (start,min(1.0,end))
        asset_box=role_box('asset'); date_box=role_box('date')
        if asset_box[1]-asset_box[0]<.10 or date_box[1]-date_box[0]<.08:
            continue
        return {'asset':asset_box,'date':date_box,'source':'header'}
    return fallback


'''
if '_year15_manhole_column_boxes' not in text:
    if marker not in text:
        raise SystemExit('parse_year15_manholes marker not found')
    text=text.replace(marker,helper+marker,1)

start=text.index(marker)
end=text.index('\ndef _retry_year15_manhole_rows',start)
func=text[start:end]
replacements=[
    ('bands,table=_table_row_bands(img,.04,.72)',
     'bands,table=_table_row_bands(img,.04,.90)'),
    ('left,right=table; tw=max(1,right-left); seen=set()',
     "left,right=table; tw=max(1,right-left); seen=set()\n        column_boxes=_year15_manhole_column_boxes(img,bands,table)\n        asset_box=column_boxes['asset']; date_box=column_boxes['date']\n        asset_left=max(0,int(left+asset_box[0]*tw)); asset_right=min(w,int(left+asset_box[1]*tw))\n        date_left=max(0,int(left+date_box[0]*tw)); date_right=min(w,int(left+date_box[1]*tw))"),
    ('id_img=img[y1:y2,left:min(w,int(left+.27*tw))]',
     'id_img=img[y1:y2,asset_left:asset_right]'),
    ('retry_left=max(0,left+left_trim)\n                retry_right=min(w,int(left+.245*tw))',
     "retry_left=max(0,asset_left+left_trim)\n                right_trim=max(2,int(round(max(1,asset_right-asset_left)*.08)))\n                retry_right=max(retry_left+1,asset_right-right_trim)"),
    ('date_img=img[y1:y2,int(left+.74*tw):right]',
     'date_img=img[y1:y2,date_left:date_right]'),
]
for old,new in replacements:
    if old not in func:
        raise SystemExit(f'parse_year15_manholes patch target missing: {old!r}')
    func=func.replace(old,new,1)
text=text[:start]+func+text[end:]

retry_marker='def _retry_year15_manhole_rows(page, master_index, on_progress=None, orientation_deg=None):\n'
rstart=text.index(retry_marker)
rend=text.index('\ndef master_workbook_lock_reason',rstart)
retry=text[rstart:rend]
replacements=[
    ('bands,table=_table_row_bands(img,.04,.72)',
     'bands,table=_table_row_bands(img,.04,.90)'),
    ('left,right=retry_table; tw=max(1,right-left)\n        for y1,y2 in retry_bands:',
     "left,right=retry_table; tw=max(1,right-left)\n        column_boxes=_year15_manhole_column_boxes(img,retry_bands,retry_table)\n        asset_box=column_boxes['asset']; date_box=column_boxes['date']\n        asset_left=max(0,int(left+asset_box[0]*tw)); asset_right=min(w,int(left+asset_box[1]*tw))\n        date_left=max(0,int(left+date_box[0]*tw)); date_right=min(w,int(left+date_box[1]*tw))\n        for y1,y2 in retry_bands:"),
    ('base=img[y1:y2,left:min(w,int(left+.30*tw))]',
     'base=img[y1:y2,asset_left:asset_right]'),
    ('trimmed=img[y1:y2,max(0,left+trim):min(w,int(left+.255*tw))]',
     "right_trim=max(2,int(round(max(1,asset_right-asset_left)*.07)))\n            trimmed=img[y1:y2,max(0,asset_left+trim):max(asset_left+trim+1,asset_right-right_trim)]"),
    ('date_img=img[y1:y2,int(left+.74*tw):right]',
     'date_img=img[y1:y2,date_left:date_right]'),
]
for old,new in replacements:
    if old not in retry:
        raise SystemExit(f'_retry_year15_manhole_rows patch target missing: {old!r}')
    retry=retry.replace(old,new,1)
text=text[:rstart]+retry+text[rend:]

path.write_text(text,encoding='utf-8')
print('Applied post-v103 reordered Manhole column patch')
