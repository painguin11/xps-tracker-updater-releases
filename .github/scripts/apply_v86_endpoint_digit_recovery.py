from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v86_assets_and_edit.py')
src=APP.read_text(encoding='utf-8')

anchor="""def _rank_asset_candidates(observations, known_items, max_full_dist=3, max_number_dist=1):\n"""
helper=r'''def _asset_body_digits(value):
    """Return only the numeric body after an asset prefix (R2-335 -> 335)."""
    text=str(value or '').strip().upper()
    if '-' in text:
        tail=text.rsplit('-',1)[-1]
        match=re.match(r'(\d+)',tail)
        return match.group(1) if match else ''
    match=re.search(r'(\d+)(?:[A-Z]?)$',text)
    return match.group(1) if match else ''


def _endpoint_digit_tokens(cell_img):
    """Return numeric strings actually OCR-observed in one endpoint cell."""
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    out=[]
    for value in _ocr_digits(cell_img,False,fast_plain=False):
        token=re.sub(r'\D','',str(value or ''))
        if token and token not in out:
            out.append(token)
    return out


def _digit_token_matches_asset_body(token,body):
    """Allow only exact bodies or the 1-2 leading grid/prefix digits seen in scans."""
    if not token or not body:
        return False
    return token==body or (token.endswith(body) and 0 < len(token)-len(body) <= 2)


def _resolve_pipe_pair_from_endpoint_digits(up_cell,dn_cell,master_index):
    """Recover a damaged prefix only when both cells identify one existing pipe.

    The numeric body of each endpoint must be OCR-observed in its own PDF cell. The
    master can disambiguate EC/DN/R2 only when exactly one existing pipe satisfies
    both observations. This cannot create a new asset or supply an unobserved number.
    """
    up_tokens=_endpoint_digit_tokens(up_cell)
    dn_tokens=_endpoint_digit_tokens(dn_cell)
    if not up_tokens or not dn_tokens:
        return None
    matches={}
    for item in master_index.get('pipe_items',[]):
        up_body=_asset_body_digits(item.get('up'))
        dn_body=_asset_body_digits(item.get('down'))
        if (any(_digit_token_matches_asset_body(token,up_body) for token in up_tokens) and
                any(_digit_token_matches_asset_body(token,dn_body) for token in dn_tokens)):
            matches[item['row']]=item
    return next(iter(matches.values())) if len(matches)==1 else None


def _rank_asset_candidates(observations, known_items, max_full_dist=3, max_number_dist=1):
'''
if helper.split('\n\n\ndef _rank_asset_candidates',1)[0] not in src:
    if src.count(anchor)!=1:
        raise SystemExit('rank asset anchor not found exactly once')
    src=src.replace(anchor,helper)

old="""            up_obs=list(dict.fromkeys(up_obs+_ocr_known_r2_candidates(cut(up_box),endpoint_items,asset_format=asset_format)))\n            dn_obs=list(dict.fromkeys(dn_obs+_ocr_known_r2_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)))\n            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n        if not match:\n            # Escalate only uncertain endpoint cells to the slower OCR ensemble.\n"""
new="""            up_obs=list(dict.fromkeys(up_obs+_ocr_known_r2_candidates(cut(up_box),endpoint_items,asset_format=asset_format)))\n            dn_obs=list(dict.fromkeys(dn_obs+_ocr_known_r2_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)))\n            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n        if not match:\n            # If grid/prefix damage erased EC/DN/R2 but both endpoint numbers are\n            # still visible, accept a recovery only when those two OCR-observed\n            # numeric bodies identify exactly one existing master pipe.\n            digit_match=_resolve_pipe_pair_from_endpoint_digits(cut(up_box),cut(dn_box),master_index)\n            if digit_match:\n                match=digit_match; match_status='Matched'\n                up_obs=[match['up']]+up_obs; dn_obs=[match['down']]+dn_obs\n        if not match:\n            # Escalate only uncertain endpoint cells to the slower OCR ensemble.\n"""
if new not in src:
    if src.count(old)!=1:
        raise SystemExit('pair numeric fallback anchor not found exactly once')
    src=src.replace(old,new)

APP.write_text(src,encoding='utf-8')

reg=TEST.read_text(encoding='utf-8')
source_marker="""    "apply_manual_asset_edit(r,self.master_index,asset=vars['Asset'].get())",\n"""
source_add="""    "apply_manual_asset_edit(r,self.master_index,asset=vars['Asset'].get())",\n    'def _resolve_pipe_pair_from_endpoint_digits(',\n    'digit_match=_resolve_pipe_pair_from_endpoint_digits(cut(up_box),cut(dn_box),master_index)',\n"""
if "'def _resolve_pipe_pair_from_endpoint_digits('" not in reg:
    if reg.count(source_marker)!=1:
        raise SystemExit('v86 regression source marker not found exactly once')
    reg=reg.replace(source_marker,source_add)

append=r'''

# Prefix-loss recovery must use both endpoint cells and fail closed on ambiguity.
original_digit_tokens=xps._endpoint_digit_tokens
try:
    xps._endpoint_digit_tokens=lambda cell:list(cell)
    pair_a={'row':1,'expected':188.8,'pipe_id':'EC1826EC1817','up':'EC-1826','down':'EC-1817',
            'up_key':'EC1826','down_key':'EC1817'}
    pair_b={'row':2,'expected':390.5,'pipe_id':'R2335R2336','up':'R2-335','down':'R2-336',
            'up_key':'R2335','down_key':'R2336'}
    pair_c={'row':3,'expected':250.0,'pipe_id':'DN1826DN1900','up':'DN-1826','down':'DN-1900',
            'up_key':'DN1826','down_key':'DN1900'}
    digit_master={'pipe_items':[pair_a,pair_b,pair_c]}
    assert xps._resolve_pipe_pair_from_endpoint_digits(['1826','11826'],['1817'],digit_master)['row']==1
    assert xps._resolve_pipe_pair_from_endpoint_digits(['12335'],['12336'],digit_master)['row']==2
    assert xps._resolve_pipe_pair_from_endpoint_digits([],['1817'],digit_master) is None
    ambiguous={'pipe_items':[pair_a,dict(pair_a,row=4,up='DN-1826',down='DN-1817',up_key='DN1826',down_key='DN1817')]}
    assert xps._resolve_pipe_pair_from_endpoint_digits(['1826'],['1817'],ambiguous) is None
finally:
    xps._endpoint_digit_tokens=original_digit_tokens
'''
if 'Prefix-loss recovery must use both endpoint cells' not in reg:
    marker="\nprint('v86 asset OCR evidence + editable asset/node regression passed.')\n"
    if reg.count(marker)!=1:
        raise SystemExit('v86 regression print marker not found exactly once')
    reg=reg.replace(marker,append+marker)
TEST.write_text(reg,encoding='utf-8')
print('Applied pair-safe v86 endpoint digit recovery.')
