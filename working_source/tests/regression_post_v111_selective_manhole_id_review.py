"""Selective Manhole ID verification: strong exact OCR passes, questionable matches block.

This regression uses pure helper functions extracted from the production module.
It does not require Windows COM, Tkinter or customer PDF fixtures.
"""
from pathlib import Path
import ast
import re

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
source=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(source)
def asset_key(raw):
    return re.sub(r'[^A-Z0-9]','',str(raw or '').upper())

def canonical_asset_id(raw):
    return str(raw or '').strip().upper()

def new_suffix(observations,known):
    keys={asset_key(k) for k in known}
    return [raw for raw in observations if asset_key(raw)[:-1] in keys and
            asset_key(raw)[-1:].isalpha() and asset_key(raw) not in keys]

ns={'asset_key':asset_key,'canonical_asset_id':canonical_asset_id,
    '_new_suffix_asset_candidates':new_suffix}

def mark(record,reason):
    reasons=record.setdefault('_review_skip_reasons',[])
    if reason not in reasons: reasons.append(reason)
    record['skip_update']=True

def clear(record,reason):
    record['_review_skip_reasons']=[x for x in record.get('_review_skip_reasons',[]) if x!=reason]
    if not record.get('_review_skip_reasons') and not record.get('_field_review_reasons'):
        record['skip_update']=False
        return True
    return False

ns['_mark_field_review_block']=mark
ns['_clear_field_review_block']=clear
names=('MANHOLE_ID_REVIEW_REASON','_manhole_match_questionable',
       '_require_manhole_id_review','_confirm_manhole_id_review',
       '_resolve_manhole_manual_id')
for name in names:
    node=next(n for n in tree.body if
              (isinstance(n,ast.FunctionDef) and n.name==name) or
              (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)))
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

questionable=ns['_manhole_match_questionable']
known={'DN2002':{'asset':'DN-2002'},'DN2003':{'asset':'DN-2003'},'DN2012':{'asset':'DN-2012'}}
def row(sources,status='Matched',asset='DN-2002'):
    return {'kind':'Manhole','asset':asset,'status':status,
            '_manhole_id_sources':sources,'skip_update':False}

# Two independent exact views: no popup, master write remains eligible.
clear_match=row([['DN-2002'],['DN-2002']])
assert not questionable(clear_match,known),clear_match

# Master presence is never sufficient when one read is weak, fuzzy or numeric-only.
assert questionable(row([['DN-2002'],[]]),known)
assert questionable(row([['2002'],['DN-2002']]),known)
assert questionable(row([['DN-20O2'],['DN-20O2']]),known)
assert questionable(row([]),known)

# Two alternate real master IDs conflict: always review even if first one matches.
assert questionable(row([['DN-2002'],['DN-2003']]),known)
assert questionable(row([['DN-2002','DN-2003'],['DN-2002']]),known)
assert questionable(row([['DN-2003'],['DN-2003']]),known)

# New assets retain their existing manual approval path, not an extra popup.
assert not questionable(row([['DN-2002A']],status='NEW MANHOLE',asset='DN-2002A'),known)

# Questionable match must stay blocked until PDF confirmation.
suspect=row([['DN-2002'],['DN-2003']])
ns['_require_manhole_id_review'](suspect)
reason=ns['MANHOLE_ID_REVIEW_REASON']
assert suspect['skip_update'] and reason in suspect['_field_review_reasons']
assert reason in suspect['warnings']
ns['_confirm_manhole_id_review'](suspect)
assert suspect['_manhole_id_verified'] and not suspect['_field_review_reasons']
assert not suspect['skip_update']

# Manual correction must exactly match the entered full ID, never a close-by master.
item,status=ns['_resolve_manhole_manual_id']('DN-2002',known)
assert status=='Matched' and item is known['DN2002']
item,status=ns['_resolve_manhole_manual_id']('DN-2004',known)
assert item is None and status=='NOT MATCHED'
item,status=ns['_resolve_manhole_manual_id']('DN-2002A',known)
assert item is None and status=='NEW MANHOLE'

# Guard the actual extraction, dialog and write paths against accidental
# reintroduction of unconditional confirmation.
app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App')
methods={n.name:n for n in app.body if isinstance(n,ast.FunctionDef)}
calls=lambda node:{n.func.id for n in ast.walk(node)
                   if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
assert '_manhole_match_questionable' in calls(methods['commit_extracted_record'])
assert '_require_manhole_id_review' in calls(methods['commit_extracted_record'])
assert '_confirm_manhole_id_review' in calls(methods['edit_selected'])
manual=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=='apply_manual_asset_edit')
assert "known.get(asset_key(asset))" in ast.get_source_segment(source,manual)
assert '_manhole_id_review_required' in source
assert 'padded_candidates' in source and 'pass_observations' in source
assert 'source_observations' in source

print('post-v111 selective Manhole ID verification regression passed')
