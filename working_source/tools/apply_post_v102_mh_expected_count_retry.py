from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
text=APP.read_text(encoding='utf-8')

old="def parse_manhole_list(page, master_index, quick_text, on_row=None, on_progress=None):"
new="def parse_manhole_list(page, master_index, quick_text, on_row=None, on_progress=None, expected_count=None):"
assert text.count(old)==1, text.count(old)
text=text.replace(old,new,1)

old_tail="""        rows.append(rec)\n        if on_row: on_row(rec)\n    return rows\n\n\ndef _year15_oriented(page, kind, preferred_deg=None, return_deg=False):\n"""
new_tail="""        rows.append(rec)\n        if on_row: on_row(rec)\n\n    # The user-confirmed Manhole count is a recovery trigger, never permission to\n    # invent IDs. If the normal Reno pass misses the target, re-scan every expected\n    # row position without the early blank-stop and with padded/alternate OCR.\n    try:\n        target_count=int(expected_count) if expected_count is not None else None\n    except Exception:\n        target_count=None\n    if target_count and target_count>0 and len(rows)!=target_count:\n        retry_rows=[]; retry_seen=set()\n        for i in range(40):\n            if on_progress: on_progress()\n            yc=int(start+i*step)\n            if yc >= .82*h: break\n            half=max(18,int(step*.58)); y1,y2=max(0,yc-half),min(h,yc+half)\n            date_img=img[y1:y2,int(.080*w):int(.190*w)]\n            id_img=img[y1:y2,int(.135*w):int(.325*w)]\n            full=[]\n            for cell,fast in ((id_img,False),):\n                for value in _ocr_asset_candidates(cell,fast_plain=fast,asset_format=asset_format):\n                    if value not in full: full.append(value)\n            try:\n                padded=cv2.copyMakeBorder(id_img,8,8,16,16,cv2.BORDER_CONSTANT,value=(255,255,255))\n                for value in _ocr_asset_candidates(padded,fast_plain=True,asset_format=asset_format):\n                    if value not in full: full.append(value)\n                gray=cv2.cvtColor(padded,cv2.COLOR_RGB2GRAY)\n                for psm in (8,13):\n                    raw=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')\n                    for value in _printed_asset_tokens(raw,asset_format):\n                        if value not in full: full.append(value)\n            except Exception:\n                pass\n            sid_candidates=_ocr_digits(id_img,False)+full\n            new_options=_new_suffix_asset_candidates(full,known.keys())\n            new_sid=new_options[0] if new_options else ''\n            sid='' if new_sid else _best_known_id(sid_candidates,known.keys(),max_dist=1)\n            if not sid and not new_sid: continue\n            observed=sid or new_sid; key=asset_key(observed)\n            if not key or key in retry_seen: continue\n            retry_seen.add(key)\n            rec={'kind':'Manhole','asset':observed,'video_length':None,\n                 'row_date':_parse_sheet_date(date_img),'status':'Matched' if sid else 'NEW MANHOLE'}\n            if not sid: rec['skip_update']=True\n            retry_rows.append(rec)\n\n        if retry_rows:\n            candidate_sets=[rows,retry_rows]\n            merged=[]; merged_seen=set()\n            for candidate in rows+retry_rows:\n                key=asset_key(candidate.get('asset'))\n                if not key or key in merged_seen: continue\n                merged_seen.add(key); merged.append(candidate)\n            candidate_sets.append(merged)\n            def score(candidate):\n                unresolved=sum(1 for row in candidate if row.get('skip_update'))\n                over=1 if len(candidate)>target_count else 0\n                return (abs(len(candidate)-target_count),over,unresolved,-len(candidate))\n            best=min(candidate_sets,key=score)\n            if best is not rows:\n                initial_keys={asset_key(row.get('asset')) for row in rows}\n                rows=best\n                if on_row:\n                    for rec in rows:\n                        if asset_key(rec.get('asset')) not in initial_keys: on_row(rec)\n    return rows\n\n\ndef _year15_oriented(page, kind, preferred_deg=None, return_deg=False):\n"""
assert text.count(old_tail)==1, text.count(old_tail)
text=text.replace(old_tail,new_tail,1)

old="def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):"
new="def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None, expected_count=None):"
assert text.count(old)==1, text.count(old)
text=text.replace(old,new,1)

old_choose="""    out=grid_out if len(grid_out)>len(token_out) else token_out\n    for rec in out:\n        if on_row: on_row(rec)\n    return out\n"""
new_choose="""    out=grid_out if len(grid_out)>len(token_out) else token_out\n\n    # A confirmed Manhole count is active OCR evidence about how many physical\n    # survey rows should exist. Only when the normal result misses that target do\n    # we spend time on a broader Manhole-only reread. Every accepted ID still has\n    # to come from the PDF and pass the existing strict ID/matching rules.\n    try:\n        target_count=int(expected_count) if expected_count is not None else None\n    except Exception:\n        target_count=None\n    if target_count and target_count>0 and len(out)!=target_count:\n        retry_layouts=[]\n        if bands and table: retry_layouts.append((bands,table))\n        try:\n            alt_bands,alt_table=_year15_all_row_bands(img,.02,.90)\n            if alt_bands and alt_table:\n                sig=(tuple((int(a),int(b)) for a,b in alt_bands),tuple(map(int,alt_table)))\n                existing_sigs={(tuple((int(a),int(b)) for a,b in rb),tuple(map(int,rt))) for rb,rt in retry_layouts}\n                if sig not in existing_sigs: retry_layouts.append((alt_bands,alt_table))\n        except Exception:\n            pass\n\n        retry_sets=[]\n        for retry_bands,retry_table in retry_layouts:\n            rleft,rright=retry_table; rtw=max(1,rright-rleft); retry_rows=[]; retry_seen=set()\n            for y1,y2 in retry_bands:\n                if on_progress: on_progress()\n                cells=[]\n                base=img[y1:y2,rleft:min(w,int(rleft+.30*rtw))]\n                if getattr(base,'size',0): cells.append((base,False))\n                trim=max(2,min(10,int(round(rtw*.005))))\n                trimmed=img[y1:y2,max(0,rleft+trim):min(w,int(rleft+.255*rtw))]\n                if getattr(trimmed,'size',0): cells.append((trimmed,True))\n                if getattr(base,'size',0):\n                    try:\n                        padded=cv2.copyMakeBorder(base,10,10,20,20,cv2.BORDER_CONSTANT,value=(255,255,255))\n                        cells.append((padded,True))\n                    except Exception:\n                        pass\n                observations=[]\n                for cell,fast in cells:\n                    for value in _ocr_asset_candidates(cell,fast_plain=fast,asset_format=asset_format):\n                        if value not in observations: observations.append(value)\n                    try:\n                        gray=cv2.cvtColor(cell,cv2.COLOR_RGB2GRAY)\n                        for psm in (8,13):\n                            raw=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')\n                            for value in _printed_asset_tokens(raw,asset_format):\n                                if value not in observations: observations.append(value)\n                    except Exception:\n                        pass\n                if not observations: continue\n                item,status=_resolve_full_asset(observations,known)\n                # Count-driven rereads may add matched rows or structurally valid\n                # NEW MANHOLE suffixes, but never generic fuzzy/unmatched guesses.\n                if item is None and status!='NEW MANHOLE': continue\n                sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))\n                unique_key=item['asset_key'] if item else asset_key(sid)\n                if not unique_key or unique_key in retry_seen: continue\n                retry_seen.add(unique_key)\n                date_img=img[y1:y2,int(rleft+.74*rtw):rright]\n                rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                     'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n                rec['_field_previews']={\n                    'asset':base.copy() if getattr(base,'size',0) else None,\n                    'date':date_img.copy() if getattr(date_img,'size',0) else None}\n                if item is None: rec['skip_update']=True\n                retry_rows.append(rec)\n            if retry_rows: retry_sets.append(retry_rows)\n\n        candidate_sets=[out]+retry_sets\n        for retry_rows in retry_sets:\n            merged=[]; merged_seen=set()\n            for rec in out+retry_rows:\n                key=asset_key(rec.get('asset'))\n                if not key or key in merged_seen: continue\n                merged_seen.add(key); merged.append(rec)\n            candidate_sets.append(merged)\n        if len(candidate_sets)>1:\n            def score(candidate):\n                unresolved=sum(1 for row in candidate if row.get('skip_update'))\n                matched=sum(1 for row in candidate if row.get('status')=='Matched')\n                over=1 if len(candidate)>target_count else 0\n                return (abs(len(candidate)-target_count),over,unresolved,-matched,-len(candidate))\n            out=min(candidate_sets,key=score)\n\n    for rec in out:\n        if on_row: on_row(rec)\n    return out\n"""
assert text.count(old_choose)==1, text.count(old_choose)
text=text.replace(old_choose,new_choose,1)

old_decl="ignored_pages=[]; validation_reports=[]; total_sources={}; manhole_rows_by_wo={}"
new_decl="ignored_pages=[]; validation_reports=[]; total_sources={}; manhole_rows_by_wo={}; manhole_retry_pages={}"
assert text.count(old_decl)==1, text.count(old_decl)
text=text.replace(old_decl,new_decl,1)

old_count="""                if kind=='manholes':\n                    wo_key=str(current_wo.get('wo',''))\n                    manhole_rows_by_wo[wo_key]=manhole_rows_by_wo.get(wo_key,0)+int(report.get('rows') or 0)\n\n            self.manhole_count_validations=[]\n"""
new_count="""                if kind=='manholes':\n                    wo_key=str(current_wo.get('wo',''))\n                    manhole_rows_by_wo[wo_key]=manhole_rows_by_wo.get(wo_key,0)+int(report.get('rows') or 0)\n                    manhole_retry_pages.setdefault(wo_key,[]).append({\n                        'page':page,'item':item,'txt':txt,'current_wo':dict(current_wo),\n                        'use_date':use_date,'page_number':pi+1})\n\n            # The confirmed expected count is not only a warning threshold. If the\n            # first pass misses it, reread every Manhole page in that work order with\n            # the slower target-aware OCR path and add only newly observed IDs.\n            for wo_info in confirmed_by_page.values():\n                expected=wo_info.get('expected_manhole_count')\n                if expected is None: continue\n                wo_key=str(wo_info.get('wo','')); expected=int(expected)\n                actual=int(manhole_rows_by_wo.get(wo_key,0))\n                if actual==expected: continue\n                contexts=manhole_retry_pages.get(wo_key,[])\n                if not contexts: continue\n                self.status.set(f'Manhole count {actual}/{expected} for W/O {wo_key} — retrying OCR...')\n                self.pump_analysis_ui()\n                existing_keys={asset_key(rec.get('asset')) for rec in self.records\n                               if rec.get('kind')=='Manhole' and str(rec.get('wo',''))==wo_key}\n                recovered=[]\n                for ctx in contexts:\n                    item=ctx['item']; page=ctx['page']; txt=ctx['txt']\n                    try:\n                        if idx.get('profile') in ('year15','phase2_year1'):\n                            retry_data=parse_year15_manholes(\n                                page,idx,None,self.pump_analysis_ui,item.get('effective_deg'),expected)\n                        else:\n                            retry_data=parse_manhole_list(\n                                page,idx,txt,None,self.pump_analysis_ui,expected)\n                    except AnalysisCancelled:\n                        raise\n                    except Exception:\n                        continue\n                    for rec in retry_data:\n                        key=asset_key(rec.get('asset'))\n                        if not key or key in existing_keys: continue\n                        recovered.append((ctx,rec,key)); existing_keys.add(key)\n                if actual<expected:\n                    for ctx,rec,key in recovered:\n                        self.commit_extracted_record(\n                            rec,ctx['current_wo'],ctx['use_date'],idx,ctx['page_number'],processed)\n                        actual+=1\n                    manhole_rows_by_wo[wo_key]=actual\n                if actual==expected:\n                    self.status.set(f'Manhole OCR retry matched confirmed count {expected} for W/O {wo_key}.')\n                else:\n                    self.status.set(f'Manhole OCR retry finished at {actual}/{expected} for W/O {wo_key}; review still required.')\n                self.pump_analysis_ui()\n\n            self.manhole_count_validations=[]\n"""
assert text.count(old_count)==1, text.count(old_count)
text=text.replace(old_count,new_count,1)

APP.write_text(text,encoding='utf-8')

# Permanent regression for the expected-count trigger and target-aware reread.
TEST=Path('working_source/tests/regression_post_v102_manhole_expected_count_retry.py')
TEST.write_text(r'''from pathlib import Path
import ast
import cv2
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')
func=ast.get_source_segment(text,node) or ''
for required in (
    'expected_count=None',
    'target_count=int(expected_count)',
    '_year15_all_row_bands(img,.02,.90)',
    'candidate_sets=[out]+retry_sets',
    "Manhole count {actual}/{expected} for W/O {wo_key} — retrying OCR",
    "manhole_retry_pages.setdefault(wo_key,[]).append",
):
    assert required in text,required

IDS=['DN-1001','DN-1002']
img=np.full((500,800,3),255,dtype=np.uint8)
bands=[(80,110),(120,150),(160,190)]
table=(50,600)
state={'retry':False}
for index,(y1,y2) in enumerate(bands):
    img[y1:y2,:,:]=220-index*30

class _Output:
    DICT='DICT'
class _Tesseract:
    Output=_Output
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        return {'text':['DN-1001'],'left':[20],'top':[125],'height':[20]}

known={value.replace('-',''):{'asset':value,'asset_key':value.replace('-','')} for value in IDS}

def printed(value,asset_format):
    value=str(value).strip().upper()
    return [value] if value in IDS else []

def resolve(values,known_items):
    for value in values:
        item=known_items.get(str(value).replace('-',''))
        if item: return item,'Matched'
    return None,'NOT MATCHED'

def ocr_assets(cell,fast_plain=False,asset_format=None):
    mean=float(np.mean(cell)) if getattr(cell,'size',0) else 255
    # Normal pass sees only DN-1001. The count-triggered alternate-band pass
    # exposes DN-1002 from the third physical row.
    if 180<mean<210: return ['DN-1001']
    if state['retry'] and 145<mean<180: return ['DN-1002']
    return []

def alt_bands(image,min_y,max_y):
    state['retry']=True
    return bands,table

ns={
    'cv2':cv2,'np':np,'pytesseract':_Tesseract,
    '_year15_oriented':lambda page,kind,preferred_deg=None: img,
    'parse_date_text':lambda value: None,
    '_printed_asset_tokens':printed,
    '_resolve_full_asset':resolve,
    '_best_observed_asset_id':lambda values,known_items: values[0] if values else '',
    'canonical_asset_id':lambda value: str(value).strip().upper(),
    'asset_key':lambda value: ''.join(ch for ch in str(value).upper() if ch.isalnum()),
    '_table_row_bands':lambda image,min_y,max_y:(bands,table),
    '_year15_all_row_bands':alt_bands,
    '_ocr_asset_candidates':ocr_assets,
    '_parse_sheet_date':lambda cell: None,
    'cached_ocr_string':lambda image,config='': '',
}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

normal=ns['parse_year15_manholes'](object(),{'asset_format':{'mode':'prefixed_dash'},'manholes':known})
assert len(normal)==1,normal
state['retry']=False
retried=ns['parse_year15_manholes'](
    object(),{'asset_format':{'mode':'prefixed_dash'},'manholes':known},expected_count=2)
assert [row['asset'] for row in retried]==IDS,retried
assert state['retry'] is True

reno=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_manhole_list')
assert 'expected_count=None' in (ast.get_source_segment(text,reno) or '')
print('post-v102 Manhole expected-count OCR retry regression passed')
''',encoding='utf-8')

# Keep living documentation synchronized.
for path in [Path('PROJECT_CONTEXT.md'),Path('working_source/docs/PROJECT_CONTEXT.md')]:
    doc=path.read_text(encoding='utf-8')
    anchor="""This is a user-confirmed count safeguard, separate from pair-table printed total\nlength validation.\n"""
    addition="""This is a user-confirmed count safeguard, separate from pair-table printed total\nlength validation.\n\nThe confirmed count is also an OCR recovery trigger. After the normal Manhole\npass finishes, any work order whose parsed count does not equal the user-confirmed\ncount automatically rereads all of that work order's Manhole pages with slower\nManhole-only alternate row/crop/segmentation passes. Newly recovered rows are\naccepted only when their IDs are actually observed in the PDF and pass the existing\nstrict matching/new-suffix safeguards. The expected count never fabricates an ID\nor deletes an observed row merely to make the number match; if the reread still\ndoes not reach the confirmed count, the existing mismatch review remains.\n"""
    assert anchor in doc,path
    if addition not in doc:
        doc=doc.replace(anchor,addition,1)
    path.write_text(doc,encoding='utf-8')

for path in [Path('RELEASE_CHECKLIST.md'),Path('working_source/docs/RELEASE_CHECKLIST.md')]:
    doc=path.read_text(encoding='utf-8')
    anchor="""- Parsed Manhole row count is checked against that expected count.\n"""
    addition="""- Parsed Manhole row count is checked against that expected count.\n- A mismatch automatically triggers a slower reread of every Manhole page in that\n  work order before the mismatch is presented for review. The retry may use only\n  PDF-observed IDs that still pass the established Manhole matching/new-suffix\n  safeguards; it must never invent, pad, or delete rows solely to hit the count.\n"""
    assert anchor in doc,path
    if addition not in doc:
        doc=doc.replace(anchor,addition,1)
    path.write_text(doc,encoding='utf-8')

print('Applied Manhole expected-count retry and documentation updates.')
