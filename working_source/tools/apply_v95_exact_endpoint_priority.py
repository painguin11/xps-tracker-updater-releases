from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
s=path.read_text(encoding='utf-8')
start=s.index('def _digit_token_matches_asset_body')
end=s.index('\ndef _rank_asset_candidates',start)
replacement='''def _digit_token_asset_body_quality(token,body):
    """Rank one OCR-observed numeric token against one master asset body.

    Exact numeric-body evidence is strongest. A token with one or two extra
    leading digits remains usable as the existing grid/prefix-damage fallback,
    but it must never tie with an exact body match from another master row.
    """
    if not token or not body:
        return None
    if token==body:
        return 0
    if token.endswith(body):
        extra=len(token)-len(body)
        if 0 < extra <= 2:
            return extra
    return None


def _digit_token_matches_asset_body(token,body):
    """Compatibility predicate for tolerated numeric endpoint evidence."""
    return _digit_token_asset_body_quality(token,body) is not None


def _resolve_pipe_pair_from_endpoint_digits(up_cell,dn_cell,master_index,up_extra=None,dn_extra=None):
    """Recover a damaged prefix only when both cells identify one best pipe.

    Both numeric bodies must be OCR-observed from their own PDF cells. Exact body
    matches outrank the tolerated one/two-leading-digit grid-noise form. If two
    master rows have the same best evidence quality, recovery remains unresolved.
    This keeps true prefix ambiguity fail-closed while preventing an exact 1911 /
    1912 observation from tying with shorter EC-11 / EC-12 bodies.
    """
    up_tokens=list(dict.fromkeys(_endpoint_digit_tokens(up_cell)+list(up_extra or [])))
    dn_tokens=list(dict.fromkeys(_endpoint_digit_tokens(dn_cell)+list(dn_extra or [])))
    if not up_tokens or not dn_tokens:
        return None
    matches={}
    for item in master_index.get('pipe_items',[]):
        up_body=_asset_body_digits(item.get('up'))
        dn_body=_asset_body_digits(item.get('down'))
        up_quality=[_digit_token_asset_body_quality(token,up_body) for token in up_tokens]
        dn_quality=[_digit_token_asset_body_quality(token,dn_body) for token in dn_tokens]
        up_quality=[q for q in up_quality if q is not None]
        dn_quality=[q for q in dn_quality if q is not None]
        if not up_quality or not dn_quality:
            continue
        matches[item['row']]=(min(up_quality)+min(dn_quality),item)
    if not matches:
        return None
    best_score=min(score for score,_item in matches.values())
    winners=[item for score,item in matches.values() if score==best_score]
    return winners[0] if len(winners)==1 else None

'''
path.write_text(s[:start]+replacement+s[end+1:],encoding='utf-8')
print('Applied v95 exact endpoint-body priority fix.')
