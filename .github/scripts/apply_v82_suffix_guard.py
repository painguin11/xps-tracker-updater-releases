from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v82_suffix_guard.py')
text=APP.read_text(encoding='utf-8')

marker='def _base_asset_key(value,known_items):\n'
if marker not in text:
    raise SystemExit('suffix helper insertion marker not found')
if 'def _confirmed_suffix_asset_candidates' not in text:
    helper=r'''def _confirmed_suffix_asset_candidates(cell_img,known_items):
    """Require a possible one-letter new-asset suffix to survive independent crops.

    A ruled table edge or neighboring stroke can occasionally be OCRed as a final
    letter (for example EC-1817 -> EC-1817A). New suffix assets are consequential,
    so the same suffix must be observed in at least two slightly different views
    of the untouched endpoint cell before it may drive NEW PIPE detection.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    width=cell_img.shape[1]
    views=[cell_img]
    for ratio in (.025,.045):
        pad=max(1,int(round(width*ratio)))
        if width>pad*2+8:
            views.append(cell_img[:,pad:width-pad])
    support={}
    for view in views:
        seen={asset_key(value) for value in _new_suffix_asset_candidates(
            _ocr_asset_candidates(view,fast_plain=True),known_items)}
        for key in seen:
            support[key]=support.get(key,0)+1
    return [canonical_asset_id(key) for key,count in support.items() if count>=2]


def _guard_unconfirmed_suffix_observations(observations,confirmed_suffixes,known_items):
    """Collapse an unconfirmed base+letter OCR artifact back to its known base ID."""
    confirmed={asset_key(value) for value in confirmed_suffixes}
    known={asset_key(value) for value in known_items}
    out=[]
    for raw in observations or []:
        suffixes=_new_suffix_asset_candidates([raw],known_items)
        if suffixes:
            suffix=suffixes[0]; key=asset_key(suffix)
            if key not in confirmed and key[:-1] in known:
                value=canonical_asset_id(key[:-1])
                if value not in out: out.append(value)
                continue
        if raw not in out: out.append(raw)
    return out


'''
    text=text.replace(marker,helper+marker,1)

old="""        if not match:
            # Escalate only uncertain endpoint cells to the slower OCR ensemble.
            up_obs=list(dict.fromkeys(up_obs+read_id(up_box,False)))
            dn_obs=list(dict.fromkeys(dn_obs+read_id(dn_box,False)))
            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)
        value_cell=cut(val_box,right_bleed=(kind=='cleaning'))
"""
new="""        if not match:
            # Escalate only uncertain endpoint cells to the slower OCR ensemble.
            up_obs=list(dict.fromkeys(up_obs+read_id(up_box,False)))
            dn_obs=list(dict.fromkeys(dn_obs+read_id(dn_box,False)))
            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)
        if kind=='pipe' and not match and match_status=='NEW PIPE':
            # A one-letter suffix can be a real new asset, but a table edge can
            # also create a stray final character. Require the suffix to survive
            # independent endpoint crops before allowing it to create a new pipe.
            up_confirmed=_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items)
            dn_confirmed=_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items)
            guarded_up=_guard_unconfirmed_suffix_observations(up_obs,up_confirmed,endpoint_items)
            guarded_dn=_guard_unconfirmed_suffix_observations(dn_obs,dn_confirmed,endpoint_items)
            if guarded_up!=up_obs or guarded_dn!=dn_obs:
                guarded_match,guarded_status=_resolve_pipe_pair(guarded_up,guarded_dn,master_index)
                if guarded_match:
                    up_obs,dn_obs=guarded_up,guarded_dn
                    match,match_status=guarded_match,guarded_status
        value_cell=cut(val_box,right_bleed=(kind=='cleaning'))
"""
if old not in text:
    raise SystemExit('pair resolver insertion block not found')
text=text.replace(old,new,1)
APP.write_text(text,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'def _confirmed_suffix_asset_candidates' in src
assert 'def _guard_unconfirmed_suffix_observations' in src
assert "for ratio in (.025,.045):" in src
assert 'if count>=2' in src
assert "if kind=='pipe' and not match and match_status=='NEW PIPE':" in src
assert '_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items)' in src
assert '_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items)' in src

# Exercise only the pure suffix-normalization helpers. Legitimate confirmed
# suffixes must survive; a lone suffix OCR artifact must collapse to the base.
tree=ast.parse(src)
names={'canonical_asset_id','asset_key','_new_suffix_asset_candidates','_guard_unconfirmed_suffix_observations'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<suffix-guard>','exec'),ns)
guard=ns['_guard_unconfirmed_suffix_observations']
known={'EC1817':'EC-1817','EC1801':'EC-1801'}
assert guard(['EC-1817A'],[],known)==['EC-1817']
assert guard(['EC-1817A'],['EC-1817A'],known)==['EC-1817A']
assert guard(['EC-1817'],[],known)==['EC-1817']
assert guard(['1EC1801'],[],known)==['1EC1801']

print('v82 new-suffix OCR corroboration regression passed.')
''',encoding='utf-8')

print('Applied v82 new-suffix OCR corroboration guard.')
