from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
text=APP.read_text(encoding='utf-8')

# Preserve both established parser signatures. The confirmed count triggers a
# separate slower recovery pass after normal parsing; existing callers and
# continuation regressions must remain unchanged.
assert "def parse_manhole_list(page, master_index, quick_text, on_row=None, on_progress=None):" in text
assert "def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):" in text

reno_anchor="""        rows.append(rec)\n        if on_row: on_row(rec)\n    return rows\n\n\ndef _year15_oriented(page, kind, preferred_deg=None, return_deg=False):\n"""
reno_insert="""        rows.append(rec)\n        if on_row: on_row(rec)\n    return rows\n\n\ndef _retry_manhole_list_rows(page, master_index, quick_text, on_progress=None):\n    \"\"\"Slower Reno Manhole reread used only after a confirmed-count mismatch.\n\n    It never fabricates an ID from the expected count. Every returned row still\n    comes from OCR of the PDF and uses the existing match/new-suffix rules.\n    \"\"\"\n    base=render_page(page,2.5)\n    img=np.array(Image.fromarray(base).rotate(270,expand=True))\n    h,w=img.shape[:2]\n    known=master_index['manholes']; asset_format=master_index.get('asset_format')\n    rows=[]; seen=set(); start=.1680*h; step=.0260*h\n    for i in range(40):\n        if on_progress: on_progress()\n        yc=int(start+i*step)\n        if yc>=.82*h: break\n        half=max(18,int(step*.58)); y1,y2=max(0,yc-half),min(h,yc+half)\n        date_img=img[y1:y2,int(.080*w):int(.190*w)]\n        id_img=img[y1:y2,int(.135*w):int(.325*w)]\n        observations=[]\n        for value in _ocr_asset_candidates(id_img,fast_plain=False,asset_format=asset_format):\n            if value not in observations: observations.append(value)\n        try:\n            padded=cv2.copyMakeBorder(id_img,8,8,16,16,cv2.BORDER_CONSTANT,value=(255,255,255))\n            for value in _ocr_asset_candidates(padded,fast_plain=True,asset_format=asset_format):\n                if value not in observations: observations.append(value)\n            gray=cv2.cvtColor(padded,cv2.COLOR_RGB2GRAY)\n            for psm in (8,13):\n                raw=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')\n                for value in _printed_asset_tokens(raw,asset_format):\n                    if value not in observations: observations.append(value)\n        except Exception:\n            pass\n        sid_candidates=_ocr_digits(id_img,False)+observations\n        new_options=_new_suffix_asset_candidates(observations,known.keys())\n        new_sid=new_options[0] if new_options else ''\n        sid='' if new_sid else _best_known_id(sid_candidates,known.keys(),max_dist=1)\n        if not sid and not new_sid: continue\n        observed=sid or new_sid; key=asset_key(observed)\n        if not key or key in seen: continue\n        seen.add(key)\n        rec={'kind':'Manhole','asset':observed,'video_length':None,\n             'row_date':_parse_sheet_date(date_img),'status':'Matched' if sid else 'NEW MANHOLE'}\n        if not sid: rec['skip_update']=True\n        rows.append(rec)\n    return rows\n\n\ndef _year15_oriented(page, kind, preferred_deg=None, return_deg=False):\n"""
assert text.count(reno_anchor)==1, text.count(reno_anchor)
text=text.replace(reno_anchor,reno_insert,1)

year15_anchor="""    out=grid_out if len(grid_out)>len(token_out) else token_out\n    for rec in out:\n        if on_row: on_row(rec)\n    return out\n\ndef master_workbook_lock_reason(path):\n"""
year15_insert="""    out=grid_out if len(grid_out)>len(token_out) else token_out\n    for rec in out:\n        if on_row: on_row(rec)\n    return out\n\n\ndef _retry_year15_manhole_rows(page, master_index, on_progress=None, orientation_deg=None):\n    \"\"\"Slower B&C Manhole reread used only after a confirmed-count mismatch.\n\n    Alternate row geometry, trimmed cells, padding, and single-word segmentation\n    are allowed here. Generic unmatched guesses are not: only an existing matched\n    Manhole or a structurally valid NEW MANHOLE suffix can be returned.\n    \"\"\"\n    asset_format=master_index.get('asset_format')\n    img=_year15_oriented(page,'manholes',preferred_deg=orientation_deg); h,w=img.shape[:2]\n    known=master_index['manholes']; retry_layouts=[]\n    bands,table=_table_row_bands(img,.04,.72)\n    if bands and table: retry_layouts.append((bands,table))\n    try:\n        alt_bands,alt_table=_year15_all_row_bands(img,.02,.90)\n        if alt_bands and alt_table:\n            sig=(tuple((int(a),int(b)) for a,b in alt_bands),tuple(map(int,alt_table)))\n            existing={(tuple((int(a),int(b)) for a,b in rb),tuple(map(int,rt))) for rb,rt in retry_layouts}\n            if sig not in existing: retry_layouts.append((alt_bands,alt_table))\n    except Exception:\n        pass\n\n    rows=[]; seen=set()\n    for retry_bands,retry_table in retry_layouts:\n        left,right=retry_table; tw=max(1,right-left)\n        for y1,y2 in retry_bands:\n            if on_progress: on_progress()\n            base=img[y1:y2,left:min(w,int(left+.30*tw))]\n            if not getattr(base,'size',0): continue\n            cells=[(base,False)]\n            trim=max(2,min(10,int(round(tw*.005))))\n            trimmed=img[y1:y2,max(0,left+trim):min(w,int(left+.255*tw))]\n            if getattr(trimmed,'size',0): cells.append((trimmed,True))\n            try:\n                padded=cv2.copyMakeBorder(base,10,10,20,20,cv2.BORDER_CONSTANT,value=(255,255,255))\n                cells.append((padded,True))\n            except Exception:\n                pass\n            observations=[]\n            for cell,fast in cells:\n                for value in _ocr_asset_candidates(cell,fast_plain=fast,asset_format=asset_format):\n                    if value not in observations: observations.append(value)\n                try:\n                    gray=cv2.cvtColor(cell,cv2.COLOR_RGB2GRAY)\n                    for psm in (8,13):\n                        raw=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')\n                        for value in _printed_asset_tokens(raw,asset_format):\n                            if value not in observations: observations.append(value)\n                except Exception:\n                    pass\n            if not observations: continue\n            item,status=_resolve_full_asset(observations,known)\n            if item is None and status!='NEW MANHOLE': continue\n            sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))\n            key=item['asset_key'] if item else asset_key(sid)\n            if not key or key in seen: continue\n            seen.add(key)\n            date_img=img[y1:y2,int(left+.74*tw):right]\n            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                 'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n            rec['_field_previews']={\n                'asset':base.copy() if getattr(base,'size',0) else None,\n                'date':date_img.copy() if getattr(date_img,'size',0) else None}\n            if item is None: rec['skip_update']=True\n            rows.append(rec)\n    return rows\n\n\ndef master_workbook_lock_reason(path):\n"""
assert text.count(year15_anchor)==1, text.count(year15_anchor)
text=text.replace(year15_anchor,year15_insert,1)

old_decl="ignored_pages=[]; validation_reports=[]; total_sources={}; manhole_rows_by_wo={}"
new_decl="ignored_pages=[]; validation_reports=[]; total_sources={}; manhole_rows_by_wo={}; manhole_retry_pages={}"
assert text.count(old_decl)==1, text.count(old_decl)
text=text.replace(old_decl,new_decl,1)

old_count="""                if kind=='manholes':\n                    wo_key=str(current_wo.get('wo',''))\n                    manhole_rows_by_wo[wo_key]=manhole_rows_by_wo.get(wo_key,0)+int(report.get('rows') or 0)\n\n            self.manhole_count_validations=[]\n"""
new_count="""                if kind=='manholes':\n                    wo_key=str(current_wo.get('wo',''))\n                    manhole_rows_by_wo[wo_key]=manhole_rows_by_wo.get(wo_key,0)+int(report.get('rows') or 0)\n                    manhole_retry_pages.setdefault(wo_key,[]).append({\n                        'page':page,'item':item,'txt':txt,'current_wo':dict(current_wo),\n                        'use_date':use_date,'page_number':pi+1,'data':list(data),'report':report})\n\n            # The confirmed expected count is an active recovery trigger. If the\n            # normal pass misses it, reread every Manhole page in that work order\n            # with slower Manhole-only OCR before showing the final count result.\n            for wo_info in confirmed_by_page.values():\n                expected=wo_info.get('expected_manhole_count')\n                if expected is None: continue\n                wo_key=str(wo_info.get('wo','')); expected=int(expected)\n                actual=int(manhole_rows_by_wo.get(wo_key,0))\n                if actual==expected: continue\n                contexts=manhole_retry_pages.get(wo_key,[])\n                if not contexts: continue\n                self.status.set(f'Manhole count {actual}/{expected} for W/O {wo_key} — retrying OCR...')\n                self.pump_analysis_ui()\n                existing_keys={asset_key(rec.get('asset')) for rec in self.records\n                               if rec.get('kind')=='Manhole' and str(rec.get('wo',''))==wo_key}\n                recovered=[]; recovered_keys=set()\n                for ctx in contexts:\n                    item=ctx['item']; page=ctx['page']; txt=ctx['txt']\n                    try:\n                        if idx.get('profile') in ('year15','phase2_year1'):\n                            retry_rows=_retry_year15_manhole_rows(\n                                page,idx,self.pump_analysis_ui,item.get('effective_deg'))\n                        else:\n                            retry_rows=_retry_manhole_list_rows(page,idx,txt,self.pump_analysis_ui)\n                    except AnalysisCancelled:\n                        raise\n                    except Exception:\n                        retry_rows=[]\n                    page_extras=[]\n                    for rec in retry_rows:\n                        key=asset_key(rec.get('asset'))\n                        if not key or key in existing_keys or key in recovered_keys: continue\n                        recovered_keys.add(key); recovered.append((ctx,rec,key)); page_extras.append(rec)\n                    ctx['_mh_retry_extras']=page_extras\n\n                candidate_total=actual+len(recovered)\n                # Never choose an arbitrary subset or delete a first-pass row merely\n                # to force the number. Add all independently observed recovery rows\n                # only when doing so cannot exceed the user's confirmed count.\n                if actual<expected and recovered and candidate_total<=expected:\n                    for ctx in contexts:\n                        extras=ctx.get('_mh_retry_extras') or []\n                        if not extras: continue\n                        merged=list(ctx.get('data') or [])+[dict(rec) for rec in extras]\n                        refreshed=validate_page_rows(merged,'manholes',ctx['txt'],ctx['page_number'],\n                                                     ctx['item'].get('pair_layout'),idx.get('profile'))\n                        ctx['report'].clear(); ctx['report'].update(refreshed); ctx['data']=merged\n                    for ctx,rec,key in recovered:\n                        self.commit_extracted_record(\n                            rec,ctx['current_wo'],ctx['use_date'],idx,ctx['page_number'],processed)\n                    actual=candidate_total; manhole_rows_by_wo[wo_key]=actual\n                elif actual<expected and candidate_total>expected:\n                    self.status.set(\n                        f'Manhole OCR retry found {len(recovered)} additional plausible row(s) for W/O {wo_key}, '\n                        f'which would exceed confirmed count {expected}; automatic add skipped for review.')\n                    self.pump_analysis_ui()\n\n                if actual==expected:\n                    self.status.set(f'Manhole OCR retry matched confirmed count {expected} for W/O {wo_key}.')\n                elif not (actual<expected and candidate_total>expected):\n                    self.status.set(f'Manhole OCR retry finished at {actual}/{expected} for W/O {wo_key}; review still required.')\n                self.pump_analysis_ui()\n\n            self.manhole_count_validations=[]\n"""
assert text.count(old_count)==1, text.count(old_count)
text=text.replace(old_count,new_count,1)

APP.write_text(text,encoding='utf-8')

TEST=Path('working_source/tests/regression_post_v102_manhole_expected_count_retry.py')
TEST.write_text(r'''from pathlib import Path
import ast
import cv2
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)

assert "def parse_manhole_list(page, master_index, quick_text, on_row=None, on_progress=None):" in text
assert "def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):" in text
for required in (
    'def _retry_manhole_list_rows(',
    'def _retry_year15_manhole_rows(',
    '_year15_all_row_bands(img,.02,.90)',
    'for psm in (8,13):',
    "Manhole count {actual}/{expected} for W/O {wo_key} — retrying OCR",
    "manhole_retry_pages.setdefault(wo_key,[]).append",
    'candidate_total=actual+len(recovered)',
    'candidate_total<=expected',
    'automatic add skipped for review',
):
    assert required in text,required

helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_retry_year15_manhole_rows')
img=np.full((400,700,3),255,dtype=np.uint8)
bands=[(80,110),(120,150),(160,190)]
table=(50,600)
for color,(y1,y2) in zip((190,160,130),bands): img[y1:y2,:,:]=color
known={
    'DN1001':{'asset':'DN-1001','asset_key':'DN1001'},
    'DN1002':{'asset':'DN-1002','asset_key':'DN1002'},
}

def ocr_assets(cell,fast_plain=False,asset_format=None):
    mean=float(np.mean(cell)) if getattr(cell,'size',0) else 255
    if 180<mean<205: return ['DN-1001']
    if 145<mean<175: return ['DN-1002']
    if 115<mean<145: return ['DN-9999']
    return []

def resolve(values,known_items):
    for value in values:
        key=''.join(ch for ch in str(value).upper() if ch.isalnum())
        if key in known_items: return known_items[key],'Matched'
    return None,'NOT MATCHED'

ns={
    'cv2':cv2,'np':np,
    '_year15_oriented':lambda page,kind,preferred_deg=None: img,
    '_table_row_bands':lambda image,a,b:(bands,table),
    '_year15_all_row_bands':lambda image,a,b:(bands,table),
    '_ocr_asset_candidates':ocr_assets,
    'cached_ocr_string':lambda image,config='':'',
    '_printed_asset_tokens':lambda value,asset_format:[],
    '_resolve_full_asset':resolve,
    '_best_observed_asset_id':lambda values,known_items: values[0] if values else '',
    'canonical_asset_id':lambda value:str(value).strip().upper(),
    'asset_key':lambda value:''.join(ch for ch in str(value).upper() if ch.isalnum()),
    '_parse_sheet_date':lambda cell:None,
}
exec(compile(ast.Module(body=[helper],type_ignores=[]),str(SOURCE),'exec'),ns)
rows=ns['_retry_year15_manhole_rows'](
    object(),{'asset_format':{'mode':'prefixed_dash'},'manholes':known})
assert [row['asset'] for row in rows]==['DN-1001','DN-1002'],rows
assert all(row['status']=='Matched' for row in rows),rows

print('post-v102 Manhole expected-count OCR retry regression passed')
''',encoding='utf-8')

for path in [Path('PROJECT_CONTEXT.md'),Path('working_source/docs/PROJECT_CONTEXT.md')]:
    doc=path.read_text(encoding='utf-8')
    anchor="""This is a user-confirmed count safeguard, separate from pair-table printed total\nlength validation.\n"""
    addition="""This is a user-confirmed count safeguard, separate from pair-table printed total\nlength validation.\n\nThe confirmed count is also an OCR recovery trigger. After the normal Manhole\npass finishes, any work order whose parsed count does not equal the user-confirmed\ncount automatically rereads all of that work order's Manhole pages with slower\nManhole-only alternate row/crop/segmentation passes. Newly recovered rows are\naccepted only when their IDs are actually observed in the PDF and pass the existing\nstrict matching/new-suffix safeguards. The expected count never fabricates an ID,\ndeletes a first-pass row, or chooses an arbitrary subset merely to make the number\nmatch. If recovery would exceed the confirmed count, automatic addition is skipped\nand review remains required.\n"""
    assert anchor in doc,path
    if addition not in doc: doc=doc.replace(anchor,addition,1)
    path.write_text(doc,encoding='utf-8')

for path in [Path('RELEASE_CHECKLIST.md'),Path('working_source/docs/RELEASE_CHECKLIST.md')]:
    doc=path.read_text(encoding='utf-8')
    active='- post-v102 Manhole partial-token/grid-row recovery regression;\n'
    if '- post-v102 Manhole expected-count retry regression;\n' not in doc:
        assert active in doc,path
        doc=doc.replace(active,'- post-v102 Manhole expected-count retry regression;\n'+active,1)
    file_anchor='- `working_source/tests/regression_post_v102_manhole_partial_tokens.py`\n'
    if '- `working_source/tests/regression_post_v102_manhole_expected_count_retry.py`\n' not in doc:
        assert file_anchor in doc,path
        doc=doc.replace(file_anchor,'- `working_source/tests/regression_post_v102_manhole_expected_count_retry.py`\n'+file_anchor,1)
    anchor="""- Parsed Manhole row count is checked against that expected count.\n"""
    addition="""- Parsed Manhole row count is checked against that expected count.\n- A mismatch automatically triggers a slower reread of every Manhole page in that\n  work order before the final mismatch is presented. The retry may use only\n  PDF-observed IDs that still pass the established matching/new-suffix safeguards;\n  it must never invent, delete, or arbitrarily select rows solely to hit the count.\n"""
    assert anchor in doc,path
    if addition not in doc: doc=doc.replace(anchor,addition,1)
    path.write_text(doc,encoding='utf-8')

print('Applied Manhole expected-count retry and documentation updates.')
