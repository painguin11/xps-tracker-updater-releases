from pathlib import Path
import re

app = Path('working_source/app/reno_scan_updater.py')
src = app.read_text(encoding='utf-8')

old = '''def _authoritative_asset_candidates(observations,known_items):
    """Keep complete observed IDs whose prefix is already valid for this project."""
    prefixes={parts[0] for key in known_items if (parts:=_asset_id_parts(key))}
    out=[]
    for raw in observations:
        parts=_asset_id_parts(raw)
        if parts and parts[0] in prefixes:
            value=canonical_asset_id(''.join(parts))
            if value not in out: out.append(value)
    return out
'''
new = '''def _authoritative_asset_candidates(observations,known_items):
    """Keep complete observed IDs whose prefix is already valid for this project."""
    prefixes={parts[0] for key in known_items if (parts:=_asset_id_parts(key))}
    out=[]
    for raw in observations:
        parts=_asset_id_parts(raw)
        if not parts:
            continue
        prefix,number,suffix=parts
        # A left table rule can attach one narrow OCR glyph to an otherwise
        # complete printed endpoint (for example DN-1912 -> IDN-1912). Repair
        # only I/L plus a prefix that is already established by the master.
        if prefix not in prefixes and len(prefix)>1 and prefix[0] in ('I','L') and prefix[1:] in prefixes:
            prefix=prefix[1:]
        if prefix in prefixes:
            value=canonical_asset_id(f'{prefix}{number}{suffix}')
            if value not in out: out.append(value)
    return out
'''
assert src.count(old) == 1, 'authoritative asset candidate block not found exactly once'
src = src.replace(old, new, 1)

old = """    if _new_pipe_base_item(up_observations,dn_observations,master_index):
        return None,'NEW PIPE'
    # Pair matching can tolerate more surrounding OCR junk because both endpoints
"""
new = """    if _new_pipe_base_item(up_observations,dn_observations,master_index):
        return None,'NEW PIPE'
    # Complete project-valid IDs are authoritative evidence from the PDF. If both
    # endpoint cells contain them but they do not form an existing/new-suffix pair,
    # preserve the printed IDs for Add/Ignore review instead of silently fuzzy-
    # mapping them to a nearby master pipe.
    if up_full and dn_full:
        return None,'NOT MATCHED'
    # Pair matching can tolerate more surrounding OCR junk because both endpoints
"""
assert src.count(old) == 1, 'pipe-pair fuzzy guard insertion point not found exactly once'
src = src.replace(old, new, 1)

old = "    if kind=='pipes' and ('survey' in compact or ('length' in compact and 'scheduled' not in compact)): return 'value'"
new = """    if kind=='pipes' and ('survey' in compact or 'survev' in compact or
                          (('length' in compact or 'leneth' in compact) and 'scheduled' not in compact)): return 'value'"""
assert src.count(old) == 1, 'pipe header role line not found exactly once'
src = src.replace(old, new, 1)

src, n = re.subn(r"^APP_VERSION\s*=\s*['\"]88['\"]", "APP_VERSION = '89'", src, count=1, flags=re.M)
assert n == 1, 'APP_VERSION 88 marker not found exactly once'
app.write_text(src, encoding='utf-8')

updater = Path('working_source/app/xps_update.py')
usrc = updater.read_text(encoding='utf-8')
usrc, n = re.subn(r'^CURRENT_VERSION\s*=\s*[\"\']88[\"\']', 'CURRENT_VERSION = "89"', usrc, count=1, flags=re.M)
assert n == 1, 'CURRENT_VERSION 88 marker not found exactly once'
updater.write_text(usrc, encoding='utf-8')

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')
if '## v89' not in text:
    text += ('\n\n## v89\n\n'
             '- Verifies Manhole work orders against the user-confirmed survey count shown in the Description of work performed crop.\n'
             '- Uses only the final continuation page total for multi-page Pipe/Cleaning total verification.\n'
             '- Adds Add to Master / Ignore / Back to Summary decisions for unresolved Pipe and Manhole rows at Update Master time.\n'
             '- Limits automatic MSA combination to exactly two duplicate Pipe rows; three or more remain blocked for ID review.\n'
             '- Adds PDF field previews to Trouble Ticket editing and preserves all existing continuation, exact-number, and partial-page safeguards.\n'
             '- Preserves complete printed endpoint pairs that are absent from the master instead of fuzzy-mapping them to nearby assets.\n'
             '- Recovers a narrow left-grid OCR artifact such as IDN-1912 back to the established DN prefix, and recognizes common OCR variants of Length Surveyed headers.\n')
    readme.write_text(text, encoding='utf-8')

regression = Path('working_source/tests/regression_v89_printed_pair_identity.py')
regression.write_text(r'''from pathlib import Path
import ast
import re

source_path=Path(__file__).resolve().parents[1] / 'app' / 'reno_scan_updater.py'
source=source_path.read_text(encoding='utf-8')
tree=ast.parse(source)
needed={
    'canonical_asset_id','asset_key','asset_number','_ocr_id_text_variants','_edit_distance',
    '_rank_asset_candidates','_asset_id_parts','_authoritative_asset_candidates',
    '_new_suffix_asset_candidates','_endpoint_base_options','_new_pipe_base_item',
    '_resolve_pipe_pair','_header_role'
}
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in needed]
found={node.name for node in nodes}
missing=needed-found
assert not missing, f'missing source functions: {sorted(missing)}'
module=ast.Module(body=nodes,type_ignores=[])
ast.fix_missing_locations(module)
ns={'re':re}
exec(compile(module,str(source_path),'exec'),ns)

pipe_a={'row':10,'up':'DN-797','down':'DN-1763','up_key':'DN797','down_key':'DN1763','pipe_id':'P-A','expected':40}
pipe_b={'row':11,'up':'DN-1911','down':'DN-1912','up_key':'DN1911','down_key':'DN1912','pipe_id':'P-B','expected':296}
master={
    'pipe_items':[pipe_a,pipe_b],
    'pipes':{('DN797','DN1763'):pipe_a,('DN1911','DN1912'):pipe_b},
    'manholes':{}
}

item,status=ns['_resolve_pipe_pair'](['DN-797'],['DN-1763'],master)
assert item is pipe_a and status=='Matched', (item,status)

item,status=ns['_resolve_pipe_pair'](['DN-777'],['DN-1762'],master)
assert item is None and status=='NOT MATCHED', (item,status)

known={'DN1911':'DN-1911','DN1912':'DN-1912'}
repaired=ns['_authoritative_asset_candidates'](['IDN-1912'],known)
assert repaired==['DN-1912'], repaired
item,status=ns['_resolve_pipe_pair'](['DN-1911'],['IDN-1912'],master)
assert item is pipe_b and status=='Matched', (item,status)

assert ns['_header_role']('ilenethsurveved','pipes')=='value'
assert ns['_header_role']('lengthsurveyed','pipes')=='value'
print('v89 printed-pair identity, grid-prefix recovery, and header OCR regression passed.')
''', encoding='utf-8')

print('Applied v89 parser safeguards, version bump, README notes, and regression.')
