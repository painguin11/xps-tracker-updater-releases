from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v82_asset_format_profiles.py')
text=APP.read_text(encoding='utf-8')

# 1) Central, intentionally editable per-project format configuration.
const_marker="_PAGE_CACHE_FOLDER = ''\n"
if const_marker not in text:
    raise SystemExit('asset format config insertion marker not found')
if 'PROJECT_ASSET_FORMAT_RULES' not in text:
    config=r'''

# Asset-ID syntax is project-specific. Add a new named rule here, then map a
# future master profile to it in PROJECT_ASSET_FORMAT_RULES below. Recognition
# code for Pipe, Manhole, and Cleaning all uses this single configuration.
ASSET_FORMAT_RULES = {
    'reno_numeric': {
        'description': 'Legacy Reno asset IDs: digits only, no dash required',
        'search_pattern': r'(?<![A-Z0-9])(\d+)(?![A-Z0-9])',
        'full_pattern': r'\d+',
        'requires_dash': False,
    },
    'prefixed_dash_1_4_optional_suffix': {
        'description': 'Prefix + required dash + 1-4 digits + optional one-letter suffix',
        'search_pattern': r'(?<![A-Z0-9])([A-Z][A-Z0-9]{0,5})\s*-\s*(\d{1,4})([A-Z]?)(?![A-Z0-9])',
        'full_pattern': r'[A-Z][A-Z0-9]{0,5}-\d{1,4}[A-Z]?',
        'requires_dash': True,
    },
}

# Future project formats should be changed HERE rather than in individual OCR
# parsers. Unknown profiles deliberately keep the legacy tolerant behavior until
# a rule is assigned, so adding a project does not silently destroy its rows.
PROJECT_ASSET_FORMAT_RULES = {
    'reno': 'reno_numeric',
    'year15': 'prefixed_dash_1_4_optional_suffix',
    'phase2_year1': 'prefixed_dash_1_4_optional_suffix',
}
'''
    text=text.replace(const_marker,const_marker+config,1)

# 2) Shared helpers. These preserve actual printed-dash evidence before asset_key
# normalization removes punctuation.
helper_marker="def parse_float(s):\n"
if helper_marker not in text:
    raise SystemExit('asset format helper insertion marker not found')
if 'def _asset_format_rule(profile):' not in text:
    helper=r'''def _asset_format_rule(profile):
    rule_name=PROJECT_ASSET_FORMAT_RULES.get(str(profile or '').strip().lower())
    return ASSET_FORMAT_RULES.get(rule_name) if rule_name else None


def _profile_requires_asset_dash(profile):
    rule=_asset_format_rule(profile)
    return bool(rule and rule.get('requires_dash'))


def _printed_asset_tokens(text,profile):
    """Extract only asset tokens that satisfy this project's printed syntax.

    This runs before punctuation normalization. For the current B&C profiles a
    literal dash must therefore be present in OCR output; EC1817 cannot become a
    valid EC-1817 merely because canonical_asset_id knows how to insert a dash.
    """
    rule=_asset_format_rule(profile)
    if not rule:
        return []
    source=str(text or '').upper()
    out=[]
    for match in re.finditer(rule['search_pattern'],source):
        if rule.get('requires_dash'):
            groups=match.groups()
            value=f'{groups[0]}-{groups[1]}{groups[2] or ""}'
        else:
            value=match.group(1)
        value=value.upper()
        if re.fullmatch(rule['full_pattern'],value) and value not in out:
            out.append(value)
    return out


def _asset_value_matches_profile(value,profile):
    rule=_asset_format_rule(profile)
    if not rule:
        return True
    raw=str(value or '').strip().upper()
    if rule.get('requires_dash') and '-' not in raw:
        return False
    compact=re.sub(r'\s+','',raw)
    return bool(re.fullmatch(rule['full_pattern'],compact))


'''
    text=text.replace(helper_marker,helper+helper_marker,1)

# 3) Generic internal parser must support the valid shortest current ID DN-1.
old="match=re.fullmatch(r'([A-Z]{1,6})(\\d{2,8})([A-Z]?)',key)"
new="match=re.fullmatch(r'([A-Z]{1,6})(\\d{1,8})([A-Z]?)',key)"
if old not in text:
    raise SystemExit('_asset_id_parts digit-range marker not found')
text=text.replace(old,new,1)

# 4) Profile-aware OCR candidate extraction. If a profile has a configured rule,
# only text that visibly satisfies it may become an asset candidate.
old_sig="def _ocr_asset_candidates(cell_img, fast_plain=False):\n"
new_sig="def _ocr_asset_candidates(cell_img, fast_plain=False, profile=None):\n"
if old_sig not in text:
    raise SystemExit('_ocr_asset_candidates signature not found')
text=text.replace(old_sig,new_sig,1)

old_body="""            txt=cached_ocr_string(im,config=f'--psm {psm}').strip().replace('\\n',' ')
            if txt:
                out.extend(_ocr_id_text_variants(txt))
                out.extend(re.findall(r'\\d{2,7}',txt))
"""
new_body="""            txt=cached_ocr_string(im,config=f'--psm {psm}').strip().replace('\\n',' ')
            if txt:
                rule=_asset_format_rule(profile)
                if rule:
                    formatted=_printed_asset_tokens(txt,profile)
                    for token in formatted:
                        out.append(token)
                        out.extend(_ocr_id_text_variants(token))
                        if not rule.get('requires_dash'):
                            out.extend(re.findall(r'\\d+',token))
                else:
                    out.extend(_ocr_id_text_variants(txt))
                    out.extend(re.findall(r'\\d{2,7}',txt))
"""
if old_body not in text:
    raise SystemExit('_ocr_asset_candidates OCR body not found')
text=text.replace(old_body,new_body,1)

# 5) Keep the specialized known-R2 repair, but it may not repair a completely
# missing dash on a profile whose format requires a printed dash.
old_r2_sig="def _ocr_known_r2_candidates(cell_img, known_items):\n"
new_r2_sig="def _ocr_known_r2_candidates(cell_img, known_items, profile=None):\n"
if old_r2_sig not in text:
    raise SystemExit('_ocr_known_r2_candidates signature not found')
text=text.replace(old_r2_sig,new_r2_sig,1)
r2_marker="""            text=cached_ocr_string(
                image,
                config=(f'--psm {psm} '
                        '-c tessedit_char_whitelist=Rr2-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            ).strip()
            key=asset_key(text)
"""
r2_new="""            text=cached_ocr_string(
                image,
                config=(f'--psm {psm} '
                        '-c tessedit_char_whitelist=Rr2-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            ).strip()
            if _profile_requires_asset_dash(profile) and '-' not in text:
                continue
            key=asset_key(text)
"""
if r2_marker not in text:
    raise SystemExit('R2 dash evidence insertion marker not found')
text=text.replace(r2_marker,r2_new,1)

# 6) Suffix corroboration must use the same project-format filter.
old_confirm_sig="def _confirmed_suffix_asset_candidates(cell_img,known_items):\n"
new_confirm_sig="def _confirmed_suffix_asset_candidates(cell_img,known_items,profile=None):\n"
if old_confirm_sig not in text:
    raise SystemExit('confirmed suffix signature not found')
text=text.replace(old_confirm_sig,new_confirm_sig,1)
old_confirm_call="_ocr_asset_candidates(view,fast_plain=True),known_items)"
new_confirm_call="_ocr_asset_candidates(view,fast_plain=True,profile=profile),known_items)"
if old_confirm_call not in text:
    raise SystemExit('confirmed suffix OCR call not found')
text=text.replace(old_confirm_call,new_confirm_call,1)

# 7) Unresolved structural guard is profile-aware. For configured projects, valid
# asset syntax is mandatory even when a length or date was read.
old_keep_sig="def _keep_unresolved_pair_row(up_value,down_value,length_value,row_date):\n"
new_keep_sig="def _keep_unresolved_pair_row(up_value,down_value,length_value,row_date,profile=None):\n"
if old_keep_sig not in text:
    raise SystemExit('unresolved row helper signature not found')
text=text.replace(old_keep_sig,new_keep_sig,1)
old_keep_body="""    if length_value is not None or row_date:
        return True
    return bool(_asset_id_parts(up_value) and _asset_id_parts(down_value))
"""
new_keep_body="""    if _asset_format_rule(profile):
        return (_asset_value_matches_profile(up_value,profile) and
                _asset_value_matches_profile(down_value,profile))
    if length_value is not None or row_date:
        return True
    return bool(_asset_id_parts(up_value) and _asset_id_parts(down_value))
"""
if old_keep_body not in text:
    raise SystemExit('unresolved row helper body not found')
text=text.replace(old_keep_body,new_keep_body,1)

# 8) Pipe/Cleaning Year15 parser: every endpoint OCR path uses the project rule.
parser_marker="""    prepared=prepared or prepare_year15_pair_layout(page,master_index,kind)
    img=prepared['img']; h,w=img.shape[:2]; bands=prepared.get('bands',[]); table=prepared.get('table')
"""
parser_new="""    prepared=prepared or prepare_year15_pair_layout(page,master_index,kind)
    profile=master_index.get('profile','')
    img=prepared['img']; h,w=img.shape[:2]; bands=prepared.get('bands',[]); table=prepared.get('table')
"""
if parser_marker not in text:
    raise SystemExit('pair parser profile marker not found')
text=text.replace(parser_marker,parser_new,1)

old_read="cell=cut(box); obs=_ocr_asset_candidates(cell,fast_plain=fast)"
new_read="cell=cut(box); obs=_ocr_asset_candidates(cell,fast_plain=fast,profile=profile)"
if old_read not in text:
    raise SystemExit('pair read_id first OCR not found')
text=text.replace(old_read,new_read,1)
text=text.replace("obs+=_ocr_asset_candidates(cell[:max(1,int(ch*.62)),:],fast_plain=fast)",
                  "obs+=_ocr_asset_candidates(cell[:max(1,int(ch*.62)),:],fast_plain=fast,profile=profile)",1)
text=text.replace("obs+=_ocr_asset_candidates(cell[int(ch*.38):,:],fast_plain=fast)",
                  "obs+=_ocr_asset_candidates(cell[int(ch*.38):,:],fast_plain=fast,profile=profile)",1)

old_r2_up="_ocr_known_r2_candidates(cut(up_box),endpoint_items)"
old_r2_dn="_ocr_known_r2_candidates(cut(dn_box),endpoint_items)"
if old_r2_up not in text or old_r2_dn not in text:
    raise SystemExit('pair R2 calls not found')
text=text.replace(old_r2_up,"_ocr_known_r2_candidates(cut(up_box),endpoint_items,profile=profile)",1)
text=text.replace(old_r2_dn,"_ocr_known_r2_candidates(cut(dn_box),endpoint_items,profile=profile)",1)

old_suf_up="_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items)"
old_suf_dn="_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items)"
if old_suf_up not in text or old_suf_dn not in text:
    raise SystemExit('pair suffix calls not found')
text=text.replace(old_suf_up,"_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,profile=profile)",1)
text=text.replace(old_suf_dn,"_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items,profile=profile)",1)

# DN-1 is a valid positive asset signal.
old_signal="if len(re.findall(r'\\d',key))>=2:\n                return True"
new_signal="if len(re.findall(r'\\d',key))>=1:\n                return True"
if old_signal not in text:
    raise SystemExit('asset digit signal minimum not found')
text=text.replace(old_signal,new_signal,1)

old_keep_call="_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d)"
if old_keep_call not in text:
    raise SystemExit('pair unresolved keep call not found')
text=text.replace(old_keep_call,"_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,profile=profile)",1)

# 9) Year15/Phase2 manholes: both token and band fallbacks use the same profile.
manhole_marker="""def parse_year15_manholes(page, master_index, on_row=None, on_progress=None):
    img=_year15_oriented(page,'manholes'); h,w=img.shape[:2]
    known=master_index['manholes']
"""
manhole_new="""def parse_year15_manholes(page, master_index, on_row=None, on_progress=None):
    profile=master_index.get('profile','')
    img=_year15_oriented(page,'manholes'); h,w=img.shape[:2]
    known=master_index['manholes']
"""
if manhole_marker not in text:
    raise SystemExit('year15 manhole profile marker not found')
text=text.replace(manhole_marker,manhole_new,1)

old_token="""            raw=str(txt)
            if not re.search(r'\\d{3,6}',raw): continue
            item,status=_resolve_full_asset([raw],known)
            token_rows.append((y+hh//2,item,status,raw))
"""
new_token="""            raw=str(txt)
            formatted=_printed_asset_tokens(raw,profile)
            if not formatted: continue
            item,status=_resolve_full_asset(formatted,known)
            token_rows.append((y+hh//2,item,status,formatted[0]))
"""
if old_token not in text:
    raise SystemExit('year15 manhole token block not found')
text=text.replace(old_token,new_token,1)

old_band="observations=_ocr_asset_candidates(id_img); item,status=_resolve_full_asset(observations,known)"
new_band="observations=_ocr_asset_candidates(id_img,profile=profile); item,status=_resolve_full_asset(observations,known)"
if old_band not in text:
    raise SystemExit('year15 manhole band OCR call not found')
text=text.replace(old_band,new_band,1)

APP.write_text(text,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'ASSET_FORMAT_RULES = {' in src
assert "'reno': 'reno_numeric'" in src
assert "'year15': 'prefixed_dash_1_4_optional_suffix'" in src
assert "'phase2_year1': 'prefixed_dash_1_4_optional_suffix'" in src
assert 'Future project formats should be changed HERE' in src
assert "def _ocr_asset_candidates(cell_img, fast_plain=False, profile=None):" in src
assert "profile=master_index.get('profile','')" in src
assert "_ocr_known_r2_candidates(cut(up_box),endpoint_items,profile=profile)" in src
assert "_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,profile=profile)" in src
assert "_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,profile=profile)" in src
assert "observations=_ocr_asset_candidates(id_img,profile=profile)" in src

# Exercise the centralized pure format helpers.
tree=ast.parse(src)
names={'_asset_format_rule','_profile_requires_asset_dash','_printed_asset_tokens',
       '_asset_value_matches_profile','asset_key','_asset_id_parts'}
nodes=[]
for n in tree.body:
    if isinstance(n,(ast.Assign,ast.AnnAssign)):
        targets=[]
        if isinstance(n,ast.Assign): targets=[t.id for t in n.targets if isinstance(t,ast.Name)]
        elif isinstance(n.target,ast.Name): targets=[n.target.id]
        if any(t in {'ASSET_FORMAT_RULES','PROJECT_ASSET_FORMAT_RULES'} for t in targets): nodes.append(n)
    elif isinstance(n,ast.FunctionDef) and n.name in names:
        nodes.append(n)
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<asset-format>','exec'),ns)
tokens=ns['_printed_asset_tokens']; valid=ns['_asset_value_matches_profile']; parts=ns['_asset_id_parts']

# Current B&C project syntax: a literal dash is mandatory, 1-4 digits, optional one suffix.
for value in ('DN-1','DN-12','DN-1234','DN-1234A','EC-1817','R2-280','R2-1234A'):
    assert tokens(value,'year15')==[value], value
    assert valid(value,'phase2_year1'), value
for value in ('DN1','DN1234A','EC1817','R2280','EN','SUNAA','1234','DN-12345','DN-1234AB'):
    assert tokens(value,'year15')==[], value
    assert not valid(value,'year15'), value
assert tokens('  DN - 1  ','year15')==['DN-1']

# Legacy Reno remains numeric-only and does not inherit the B&C dash rule.
assert tokens('1234','reno')==['1234']
assert valid('1234','reno')
assert tokens('DN-1','reno')==[]
assert not valid('DN-1','reno')

# Generic internal parsing now permits the valid one-digit current asset number.
assert parts('DN-1') is not None

print('v82 centralized project asset-format regression passed.')
''',encoding='utf-8')

print('Applied centralized v82 project asset-format rules.')
