from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')

marker='def _batch_pair_endpoint_digit_candidates(img,bands,table,box):\n'
assert marker in s and 'def _batch_pair_endpoint_full_candidates(' not in s
helper=r'''def _batch_pair_endpoint_full_candidates(img,bands,table,box,asset_format=None,known_items=None):
    """Recover complete endpoint IDs from individually padded row cells.

    Whole-column OCR can skip rows, while tight isolated cells can lose the first
    or last glyph to a grid rule. This fallback gives each physical endpoint cell
    white breathing room, stacks the cells, and OCRs the same observed pixels with
    independent segmentation/threshold passes. A complete ID is returned only
    when at least two passes agree. The master is used only to reject impossible
    project prefixes; it never supplies missing letters or digits.
    """
    if img is None or not bands or not table or not box:
        return {}
    left,right=table; tw=max(1,right-left); h,w=img.shape[:2]
    x1=max(0,int(left+box[0]*tw)-3); x2=min(w,int(left+box[1]*tw)+3)
    if x2<=x1:
        return {}
    prefixes=set()
    for key in (known_items or {}):
        parts=_asset_id_parts(key)
        if parts: prefixes.add(parts[0])
    tiles=[]; spans=[]; cursor=0
    for band_index,(y1,y2) in enumerate(bands):
        cell=img[max(0,int(y1)):min(h,int(y2)),x1:x2]
        if not getattr(cell,'size',0):
            continue
        ch,cw=cell.shape[:2]
        trim=max(1,int(round(ch*.08)))
        sample=cell[trim:max(trim+2,ch-trim),:]
        if not getattr(sample,'size',0):
            continue
        gray=cv2.cvtColor(sample,cv2.COLOR_RGB2GRAY)
        gray=cv2.resize(gray,None,fx=4.0,fy=4.0,interpolation=cv2.INTER_CUBIC)
        gray=cv2.copyMakeBorder(gray,16,16,36,36,cv2.BORDER_CONSTANT,value=255)
        tiles.append((band_index,gray))
    if not tiles:
        return {}
    width=max(tile.shape[1] for _,tile in tiles)
    padded=[]
    for band_index,tile in tiles:
        if tile.shape[1]<width:
            tile=cv2.copyMakeBorder(tile,0,0,0,width-tile.shape[1],cv2.BORDER_CONSTANT,value=255)
        spans.append((band_index,cursor,cursor+tile.shape[0]))
        cursor+=tile.shape[0]; padded.append(tile)
    stack=np.vstack(padded)
    variants=[('gray',stack)]
    try:
        variants.append(('otsu',cv2.threshold(stack,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]))
    except Exception:
        pass
    votes={}
    whitelist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
    for variant_name,variant in variants:
        for psm in (6,11):
            pass_id=f'{variant_name}-{psm}'
            try:
                data=pytesseract.image_to_data(
                    variant,config=f'--psm {psm} -c tessedit_char_whitelist={whitelist}',
                    output_type=pytesseract.Output.DICT)
            except Exception:
                continue
            for i,raw in enumerate(data.get('text',[])):
                text=str(raw or '').strip().upper()
                if not text:
                    continue
                try:
                    yc=float(data['top'][i])+float(data['height'][i])/2.0
                except Exception:
                    continue
                span=min(spans,key=lambda item:abs(yc-(item[1]+item[2])/2.0))
                if not (span[1]-5<=yc<=span[2]+5):
                    continue
                raw_variants=[text]
                # A vertical grid rule is commonly read as one leading I/J/L/1.
                # Strip exactly one such glyph only when the remainder is a valid
                # project-format token with a prefix already present in the master.
                if len(text)>1 and text[0] in 'IJL1':
                    raw_variants.append(text[1:])
                for raw_variant in raw_variants:
                    for token in _printed_asset_tokens(raw_variant,asset_format):
                        parts=_asset_id_parts(token)
                        if prefixes and (not parts or parts[0] not in prefixes):
                            continue
                        votes.setdefault(span[0],{}).setdefault(token,set()).add(pass_id)
    out={}
    for band_index,band_votes in votes.items():
        accepted=[(len(pass_ids),token) for token,pass_ids in band_votes.items() if len(pass_ids)>=2]
        if accepted:
            accepted.sort(key=lambda item:(-item[0],item[1]))
            out[band_index]=[token for _,token in accepted]
    return out


'''
s=s.replace(marker,helper+marker,1)

old="    batch_up_digit_endpoints=None; batch_dn_digit_endpoints=None\n"
new="    batch_up_full_endpoints=None; batch_dn_full_endpoints=None\n    batch_up_digit_endpoints=None; batch_dn_digit_endpoints=None\n"
assert old in s
s=s.replace(old,new,1)

old='''        match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n        if not match and match_status!='NEW PIPE':\n'''
new='''        match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n        padded_up=[]; padded_dn=[]\n        # Before any lossy prefix/digit fallback, give unresolved rows an\n        # independent complete-ID read from white-padded physical cells. This is\n        # especially important for newly suffixed endpoints such as DN-2241A,\n        # where numeric-only recovery would erase the printed suffix.\n        if not match:\n            if batch_up_full_endpoints is None:\n                batch_up_full_endpoints=_batch_pair_endpoint_full_candidates(\n                    img,bands,table,up_box,asset_format,endpoint_items)\n                batch_dn_full_endpoints=_batch_pair_endpoint_full_candidates(\n                    img,bands,table,dn_box,asset_format,endpoint_items)\n            padded_up=list(batch_up_full_endpoints.get(band_index,[]))\n            padded_dn=list(batch_dn_full_endpoints.get(band_index,[]))\n            # A two-pass complete-ID consensus is stronger than the unresolved\n            # tight/whole-column observations that triggered this fallback.\n            # Replace only the endpoint(s) for which that consensus exists so a\n            # stray whole-column suffix cannot make a real new pipe ambiguous.\n            if padded_up: up_obs=padded_up\n            if padded_dn: dn_obs=padded_dn\n            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n        authoritative_pair=(\n            bool(_authoritative_asset_candidates(up_obs,endpoint_items)) and\n            bool(_authoritative_asset_candidates(dn_obs,endpoint_items)))\n        if not match and match_status!='NEW PIPE' and not authoritative_pair:\n'''
assert old in s
s=s.replace(old,new,1)

old="        if not match and match_status!='NEW PIPE':\n            # If grid/prefix damage erased EC/DN/R2 but both endpoint numbers are\n"
new="        if not match and match_status!='NEW PIPE' and not authoritative_pair:\n            # If grid/prefix damage erased EC/DN/R2 but both endpoint numbers are\n"
assert old in s
s=s.replace(old,new,1)

old="        if not match and match_status!='NEW PIPE':\n            # Escalate only uncertain endpoint cells to the slower OCR ensemble.\n"
new="        if not match and match_status!='NEW PIPE' and not authoritative_pair:\n            # Escalate only uncertain endpoint cells to the slower OCR ensemble.\n"
assert old in s
s=s.replace(old,new,1)

old='''            up_confirmed=_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,asset_format=asset_format)\n            dn_confirmed=_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)\n'''
new='''            up_confirmed=_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,asset_format=asset_format)\n            dn_confirmed=_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)\n            # The padded complete-ID stack is already an independent multi-pass\n            # read of the same printed cell. Let that consensus corroborate a\n            # suffix when tight-cell confirmation is damaged by the grid rule.\n            up_confirmed=list(dict.fromkeys(up_confirmed+[value for value in padded_up\n                if _new_suffix_asset_candidates([value],endpoint_items)]))\n            dn_confirmed=list(dict.fromkeys(dn_confirmed+[value for value in padded_dn\n                if _new_suffix_asset_candidates([value],endpoint_items)]))\n'''
assert old in s
s=s.replace(old,new,1)

SOURCE.write_text(s,encoding='utf-8')
print('Applied post-v95 padded complete endpoint-ID recovery.')
