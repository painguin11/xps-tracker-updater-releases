from pathlib import Path
APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v86_asset_nodes.py')
s=APP.read_text(encoding='utf-8')

# 1) Generic pair-safe numeric endpoint recovery after the existing R2-specific helper.
anchor="""def _rank_asset_candidates(observations, known_items, max_full_dist=3, max_number_dist=1):\n"""
helper=r'''def _asset_body_digits(value):
    """Return only the numeric body after the asset prefix (R2-335 -> 335)."""
    text=str(value or '').strip().upper()
    if '-' in text:
        tail=text.rsplit('-',1)[-1]
        match=re.match(r'(\d+)',tail)
        return match.group(1) if match else ''
    match=re.search(r'(\d+)(?:[A-Z]?)$',text)
    return match.group(1) if match else ''


def _endpoint_digit_tokens(cell_img):
    """Return numeric strings visibly OCR-observed in one endpoint cell."""
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    out=[]
    for value in _ocr_digits(cell_img,False,fast_plain=False):
        token=re.sub(r'\D','',str(value or ''))
        if token and token not in out: out.append(token)
    return out


def _digit_token_matches_asset_body(token,body):
    if not token or not body: return False
    return token==body or (token.endswith(body) and 0 < len(token)-len(body) <= 2)


def _resolve_pipe_pair_from_endpoint_digits(up_cell,dn_cell,master_index):
    """Resolve damaged prefixes only when cell evidence identifies one master pipe.

    Both endpoint numeric bodies must be OCR-observed in their own cells. The master
    may disambiguate a damaged prefix, but it never supplies a missing measurement or
    invents a new asset. One/two extra leading digits are tolerated only for the
    prefix/grid artifacts seen on these ruled reports (11826 -> 1826, 12335 -> 335).
    """
    up_tokens=_endpoint_digit_tokens(up_cell); dn_tokens=_endpoint_digit_tokens(dn_cell)
    if not up_tokens or not dn_tokens: return None
    matches={}
    for item in master_index.get('pipe_items',[]):
        up_body=_asset_body_digits(item.get('up')); dn_body=_asset_body_digits(item.get('down'))
        if (any(_digit_token_matches_asset_body(token,up_body) for token in up_tokens) and
                any(_digit_token_matches_asset_body(token,dn_body) for token in dn_tokens)):
            matches[item['row']]=item
    return next(iter(matches.values())) if len(matches)==1 else None


def _rank_asset_candidates(observations, known_items, max_full_dist=3, max_number_dist=1):
'''
if s.count(anchor)!=1: raise SystemExit('rank asset anchor not found exactly once')
s=s.replace(anchor,helper)

old="""            up_obs=list(dict.fromkeys(up_obs+_ocr_known_r2_candidates(cut(up_box),endpoint_items,asset_format=asset_format)))\n            dn_obs=list(dict.fromkeys(dn_obs+_ocr_known_r2_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)))\n            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n        if not match:\n            # Escalate only uncertain endpoint cells to the slower OCR ensemble.\n"""
new="""            up_obs=list(dict.fromkeys(up_obs+_ocr_known_r2_candidates(cut(up_box),endpoint_items,asset_format=asset_format)))\n            dn_obs=list(dict.fromkeys(dn_obs+_ocr_known_r2_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)))\n            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n        if not match:\n            # Prefix/grid damage can leave clean endpoint numbers while losing EC/DN/R2.\n            # Accept this only when both cells' OCR-observed numeric bodies identify\n            # exactly one existing master pipe.\n            digit_match=_resolve_pipe_pair_from_endpoint_digits(cut(up_box),cut(dn_box),master_index)\n            if digit_match:\n                match=digit_match; match_status='Matched'\n                up_obs=[match['up']]+up_obs; dn_obs=[match['down']]+dn_obs\n        if not match:\n            # Escalate only uncertain endpoint cells to the slower OCR ensemble.\n"""
if s.count(old)!=1: raise SystemExit('pair fallback anchor not found exactly once')
s=s.replace(old,new)

# 2) Store exact endpoint/asset image crops for Edit Selected.
old="""        rec['_field_previews']={\n            'activity_value':value_cell.copy() if getattr(value_cell,'size',0) else None,\n            'date':date_cell.copy() if getattr(date_cell,'size',0) else None,\n        }\n"""
new="""        upstream_preview=cut(up_box); downstream_preview=cut(dn_box)\n        rec['_field_previews']={\n            'upstream':upstream_preview.copy() if getattr(upstream_preview,'size',0) else None,\n            'downstream':downstream_preview.copy() if getattr(downstream_preview,'size',0) else None,\n            'activity_value':value_cell.copy() if getattr(value_cell,'size',0) else None,\n            'date':date_cell.copy() if getattr(date_cell,'size',0) else None,\n        }\n"""
if s.count(old)!=1: raise SystemExit('pair preview anchor not found exactly once')
s=s.replace(old,new)

old="""            rec['_field_previews']={'date':date_preview.copy() if getattr(date_preview,'size',0) else None}\n"""
new="""            asset_preview=img[max(0,int(yc)-preview_half):min(h,int(yc)+preview_half),0:int(w*.40)]\n            rec['_field_previews']={\n                'asset':asset_preview.copy() if getattr(asset_preview,'size',0) else None,\n                'date':date_preview.copy() if getattr(date_preview,'size',0) else None}\n"""
if s.count(old)!=1: raise SystemExit('manhole token preview anchor not found exactly once')
s=s.replace(old,new)

old="""        rec['_field_previews']={'date':date_img.copy() if getattr(date_img,'size',0) else None}\n"""
new="""        rec['_field_previews']={\n            'asset':id_img.copy() if getattr(id_img,'size',0) else None,\n            'date':date_img.copy() if getattr(date_img,'size',0) else None}\n"""
if s.count(old)!=1: raise SystemExit('manhole grid preview anchor not found exactly once')
s=s.replace(old,new)

old="""        for key in ('activity_value','date'):\n            field_pages.setdefault(key,[page_number])\n"""
new="""        for key in ('upstream','downstream','asset','activity_value','date'):\n            field_pages.setdefault(key,[page_number])\n"""
if s.count(old)!=1: raise SystemExit('field pages anchor not found exactly once')
s=s.replace(old,new)

# 3) Make node/asset identity editable in the same preview dialog.
old="""        fields=[('Activity Value','activity_value'),('Date','date'),('W/O','wo'),('Truck','truck'),('Operator','operator')]; vars={}\n        values=[('' if r['video_length'] is None else str(r['video_length'])),fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n"""
new="""        if r.get('kind') in ('Pipe','Cleaning'):\n            fields=[('Upstream Node','upstream'),('Downstream Node','downstream'),('Activity Value','activity_value'),\n                    ('Date','date'),('W/O','wo'),('Truck','truck'),('Operator','operator')]\n            values=[r.get('up',''),r.get('down',''),('' if r['video_length'] is None else str(r['video_length'])),\n                    fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n        else:\n            fields=[('Asset','asset'),('Date','date'),('W/O','wo'),('Truck','truck'),('Operator','operator')]\n            values=[r.get('asset',''),fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n        vars={}\n"""
if s.count(old)!=1: raise SystemExit('edit field anchor not found exactly once')
s=s.replace(old,new)

old="""                old_length=r.get('video_length')\n                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())\n                if r.get('kind') in ('Pipe','Cleaning') and r.get('video_length') is not None and not _valid_row_length_value(r.get('video_length')):\n                    raise ValueError(f'Individual activity length must be greater than 0 and no more than {MAX_ROW_LENGTH:g} ft.')\n                if r.get('kind')=='Cleaning' and old_length!=r.get('video_length'):\n                    r['_length_user_edited']=True\n                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()\n"""
new="""                old_length=r.get('video_length')\n                if r.get('kind') in ('Pipe','Cleaning'):\n                    r['up']=canonical_asset_id(vars['Upstream Node'].get())\n                    r['down']=canonical_asset_id(vars['Downstream Node'].get())\n                    if not r['up'] or not r['down']:\n                        raise ValueError('Upstream Node and Downstream Node are required.')\n                    r['video_length']=None if not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())\n                    if r.get('video_length') is not None and not _valid_row_length_value(r.get('video_length')):\n                        raise ValueError(f'Individual activity length must be greater than 0 and no more than {MAX_ROW_LENGTH:g} ft.')\n                    match,match_status=_resolve_pipe_pair([r['up']],[r['down']],getattr(self,'master_index',{}) or {})\n                    if match:\n                        r['asset']=match.get('pipe_id',''); r['master_length']=match.get('expected')\n                        r['status']='Matched'\n                        if 'DUPLICATE IN PDF' not in r.get('warnings',[]): r.pop('skip_update',None)\n                    else:\n                        r['asset']=''; r['master_length']=None; r['status']=match_status or 'NOT MATCHED'; r['skip_update']=True\n                    suffix=(f\"  (pipe {r.get('asset')})\" if r.get('asset') else '')\n                    r['display_asset']=f\"{r['up']} -> {r['down']}\"+suffix\n                    r['display_asset_base']=r['display_asset']\n                    if old_length!=r.get('video_length'): r['_length_user_edited']=True\n                else:\n                    r['asset']=canonical_asset_id(vars['Asset'].get())\n                    if not r['asset']: raise ValueError('Asset is required.')\n                    item,status=_resolve_full_asset([r['asset']],(getattr(self,'master_index',{}) or {}).get('manholes',{}))\n                    r['asset_key']=item.get('asset_key') if item else asset_key(r['asset'])\n                    if item:\n                        r['asset']=item.get('asset') or r['asset']; r['status']='Matched'\n                        if 'DUPLICATE IN PDF' not in r.get('warnings',[]): r.pop('skip_update',None)\n                    else:\n                        r['status']=status or 'NOT MATCHED'; r['skip_update']=True\n                    r['display_asset']=r['asset']\n                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()\n"""
if s.count(old)!=1: raise SystemExit('edit save anchor not found exactly once')
s=s.replace(old,new)

APP.write_text(s,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
for required in (
    'def _resolve_pipe_pair_from_endpoint_digits(',
    "digit_match=_resolve_pipe_pair_from_endpoint_digits(cut(up_box),cut(dn_box),master_index)",
    "'upstream':upstream_preview.copy()",
    "'downstream':downstream_preview.copy()",
    "'asset':asset_preview.copy()",
    "fields=[('Upstream Node','upstream'),('Downstream Node','downstream')",
    "fields=[('Asset','asset'),('Date','date')",
    "r['up']=canonical_asset_id(vars['Upstream Node'].get())",
    "r['down']=canonical_asset_id(vars['Downstream Node'].get())",
    "match,match_status=_resolve_pipe_pair([r['up']],[r['down']]",
):
    assert required in src, required

tree=ast.parse(src)
names={'_asset_body_digits','_digit_token_matches_asset_body','_resolve_pipe_pair_from_endpoint_digits'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v86-pair-digits>','exec'),ns)
ns['_endpoint_digit_tokens']=lambda cell: list(cell)
resolve=ns['_resolve_pipe_pair_from_endpoint_digits']
master={'pipe_items':[
    {'row':1,'up':'EC-1826','down':'EC-1817'},
    {'row':2,'up':'DN-1826','down':'DN-1900'},
    {'row':3,'up':'R2-335','down':'R2-336'},
]}
assert resolve(['1826','11826'],['1817'],master)['row']==1
assert resolve(['12335'],['12336'],master)['row']==3
assert resolve([],['1817'],master) is None
amb={'pipe_items':[{'row':1,'up':'EC-1826','down':'EC-1817'},
                   {'row':2,'up':'DN-1826','down':'DN-1817'}]}
assert resolve(['1826'],['1817'],amb) is None
print('v86 asset/node edit and pair-safe endpoint recovery regression passed.')
''',encoding='utf-8')
print('Applied v86 asset/node editing and endpoint OCR recovery patch.')
