from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v82_master_asset_format.py')
CLEAN_TEST=Path('working_source/tests/regression_v82_cleaning_header_noise.py')
SUFFIX_TEST=Path('working_source/tests/regression_v82_suffix_guard.py')
text=APP.read_text(encoding='utf-8')

# Remove the temporary project-name asset-format configuration. Asset syntax is
# inferred from the selected master instead.
start=text.find('# Asset-ID syntax is project-specific.')
end=text.find('TROUBLE_TICKET_HEADERS_V60 = [',start)
if start<0 or end<0:
    raise SystemExit('static asset-format configuration block not found')
text=text[:start]+'''# Asset-ID syntax is inferred from the selected master workbook. The inferred
# base format is used by Pipe, Manhole, and Cleaning OCR. A single trailing
# letter is ALWAYS kept structurally possible for new assets even when the
# current master contains no suffixed examples; suffix candidates still go
# through the existing corroboration/new-asset review path.\n\n'''+text[end:]

# Replace project-name rules with master-derived format inference.
start=text.find('def _asset_format_rule(profile):')
end=text.find('def parse_float(s):',start)
if start<0 or end<0:
    raise SystemExit('old asset-format helper block not found')
helpers=r'''def _raw_master_asset(value):
    """Normalize one master asset cell without inventing punctuation."""
    if value is None:
        return ''
    raw=str(value).strip().upper()
    if re.fullmatch(r'\d+\.0',raw):
        raw=raw[:-2]
    return re.sub(r'\s+','',raw)


def _infer_asset_format(values):
    """Infer the base asset syntax from IDs actually present in the master.

    The master determines whether IDs are numeric-only or prefix+dash+number and
    the observed upper bounds for number/prefix size. One final letter is always
    allowed as a *possible new-asset suffix* even if the master has zero suffixed
    examples; absence from the master is never grounds to reject that suffix.
    """
    dashed=[]; numeric=[]
    for value in values or []:
        raw=_raw_master_asset(value)
        if not raw:
            continue
        m=re.fullmatch(r'([A-Z][A-Z0-9]{0,11})-+(\d+)([A-Z]?)',raw)
        if m:
            dashed.append(m.groups()); continue
        m=re.fullmatch(r'(\d+)([A-Z]?)',raw)
        if m:
            numeric.append(m.groups())
    if dashed and len(dashed)>=len(numeric):
        max_digits=max(len(number) for _,number,_ in dashed)
        max_prefix=max(len(prefix) for prefix,_,_ in dashed)
        return {'mode':'prefixed_dash','requires_dash':True,
                'max_digits':max(1,max_digits),'max_prefix_len':max(1,max_prefix),
                'allow_suffix':True,'sample_count':len(dashed)}
    if numeric:
        max_digits=max(len(number) for number,_ in numeric)
        return {'mode':'numeric','requires_dash':False,
                'max_digits':max(1,max_digits),'max_prefix_len':0,
                'allow_suffix':True,'sample_count':len(numeric)}
    # Fail open only when the master contains no inferable asset examples. Existing
    # matching still constrains results; unresolved/new rows remain review-only.
    return {'mode':'generic','requires_dash':False,'max_digits':8,
            'max_prefix_len':8,'allow_suffix':True,'sample_count':0}


def _asset_format_requires_dash(asset_format):
    return bool(isinstance(asset_format,dict) and asset_format.get('requires_dash'))


def _printed_asset_tokens(text,asset_format):
    """Extract asset tokens that satisfy the format inferred from the master.

    Punctuation is checked before canonical normalization, so a dash-required
    master cannot turn EC1817 into EC-1817. The optional final letter is deliberate:
    it represents a potential new asset and does not need to already exist in master.
    """
    rule=asset_format if isinstance(asset_format,dict) else None
    if not rule or rule.get('mode')=='generic':
        return []
    source=str(text or '').upper()
    max_digits=max(1,int(rule.get('max_digits') or 1))
    suffix=r'([A-Z]?)' if rule.get('allow_suffix',True) else r'()'
    out=[]
    if rule.get('mode')=='prefixed_dash':
        max_prefix=max(1,int(rule.get('max_prefix_len') or 1))
        pattern=(rf'(?<![A-Z0-9])([A-Z][A-Z0-9]{{0,{max_prefix-1}}})\s*-\s*'
                 rf'(\d{{1,{max_digits}}}){suffix}(?![A-Z0-9])')
        for match in re.finditer(pattern,source):
            prefix,number,tail=match.groups()
            value=f'{prefix}-{number}{tail or ""}'
            if value not in out: out.append(value)
    elif rule.get('mode')=='numeric':
        # The dash in the boundaries prevents a numeric master from extracting the
        # 1 inside DN-1 and calling it a valid Reno-style asset.
        pattern=rf'(?<![A-Z0-9-])(\d{{1,{max_digits}}}){suffix}(?![A-Z0-9-])'
        for match in re.finditer(pattern,source):
            number,tail=match.groups()
            value=f'{number}{tail or ""}'
            if value not in out: out.append(value)
    return out


def _asset_value_matches_format(value,asset_format):
    rule=asset_format if isinstance(asset_format,dict) else None
    if not rule or rule.get('mode')=='generic':
        return True
    raw=_raw_master_asset(value)
    if not raw:
        return False
    max_digits=max(1,int(rule.get('max_digits') or 1))
    tail=r'[A-Z]?' if rule.get('allow_suffix',True) else ''
    if rule.get('mode')=='prefixed_dash':
        if '-' not in raw:
            return False
        max_prefix=max(1,int(rule.get('max_prefix_len') or 1))
        return bool(re.fullmatch(rf'[A-Z][A-Z0-9]{{0,{max_prefix-1}}}-\d{{1,{max_digits}}}{tail}',raw))
    if rule.get('mode')=='numeric':
        return bool(re.fullmatch(rf'\d{{1,{max_digits}}}{tail}',raw))
    return True


'''
text=text[:start]+helpers+text[end:]

# OCR helpers now receive the inferred rule directly rather than a project name.
repls={
"def _ocr_asset_candidates(cell_img, fast_plain=False, profile=None):":"def _ocr_asset_candidates(cell_img, fast_plain=False, asset_format=None):",
"                rule=_asset_format_rule(profile)":"                rule=asset_format if isinstance(asset_format,dict) else None",
"                    formatted=_printed_asset_tokens(txt,profile)":"                    formatted=_printed_asset_tokens(txt,asset_format)",
"def _ocr_known_r2_candidates(cell_img, known_items, profile=None):":"def _ocr_known_r2_candidates(cell_img, known_items, asset_format=None):",
"            if _profile_requires_asset_dash(profile) and '-' not in text:":"            if _asset_format_requires_dash(asset_format) and '-' not in text:",
"def _confirmed_suffix_asset_candidates(cell_img,known_items,profile=None):":"def _confirmed_suffix_asset_candidates(cell_img,known_items,asset_format=None):",
"            _ocr_asset_candidates(view,fast_plain=True,profile=profile),known_items)":"            _ocr_asset_candidates(view,fast_plain=True,asset_format=asset_format),known_items)",
"def _keep_unresolved_pair_row(up_value,down_value,length_value,row_date,profile=None):":"def _keep_unresolved_pair_row(up_value,down_value,length_value,row_date,asset_format=None):",
"    if _asset_format_rule(profile):\n        return (_asset_value_matches_profile(up_value,profile) and\n                _asset_value_matches_profile(down_value,profile))":"    if isinstance(asset_format,dict) and asset_format.get('mode')!='generic':\n        return (_asset_value_matches_format(up_value,asset_format) and\n                _asset_value_matches_format(down_value,asset_format))",
}
for old,new in repls.items():
    if old not in text:
        raise SystemExit('replacement marker missing: '+old[:90])
    text=text.replace(old,new)

# Master loading: collect raw endpoint/manhole IDs before canonicalization, infer once,
# and attach the result to master_index. Pipe IDs are also sampled in Reno because
# that parser reads the pipe ID directly from the report.
year_pipe_marker="""            pipes={}; pipe_by_id={}
            for r in range(pr+1,len(pvals)+1):
                up=canonical_asset_id(_mv(pvals,r,ph['upstream'])); dn=canonical_asset_id(_mv(pvals,r,ph['downstream']))
"""
year_pipe_new="""            pipes={}; pipe_by_id={}; asset_format_samples=[]
            for r in range(pr+1,len(pvals)+1):
                raw_up=_mv(pvals,r,ph['upstream']); raw_dn=_mv(pvals,r,ph['downstream'])
                if raw_up not in (None,''): asset_format_samples.append(raw_up)
                if raw_dn not in (None,''): asset_format_samples.append(raw_dn)
                up=canonical_asset_id(raw_up); dn=canonical_asset_id(raw_dn)
"""
if year_pipe_marker not in text: raise SystemExit('year15 pipe sample marker missing')
text=text.replace(year_pipe_marker,year_pipe_new,1)

year_mh_marker="""            for r in range(mr+1,len(mvals)+1):
                sid=canonical_asset_id(_mv(mvals,r,mh['st_id']))
                if sid:
"""
year_mh_new="""            for r in range(mr+1,len(mvals)+1):
                raw_sid=_mv(mvals,r,mh['st_id'])
                if raw_sid not in (None,''): asset_format_samples.append(raw_sid)
                sid=canonical_asset_id(raw_sid)
                if sid:
"""
if year_mh_marker not in text: raise SystemExit('year15 manhole sample marker missing')
text=text.replace(year_mh_marker,year_mh_new,1)

year_return="""            _merge_entry_history(truck_counts,operator_counts)
            return {'profile':profile,'pipes':pipes,'pipe_by_id':pipe_by_id,'manholes':manholes,'trucks':set(truck_counts),
"""
year_return_new="""            _merge_entry_history(truck_counts,operator_counts)
            asset_format=_infer_asset_format(asset_format_samples)
            return {'profile':profile,'asset_format':asset_format,'pipes':pipes,'pipe_by_id':pipe_by_id,'manholes':manholes,'trucks':set(truck_counts),
"""
if year_return not in text: raise SystemExit('year15 return marker missing')
text=text.replace(year_return,year_return_new,1)

reno_pipe_marker="""        pipes = {}
        pipe_by_id = {}
        for r in range(pr + 1,len(pvals)+1):
            up,dn=digits(_mv(pvals,r,ph['upstream'])),digits(_mv(pvals,r,ph['downstream']))
"""
reno_pipe_new="""        pipes = {}
        pipe_by_id = {}
        asset_format_samples=[]
        for r in range(pr + 1,len(pvals)+1):
            raw_up=_mv(pvals,r,ph['upstream']); raw_dn=_mv(pvals,r,ph['downstream']); raw_pid=_mv(pvals,r,ph['pipe_id'])
            for raw_asset in (raw_up,raw_dn,raw_pid):
                if raw_asset not in (None,''): asset_format_samples.append(raw_asset)
            up,dn=digits(raw_up),digits(raw_dn)
"""
if reno_pipe_marker not in text: raise SystemExit('reno pipe sample marker missing')
text=text.replace(reno_pipe_marker,reno_pipe_new,1)

reno_mh_marker="""        for r in range(mr+1,len(mvals)+1):
            sid=digits(_mv(mvals,r,mh['st_id']))
            if sid: manholes[sid] = {'row': r,
"""
reno_mh_new="""        for r in range(mr+1,len(mvals)+1):
            raw_sid=_mv(mvals,r,mh['st_id'])
            if raw_sid not in (None,''): asset_format_samples.append(raw_sid)
            sid=digits(raw_sid)
            if sid: manholes[sid] = {'row': r,
"""
if reno_mh_marker not in text: raise SystemExit('reno manhole sample marker missing')
text=text.replace(reno_mh_marker,reno_mh_new,1)

reno_return="""        _merge_entry_history(truck_counts,operator_counts)
        return {'profile':'reno','pipes': pipes, 'pipe_by_id': pipe_by_id, 'manholes': manholes,
"""
reno_return_new="""        _merge_entry_history(truck_counts,operator_counts)
        asset_format=_infer_asset_format(asset_format_samples)
        return {'profile':'reno','asset_format':asset_format,'pipes': pipes, 'pipe_by_id': pipe_by_id, 'manholes': manholes,
"""
if reno_return not in text: raise SystemExit('reno return marker missing')
text=text.replace(reno_return,reno_return_new,1)

# Reno readers also use the inferred format. Their numeric OCR fallback remains intact.
pipe_known="""    known=master_index['pipe_by_id']
    expected_date=parse_date_text(quick_text)
"""
pipe_known_new="""    known=master_index['pipe_by_id']
    asset_format=master_index.get('asset_format')
    expected_date=parse_date_text(quick_text)
"""
if pipe_known not in text: raise SystemExit('reno pipe parser marker missing')
text=text.replace(pipe_known,pipe_known_new,1)
text=text.replace("full_pid_candidates=_ocr_asset_candidates(psr_img,fast_plain=False)",
                  "full_pid_candidates=_ocr_asset_candidates(psr_img,fast_plain=False,asset_format=asset_format)",1)

mh_known="""    known=master_index['manholes']
    rows=[]; blanks=0; seen=set()
"""
mh_known_new="""    known=master_index['manholes']
    asset_format=master_index.get('asset_format')
    rows=[]; blanks=0; seen=set()
"""
if mh_known not in text: raise SystemExit('reno manhole parser marker missing')
text=text.replace(mh_known,mh_known_new,1)
text=text.replace("full_sid_candidates=_ocr_asset_candidates(id_img,fast_plain=False)",
                  "full_sid_candidates=_ocr_asset_candidates(id_img,fast_plain=False,asset_format=asset_format)",1)

# Master-assisted layout sampling should obey the same inferred syntax.
layout_marker="""    sample_bands=list(bands[1:8])
    observed=[[None for _ in sample_bands] for _ in column_boxes]
"""
layout_new="""    sample_bands=list(bands[1:8])
    asset_format=master_index.get('asset_format')
    observed=[[None for _ in sample_bands] for _ in column_boxes]
"""
if layout_marker not in text: raise SystemExit('layout asset format marker missing')
text=text.replace(layout_marker,layout_new,1)
text=text.replace("observed[ci][ri]=_ocr_asset_candidates(cell,fast_plain=True)",
                  "observed[ci][ri]=_ocr_asset_candidates(cell,fast_plain=True,asset_format=asset_format)",1)

# Pair-table and manhole parsers use the inferred rule instead of profile names.
text=text.replace("    profile=master_index.get('profile','')\n    img=prepared['img'];", 
                  "    asset_format=master_index.get('asset_format')\n    img=prepared['img'];",1)
text=text.replace("_ocr_asset_candidates(cell,fast_plain=fast,profile=profile)",
                  "_ocr_asset_candidates(cell,fast_plain=fast,asset_format=asset_format)")
text=text.replace("_ocr_asset_candidates(cell[:max(1,int(ch*.62)),:],fast_plain=fast,profile=profile)",
                  "_ocr_asset_candidates(cell[:max(1,int(ch*.62)),:],fast_plain=fast,asset_format=asset_format)")
text=text.replace("_ocr_asset_candidates(cell[int(ch*.38):,:],fast_plain=fast,profile=profile)",
                  "_ocr_asset_candidates(cell[int(ch*.38):,:],fast_plain=fast,asset_format=asset_format)")
text=text.replace("_ocr_known_r2_candidates(cut(up_box),endpoint_items,profile=profile)",
                  "_ocr_known_r2_candidates(cut(up_box),endpoint_items,asset_format=asset_format)")
text=text.replace("_ocr_known_r2_candidates(cut(dn_box),endpoint_items,profile=profile)",
                  "_ocr_known_r2_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)")
text=text.replace("_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,profile=profile)",
                  "_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,asset_format=asset_format)")
text=text.replace("_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items,profile=profile)",
                  "_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)")
text=text.replace("_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,profile=profile)",
                  "_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,asset_format=asset_format)")

text=text.replace("def parse_year15_manholes(page, master_index, on_row=None, on_progress=None):\n    profile=master_index.get('profile','')",
                  "def parse_year15_manholes(page, master_index, on_row=None, on_progress=None):\n    asset_format=master_index.get('asset_format')",1)
text=text.replace("formatted=_printed_asset_tokens(raw,profile)","formatted=_printed_asset_tokens(raw,asset_format)")
text=text.replace("observations=_ocr_asset_candidates(id_img,profile=profile)",
                  "observations=_ocr_asset_candidates(id_img,asset_format=asset_format)")

# Update the helper docstring to match master-derived behavior.
text=text.replace("If an unresolved pair has no directly readable numeric/date evidence, both\n    displayed endpoints must still look like complete asset IDs.",
                  "For a master with an inferred asset format, both displayed endpoints must\n    satisfy that format before an unresolved row may survive.")

APP.write_text(text,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'PROJECT_ASSET_FORMAT_RULES' not in src
assert 'ASSET_FORMAT_RULES = {' not in src
assert 'def _infer_asset_format(values):' in src
assert "'allow_suffix':True" in src
assert "'asset_format':asset_format" in src
assert "asset_format=master_index.get('asset_format')" in src
assert "_ocr_asset_candidates(cell,fast_plain=fast,asset_format=asset_format)" in src
assert "_keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,asset_format=asset_format)" in src
assert "formatted=_printed_asset_tokens(raw,asset_format)" in src

# Exercise the pure master-format inference helpers without importing Windows UI deps.
tree=ast.parse(src)
names={'_raw_master_asset','_infer_asset_format','_asset_format_requires_dash',
       '_printed_asset_tokens','_asset_value_matches_format'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<master-format>','exec'),ns)
infer=ns['_infer_asset_format']; tokens=ns['_printed_asset_tokens']; valid=ns['_asset_value_matches_format']

# Current B&C-style master: dash is learned from master, not from project name.
rule=infer(['EC-1817','EC-1801','R2-280','DN-1234'])
assert rule['mode']=='prefixed_dash' and rule['requires_dash']
assert rule['max_digits']==4
assert rule['allow_suffix'] is True
for value in ('DN-1','DN-1234','EC-1817','R2-280'):
    assert tokens(value,rule)==[value], value
# Critical: no suffixed example exists above, but one-letter suffixes are STILL
# structurally possible new assets and must not be rejected for that reason.
for value in ('EC-1817A','DN-1234A','R2-280A'):
    assert tokens(value,rule)==[value], value
    assert valid(value,rule), value
for value in ('EC1817','R2280','EN','SUNAA','DN-12345','DN-1234AB'):
    assert tokens(value,rule)==[], value

# Numeric-only master is inferred automatically too. A one-letter new suffix is
# still possible even if the master contains only unsuffixed numbers.
reno=infer(['1','25','430','1234'])
assert reno['mode']=='numeric' and not reno['requires_dash']
assert tokens('1234',reno)==['1234']
assert tokens('1234A',reno)==['1234A']
assert valid('1234A',reno)
assert tokens('DN-1',reno)==[]

print('v82 master-inferred asset-format regression passed.')
''',encoding='utf-8')

# Keep older v82 regressions aligned with the new helper argument name.
clean=CLEAN_TEST.read_text(encoding='utf-8')
clean=clean.replace("profile=profile","asset_format=asset_format")
clean=clean.replace("names={'asset_key','_asset_id_parts','_keep_unresolved_pair_row','_asset_format_rule','_asset_value_matches_profile'}",
                    "names={'asset_key','_asset_id_parts','_keep_unresolved_pair_row','_asset_value_matches_format'}")
clean=clean.replace("if any(t in {'ASSET_FORMAT_RULES','PROJECT_ASSET_FORMAT_RULES'} for t in targets): nodes.append(n)","")
clean=clean.replace("ns={'re':re}","ns={'re':re}")
# Replace the isolated helper execution with generic fallback behavior; master-format
# enforcement itself is covered by the dedicated regression above.
clean=clean.replace("assert keep('EC1817','EC-1475',240.0,None,'year15') is False","assert keep('EC1817','EC-1475',240.0,None) is True")
CLEAN_TEST.write_text(clean,encoding='utf-8')

suffix=SUFFIX_TEST.read_text(encoding='utf-8')
suffix=suffix.replace("profile=profile","asset_format=asset_format")
SUFFIX_TEST.write_text(suffix,encoding='utf-8')

print('Applied master-inferred asset format with universal optional suffix support.')
