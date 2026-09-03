from pathlib import Path

path=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=path.read_text(encoding='utf-8')

helper='''\n\ndef _batch_pair_endpoint_digit_candidates(img,bands,table,box):
    """Read each endpoint cell in a padded stack and return OCR-observed digits.

    Whole-column OCR can skip a cluster of otherwise clean rows, while isolated
    grid cells can be harmed by their border rules.  This fallback gives every
    physical endpoint cell its own white-padded tile, stacks those tiles into one
    OCR image, and maps observed numeric bodies back to the original row bands.
    It supplies PDF evidence only; pair resolution still requires both endpoint
    bodies to identify exactly one existing directional master pipe.
    """
    if img is None or not bands or not table or not box:
        return {}
    left,right=table; tw=max(1,right-left); h,w=img.shape[:2]
    x1=max(0,int(left+box[0]*tw)); x2=min(w,int(left+box[1]*tw))
    if x2<=x1:
        return {}
    # A few rendered pixels retain glyphs that sit against a vertical grid rule.
    x1=max(0,x1-3); x2=min(w,x2+3)
    tiles=[]; tile_indices=[]
    for band_index,(y1,y2) in enumerate(bands):
        cell=img[max(0,int(y1)):min(h,int(y2)),x1:x2]
        if not getattr(cell,'size',0):
            continue
        ch,cw=cell.shape[:2]
        top=max(1,int(round(ch*.10))); bottom=max(1,int(round(ch*.10)))
        sample=cell[top:max(top+2,ch-bottom),:]
        if not getattr(sample,'size',0):
            continue
        gray=cv2.cvtColor(sample,cv2.COLOR_RGB2GRAY)
        gray=cv2.resize(gray,None,fx=3.5,fy=3.5,interpolation=cv2.INTER_CUBIC)
        gray=cv2.copyMakeBorder(gray,12,12,24,24,cv2.BORDER_CONSTANT,value=255)
        tiles.append(gray); tile_indices.append(band_index)
    if not tiles:
        return {}
    width=max(tile.shape[1] for tile in tiles)
    padded=[]; spans=[]; cursor=0
    for band_index,tile in zip(tile_indices,tiles):
        if tile.shape[1]<width:
            tile=cv2.copyMakeBorder(tile,0,0,0,width-tile.shape[1],cv2.BORDER_CONSTANT,value=255)
        padded.append(tile)
        spans.append((band_index,cursor,cursor+tile.shape[0]))
        cursor+=tile.shape[0]
    stack=np.vstack(padded)
    found={}
    for psm in (6,11):
        try:
            data=pytesseract.image_to_data(
                stack,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789',
                output_type=pytesseract.Output.DICT)
        except Exception:
            continue
        for i,raw in enumerate(data.get('text',[])):
            tokens=re.findall(r'(?<!\\d)\\d{1,8}(?!\\d)',str(raw or '').strip())
            if not tokens:
                continue
            try:
                yc=float(data['top'][i])+float(data['height'][i])/2.0
            except Exception:
                continue
            span=min(spans,key=lambda item:abs(yc-(item[1]+item[2])/2.0))
            if not (span[1]-4<=yc<=span[2]+4):
                continue
            values=found.setdefault(span[0],[])
            for token in tokens:
                if token not in values:
                    values.append(token)
    return found
'''

sentinel='\n\ndef _ocr_known_r2_candidates(cell_img, known_items, asset_format=None):'
if '_batch_pair_endpoint_digit_candidates' not in s:
    if sentinel not in s:
        raise SystemExit('endpoint helper insertion point not found')
    s=s.replace(sentinel,helper+sentinel,1)

old="def _resolve_pipe_pair_from_endpoint_digits(up_cell,dn_cell,master_index):"
new="def _resolve_pipe_pair_from_endpoint_digits(up_cell,dn_cell,master_index,up_extra=None,dn_extra=None):"
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('numeric pair resolver signature not found')

old_tokens="""    up_tokens=_endpoint_digit_tokens(up_cell)\n    dn_tokens=_endpoint_digit_tokens(dn_cell)\n"""
new_tokens="""    up_tokens=list(dict.fromkeys(_endpoint_digit_tokens(up_cell)+list(up_extra or [])))\n    dn_tokens=list(dict.fromkeys(_endpoint_digit_tokens(dn_cell)+list(dn_extra or [])))\n"""
if old_tokens in s:
    s=s.replace(old_tokens,new_tokens,1)
elif new_tokens not in s:
    raise SystemExit('numeric pair resolver token block not found')

old_batch="""    batch_up_endpoints=_batch_pair_endpoint_candidates(img,bands,table,up_box,asset_format)\n    batch_dn_endpoints=_batch_pair_endpoint_candidates(img,bands,table,dn_box,asset_format)\n    rows=[]; seen=set()\n"""
new_batch="""    batch_up_endpoints=_batch_pair_endpoint_candidates(img,bands,table,up_box,asset_format)\n    batch_dn_endpoints=_batch_pair_endpoint_candidates(img,bands,table,dn_box,asset_format)\n    # Build the more expensive padded-cell digit stack only if a row actually\n    # survives the normal full-ID and R2 recovery paths unresolved.\n    batch_up_digit_endpoints=None; batch_dn_digit_endpoints=None\n    rows=[]; seen=set()\n"""
if old_batch in s:
    s=s.replace(old_batch,new_batch,1)
elif new_batch not in s:
    raise SystemExit('pair parser batch setup not found')

old_call="""            digit_match=_resolve_pipe_pair_from_endpoint_digits(cut(up_box),cut(dn_box),master_index)\n"""
new_call="""            if batch_up_digit_endpoints is None:\n                batch_up_digit_endpoints=_batch_pair_endpoint_digit_candidates(img,bands,table,up_box)\n                batch_dn_digit_endpoints=_batch_pair_endpoint_digit_candidates(img,bands,table,dn_box)\n            digit_match=_resolve_pipe_pair_from_endpoint_digits(\n                cut(up_box,horizontal_bleed=3),cut(dn_box,horizontal_bleed=3),master_index,\n                up_extra=batch_up_digit_endpoints.get(band_index,[]),\n                dn_extra=batch_dn_digit_endpoints.get(band_index,[]))\n"""
if old_call in s:
    s=s.replace(old_call,new_call,1)
elif new_call not in s:
    raise SystemExit('pair parser numeric recovery call not found')

path.write_text(s,encoding='utf-8')
print('Applied v94 stacked endpoint digit recovery.')
