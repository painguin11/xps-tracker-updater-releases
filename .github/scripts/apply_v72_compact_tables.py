from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
text=path.read_text(encoding='utf-8')

marker='def _year15_grid_bands(img):\n'
if marker not in text:
    raise SystemExit('year15 grid marker not found')

helper=r'''def _year15_compact_grid_bands(img):
    """Fallback for valid pair tables that occupy only a small part of the page.

    The normal Year 15 detector intentionally requires very long full-page grid
    rules. Some B&C scans place a perfectly valid table in only the upper quarter
    or third of the sheet, so those rules are short relative to the page even
    though they span essentially the entire table. This fallback first isolates
    the largest connected table-like region, then measures vertical continuity
    relative to that region. It is used only after the strict detector fails.
    """
    h,w=img.shape[:2]
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)

    # A slightly lighter threshold is appropriate only for locating the connected
    # table region. Actual column rules are re-validated below at a stricter level.
    inv=cv2.threshold(gray,235,255,cv2.THRESH_BINARY_INV)[1]
    connected=cv2.morphologyEx(
        inv,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)))
    contours,_=cv2.findContours(connected,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    candidates=[]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if ww>=w*.35 and hh>=h*.12 and ww*hh<=w*h*.85:
            candidates.append((ww*hh,x,y,ww,hh))
    if not candidates:
        return [],None,None

    _,bx,by,bw,bh=max(candidates)
    crop=img[by:by+bh,bx:bx+bw]
    if crop.size==0:
        return [],None,None

    cgray=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
    cinv=cv2.threshold(cgray,225,255,cv2.THRESH_BINARY_INV)[1]
    joined=cv2.morphologyEx(
        cinv,cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(3,int(bh*.012)))))
    vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(20,int(bh*.12))))
    vertical=cv2.morphologyEx(joined,cv2.MORPH_OPEN,vk)
    contours,_=cv2.findContours(vertical,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    # Short fragments at one x-coordinate are merged before judging continuity.
    # This repairs grid rules interrupted by printed text crossing the line.
    rules=[]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if hh>=bh*.18 and ww<=max(24,bw*.025):
            rules.append((x+ww//2,y,y+hh))
    rules.sort(); merged=[]
    for rule in rules:
        if merged and abs(rule[0]-merged[-1][0])<=max(5,int(bw*.006)):
            old=merged[-1]
            merged[-1]=((old[0]+rule[0])//2,min(old[1],rule[1]),max(old[2],rule[2]))
        else:
            merged.append(rule)
    if len(merged)<5:
        return [],None,None

    max_span=max(y2-y1 for _,y1,y2 in merged)
    strong=[rule for rule in merged if rule[2]-rule[1]>=max_span*.85]
    if len(strong)<5:
        return [],None,None

    xs=[]
    for x,_,_ in strong:
        full_x=bx+x
        if not xs or full_x-xs[-1]>max(4,int(bw*.004)):
            xs.append(full_x)
        else:
            xs[-1]=(xs[-1]+full_x)//2
    if len(xs)<5:
        return [],None,None
    left,right=xs[0],xs[-1]
    if right-left<w*.35:
        return [],None,None

    # Build row bands from horizontal rules inside the isolated table. A compact
    # table may have a title band before the actual column header, so keep the
    # first meaningful tall band and let header-role OCR choose among the first
    # four bands as it already does on normal layouts.
    roi=inv[by:by+bh,max(0,left):min(w,right)]
    hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(35,int((right-left)*.20)),1))
    horizontal=cv2.morphologyEx(roi,cv2.MORPH_OPEN,hk)
    contours,_=cv2.findContours(horizontal,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    ys=[by,by+bh-1]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if ww>=(right-left)*.45 and hh<=max(14,h*.018):
            ys.append(by+y+hh//2)
    ys.sort(); ymerged=[]
    for y in ys:
        if not ymerged or y-ymerged[-1]>max(3,int(h*.004)):
            ymerged.append(y)
        else:
            ymerged[-1]=(ymerged[-1]+y)//2

    bands=[]; first_meaningful=True
    for a,b in zip(ymerged,ymerged[1:]):
        gap=b-a
        if gap<10:
            continue
        gap_limit=max(140,int(bh*.30)) if first_meaningful else max(90,int(bh*.18))
        if gap<=gap_limit:
            pad=max(2,int(gap*.10))
            bands.append((a+pad,b-pad))
            first_meaningful=False
    if not bands:
        return [],None,None
    return bands,(left,right),xs


'''
text=text.replace(marker,helper+marker,1)

old="""    bands,table,column_bounds=_year15_grid_bands(img)\n    geometry_source='vertical grid'\n    if not bands:\n        bands,table=_year15_all_row_bands(img,.04,.90); column_bounds=None; geometry_source='horizontal fallback'\n"""
new="""    bands,table,column_bounds=_year15_grid_bands(img)\n    geometry_source='vertical grid'\n    if not bands:\n        bands,table,column_bounds=_year15_compact_grid_bands(img)\n        if bands: geometry_source='compact table grid'\n    if not bands:\n        bands,table=_year15_all_row_bands(img,.04,.90); column_bounds=None; geometry_source='horizontal fallback'\n"""
if old not in text:
    raise SystemExit('prepare_year15_pair_layout fallback block not found')
text=text.replace(old,new,1)

path.write_text(text,encoding='utf-8')

# Add a static regression guard. Customer PDFs remain local and are never copied
# into this public repository.
test=Path('working_source/tests/regression_compact_table_fallback.py')
test.write_text(r'''from pathlib import Path

source=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'def _year15_compact_grid_bands' in source
assert "geometry_source='compact table grid'" in source
assert 'hh>=bh*.18' in source
assert 'rule[2]-rule[1]>=max_span*.85' in source
assert "if not bands:\n        bands,table,column_bounds=_year15_compact_grid_bands(img)" in source
assert source.index('_year15_compact_grid_bands(img)') < source.index("_year15_all_row_bands(img,.04,.90)")
print('Compact Year 15 table fallback guard passed.')
''',encoding='utf-8')
