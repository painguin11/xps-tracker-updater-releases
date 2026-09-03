from pathlib import Path
import ast

APP = Path('working_source/app/reno_scan_updater.py')
source = APP.read_text(encoding='utf-8')


def replace_top_function(src, name, new_text):
    tree = ast.parse(src)
    node = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
    if node is None:
        raise AssertionError(f'top-level function {name} not found')
    lines = src.splitlines(keepends=True)
    replacement = new_text.rstrip() + '\n\n'
    return ''.join(lines[:node.lineno-1]) + replacement + ''.join(lines[node.end_lineno:])


def replace_between(src, start_marker, end_marker, new_text):
    start = src.find(start_marker)
    if start < 0:
        raise AssertionError(f'start marker not found: {start_marker}')
    end = src.find(end_marker, start)
    if end < 0:
        raise AssertionError(f'end marker not found: {end_marker}')
    return src[:start] + new_text.rstrip() + '\n\n' + src[end:]


def replace_once(src, old, new):
    count = src.count(old)
    if count != 1:
        raise AssertionError(f'expected exactly one replacement marker, found {count}: {old[:120]!r}')
    return src.replace(old, new, 1)


source = replace_top_function(source, '_year15_oriented', r'''def _year15_oriented(page, kind, preferred_deg=None, return_deg=False):
    """Orient a B&C table page, optionally inheriting the prior table rotation.

    Headerless continuation pages cannot be scored from header words, so callers
    may provide the rotation already confirmed by the preceding page in the same
    work order/table run. Explicitly headed pages keep the existing OCR scoring.
    """
    base=render_page(page,2.5)

    def rotated(deg):
        return base if deg==0 else np.array(Image.fromarray(base).rotate(deg,expand=True))

    if preferred_deg in (0,90,180,270):
        img=rotated(int(preferred_deg))
        return (img,int(preferred_deg)) if return_deg else img

    best=None
    for deg in (0,270,90):
        img=rotated(deg)
        txt=ocr_text(img[:max(1,int(img.shape[0]*.30)),:],11).lower()
        if kind=='cleaning':
            norm=re.sub(r'[^a-z0-9]+',' ',txt)
            score=(8*(('wheel walk' in norm) or ('wheel' in norm and 'walk' in norm))+
                   5*(('cleaning date' in norm) or ('cleaning' in norm and 'date' in norm))+
                   2*('up mh' in norm))
        elif kind=='pipes': score=8*('length surveyed' in txt or 'surveyed length' in txt)+3*('upstream' in txt)+3*('downstream' in txt)
        else: score=8*('manhole number' in txt)+4*('drainage area' in txt)
        if best is None or score>best[0]: best=(score,img,deg)
    return (best[1],best[2]) if return_deg else best[1]
''')

insert_marker = '\ndef _header_role(compact,kind):\n'
if insert_marker not in source:
    raise AssertionError('header-role insertion marker missing')
recovery = r'''
def _year15_recover_vertical_rules(img,bands,table,column_bounds=None):
    """Supplement missing B&C column boundaries using repeated row-band evidence.

    A true vertical grid rule remains dark through most of many row interiors even
    when horizontal intersections break it into segments. Text strokes may repeat
    at similar x positions, but they do not occupy most of the row height across a
    large fraction of rows. Existing strong rules are retained and this recovery is
    rejected if it would create an implausible (>20-column) layout.
    """
    existing=sorted(int(x) for x in (column_bounds or []))
    if img is None or not bands or not table:
        return existing
    left,right=map(int,table); h,w=img.shape[:2]
    left=max(0,min(w-1,left)); right=max(left+1,min(w,right))
    if right-left<40 or len(bands)<3:
        return existing
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    heights=[max(1,int(b)-int(a)) for a,b in bands]
    typical=float(np.median(heights)) if heights else 1.0
    usable=[(max(0,int(a)),min(h,int(b))) for a,b in bands
            if typical*.55 <= max(1,int(b)-int(a)) <= typical*1.55]
    if len(usable)<3:
        usable=[(max(0,int(a)),min(h,int(b))) for a,b in bands]
    width=right-left
    hits=np.zeros(width,dtype=np.int16)
    for y1,y2 in usable:
        if y2-y1<4: continue
        dark=(gray[y1:y2,left:right] < 205).astype(np.uint8)
        dark=cv2.dilate(dark,np.ones((1,3),np.uint8),iterations=1)
        vertical_fraction=np.mean(dark>0,axis=0)
        hits += (vertical_fraction>=.72).astype(np.int16)
    required=max(3,int(np.ceil(len(usable)*.42)))
    candidate_positions=[left+int(x) for x in np.where(hits>=required)[0]]
    groups=[]
    max_gap=max(2,int(round(width*.0025)))
    for x in candidate_positions:
        if not groups or x-groups[-1][-1]>max_gap:
            groups.append([x])
        else:
            groups[-1].append(x)
    recovered=[int(round(float(np.median(group)))) for group in groups]

    merged=sorted(set([left,right]+existing+recovered))
    dedup=[]; minimum_gap=max(7,int(round(width*.010)))
    for x in merged:
        if not dedup:
            dedup.append(x); continue
        if x-dedup[-1]<minimum_gap:
            prev=dedup[-1]
            if x in existing and prev not in existing: dedup[-1]=x
            elif prev not in existing and x not in existing: dedup[-1]=(prev+x)//2
        else:
            dedup.append(x)
    if not (5<=len(dedup)<=21):
        return existing or [left,right]
    return dedup
'''
source = source.replace(insert_marker, '\n' + recovery.rstrip() + '\n\n' + insert_marker.lstrip('\n'), 1)

source = replace_top_function(source, 'prepare_year15_pair_layout', r'''def prepare_year15_pair_layout(page,master_index,kind,inherited_layout=None,preferred_deg=None):
    """Render once, detect the grid, and prepare a confirmable/reusable pair layout.

    A headerless continuation reuses only the preceding confirmed table's relative
    column geometry, role indices, and orientation within the same work order. Row
    bands and outer table bounds are still detected on the current physical page.
    """
    img,orientation_deg=_year15_oriented(page,kind,preferred_deg=preferred_deg,return_deg=True)
    bands,table,column_bounds=_year15_grid_bands(img)
    geometry_source='vertical grid'
    if not bands:
        bands,table,column_bounds=_year15_compact_grid_bands(img)
        if bands: geometry_source='compact table grid'
    if not bands:
        bands,table=_year15_all_row_bands(img,.04,.90); column_bounds=None; geometry_source='horizontal fallback'

    if bands and not table and inherited_layout:
        previous_img=inherited_layout.get('img'); previous_table=inherited_layout.get('table')
        if previous_img is not None and previous_table and getattr(previous_img,'shape',None):
            prev_w=max(1,int(previous_img.shape[1])); cur_w=max(1,int(img.shape[1]))
            table=(int(previous_table[0]/prev_w*cur_w),int(previous_table[1]/prev_w*cur_w))
            geometry_source+=' / inherited outer bounds'

    if not bands or not table:
        return {'kind':kind,'img':img,'bands':[],'table':None,'mapping':{},'headers':[],
                'column_boxes':[],'role_indices':{},'confidence':0,'source':'table not found',
                'warnings':['TABLE STRUCTURE NOT RESOLVED'],'orientation_deg':orientation_deg,
                'inherited_layout':False}

    column_bounds=_year15_recover_vertical_rules(img,bands,table,column_bounds)
    left,right=table; tw=max(1,right-left)
    if column_bounds and len(column_bounds)>=2:
        column_boxes=[((a-left)/tw,(b-left)/tw) for a,b in zip(column_bounds,column_bounds[1:])]
    else:
        column_boxes=[]
    mapping,cells,source,header_band_index=_table_header_columns(img,bands,table,kind,column_bounds,return_details=True)
    if cells and not column_boxes: column_boxes=[c[1] for c in sorted(cells,key=lambda x:x[0])]
    headers=[f'Column {i+1}' for i in range(len(column_boxes))]
    for ci,box,compact,display in cells:
        if 0<=ci<len(headers): headers[ci]=f'Column {ci+1} — {display}'
    mapping=dict(mapping or {}); role_indices={}
    for role,box in mapping.items():
        idx=_column_index_for_box(box,column_boxes)
        if idx is not None: role_indices[role]=idx

    previous_boxes=list((inherited_layout or {}).get('column_boxes') or [])
    previous_roles=dict((inherited_layout or {}).get('role_indices') or {})
    can_inherit=(previous_boxes and all(k in previous_roles for k in ('up','down','value','date')))
    complete_header=all(k in role_indices for k in ('up','down','value','date'))
    if can_inherit and not complete_header:
        if len(column_boxes)!=len(previous_boxes):
            column_boxes=list(previous_boxes)
        if len(column_boxes)==len(previous_boxes) and all(0<=int(v)<len(column_boxes) for v in previous_roles.values()):
            role_indices={k:int(v) for k,v in previous_roles.items()}
            mapping={role:column_boxes[idx] for role,idx in role_indices.items()}
            previous_headers=list((inherited_layout or {}).get('headers') or [])
            if len(previous_headers)==len(column_boxes): headers=previous_headers
            else: headers=[f'Column {i+1}' for i in range(len(column_boxes))]
            return {'kind':kind,'img':img,'bands':bands,'table':table,'mapping':mapping,
                    'headers':headers,'column_boxes':column_boxes,'role_indices':role_indices,
                    'confidence':95,'source':'inherited continuation / '+geometry_source,
                    'warnings':[],'fingerprint':(inherited_layout or {}).get('fingerprint') or '',
                    'header_band_index':None,'master_pair_score':0,'master_pair_second':0,
                    'orientation_deg':orientation_deg,'inherited_layout':True}

    warnings=[]; assisted_score=0; assisted_second=0
    if ('up' not in role_indices or 'down' not in role_indices) and column_boxes:
        pair,assisted_score,assisted_second=_master_assisted_endpoint_columns(img,bands,table,column_boxes,master_index)
        if pair:
            role_indices['up'],role_indices['down']=pair
            mapping['up'],mapping['down']=column_boxes[pair[0]],column_boxes[pair[1]]
            source='master-assisted'
        else: warnings.append('ENDPOINT COLUMNS NEED CONFIRMATION')
    missing=[r for r in ('up','down','value','date') if r not in role_indices]
    if missing: warnings.append('MISSING COLUMN ROLES: '+', '.join(x.upper() for x in missing))
    confidence=100 if not missing and source=='header' and geometry_source=='vertical grid' else (85 if not missing else max(30,75-15*len(missing)))
    fingerprint=hashlib.sha1((kind+'|'+ '|'.join(re.sub(r'[^a-z0-9]+','',x.lower()) for x in headers)).encode()).hexdigest()
    return {'kind':kind,'img':img,'bands':bands,'table':table,'mapping':mapping,'headers':headers,
            'column_boxes':column_boxes,'role_indices':role_indices,'confidence':confidence,
            'source':source+' / '+geometry_source,'warnings':warnings,'fingerprint':fingerprint,
            'header_band_index':header_band_index,
            'master_pair_score':assisted_score,'master_pair_second':assisted_second,
            'orientation_deg':orientation_deg,'inherited_layout':False}
''')

source = replace_once(
    source,
    "def parse_year15_manholes(page, master_index, on_row=None, on_progress=None):\n    asset_format=master_index.get('asset_format')\n    img=_year15_oriented(page,'manholes'); h,w=img.shape[:2]",
    "def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):\n    asset_format=master_index.get('asset_format')\n    img=_year15_oriented(page,'manholes',preferred_deg=orientation_deg); h,w=img.shape[:2]"
)

source = replace_once(
    source,
    "self.pdf_path=tk.StringVar(master=self); self.master_path=tk.StringVar(master=self); self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.pdf_hash=''",
    "self.pdf_path=tk.StringVar(master=self); self.master_path=tk.StringVar(master=self); self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.unprocessed_pages=[]; self.pdf_hash=''"
)
source = replace_once(
    source,
    "self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.pdf_hash=''\n        if hasattr(self,'tree'):",
    "self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.unprocessed_pages=[]; self.pdf_hash=''\n        if hasattr(self,'tree'):"
)
source = replace_once(
    source,
    "self.tree.tag_configure('check_warning', background='#ffcccc', foreground='#7a0000')",
    "self.tree.tag_configure('check_warning', background='#ffcccc', foreground='#7a0000')\n        self.tree.tag_configure('page_error', background='#8b0000', foreground='white')"
)

method_marker = "    def _total_error_iid(self,check):\n"
if method_marker not in source:
    raise AssertionError('App total-error method marker missing')
page_methods = r'''    def add_unprocessed_page(self,wo,page_number,kind,reason):
        """Record one nonfatal page failure and keep a grouped warning at the top."""
        entry={'wo':str(wo or 'UNKNOWN').strip() or 'UNKNOWN','page':int(page_number),
               'kind':str(kind or 'unknown').strip(),'reason':re.sub(r'\s+',' ',str(reason or '')).strip()}
        key=(entry['wo'],entry['page'])
        for existing in self.unprocessed_pages:
            if (existing.get('wo'),existing.get('page'))==key:
                if entry['kind'] and existing.get('kind') in ('','unknown','other'): existing['kind']=entry['kind']
                if entry['reason']: existing['reason']=entry['reason']
                self.refresh_unprocessed_summary(); return
        self.unprocessed_pages.append(entry)
        self.refresh_unprocessed_summary()

    def refresh_unprocessed_summary(self):
        """Render one top summary row per affected W/O, listing every failed page."""
        if not hasattr(self,'tree'): return
        for iid in list(self.tree.get_children()):
            if str(iid).startswith('page-error:'):
                self.tree.delete(iid)
        grouped={}; order=[]
        for entry in self.unprocessed_pages:
            wo=entry.get('wo') or 'UNKNOWN'
            if wo not in grouped:
                grouped[wo]=[]; order.append(wo)
            grouped[wo].append(entry)
        for wo in reversed(order):
            entries=sorted(grouped[wo],key=lambda item:int(item.get('page') or 0))
            pages=', '.join(str(item.get('page')) for item in entries)
            kinds=', '.join(dict.fromkeys(str(item.get('kind') or '').title() for item in entries if item.get('kind')))
            status=f"PAGES {pages} COULD NOT BE PROCESSED"
            if kinds: status+=f" — {kinds}"
            iid='page-error:'+hashlib.sha1(str(wo).encode()).hexdigest()[:16]
            self.tree.insert('',0,iid=iid,values=('UNPROCESSED','','','',wo,'','',status),tags=('page_error',))
        try: self.update_idletasks()
        except Exception: pass

'''
source = source.replace(method_marker, page_methods + method_marker, 1)

source = replace_once(
    source,
    "        if iid.startswith('group-error:'):\n            messagebox.showinfo('Work Order Validation','This row is the work-order total-length status separator, not an individual asset row.',parent=self)\n            return",
    "        if iid.startswith('page-error:'):\n            messagebox.showinfo('Unprocessed PDF Page','This is an analysis warning row. The listed PDF page(s) could not be processed, while readable pages were kept.',parent=self)\n            return\n        if iid.startswith('group-error:'):\n            messagebox.showinfo('Work Order Validation','This row is the work-order total-length status separator, not an individual asset row.',parent=self)\n            return"
)
source = replace_once(
    source,
    "self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.tree.delete(*self.tree.get_children())",
    "self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.unprocessed_pages=[]; self.tree.delete(*self.tree.get_children())"
)

layout_start = "            # Prepare and confirm every unique pair-table layout before any asset\n"
stage2_marker = "            # Stage 2: every work order is now confirmed. Process spreadsheet pages\n"
new_layout_stage = r'''            # Assign list type/orientation to headerless continuation pages. Every
            # continuation is scoped to the preceding confirmed table inside the
            # SAME work order; Pipe, Cleaning, and Manhole all use this rule.
            active_wo=None; inherited_kind=None; inherited_deg=None
            for item in page_info:
                raw_kind=item['kind']
                if raw_kind=='workorder':
                    active_wo=confirmed_by_page.get(item['index'])
                    inherited_kind=None; inherited_deg=None
                    item['effective_kind']='workorder'; item['is_continuation']=False
                elif raw_kind=='trouble':
                    inherited_kind=None; inherited_deg=None
                    item['effective_kind']='trouble'; item['is_continuation']=False
                elif raw_kind in ('pipes','manholes','cleaning'):
                    inherited_kind=raw_kind; inherited_deg=item.get('deg')
                    item['effective_kind']=raw_kind; item['effective_deg']=inherited_deg
                    item['is_continuation']=False
                elif raw_kind=='other' and inherited_kind:
                    item['effective_kind']=inherited_kind; item['effective_deg']=inherited_deg
                    item['is_continuation']=True
                else:
                    item['effective_kind']=raw_kind; item['is_continuation']=False
                item['work_order']=active_wo

            confirmed_layouts={}; saved_layouts=load_layout_profiles()
            if idx.get('profile') in ('year15','phase2_year1'):
                last_pair_layout={}; pair_items=[]
                for item in page_info:
                    kind=item.get('effective_kind')
                    if kind in ('pipes','cleaning'):
                        pair_items.append(item); continue
                    if kind=='other' and item.get('work_order'):
                        options=[]
                        for candidate_kind in ('cleaning','pipes'):
                            candidate=prepare_year15_pair_layout(item['page'],idx,candidate_kind)
                            roles=candidate.get('role_indices',{})
                            if all(x in roles for x in ('up','down')) and candidate.get('column_boxes'):
                                options.append((len(roles),candidate.get('master_pair_score',0),candidate.get('confidence',0),candidate_kind,candidate))
                        if options:
                            _,_,_,chosen_kind,chosen=max(options,key=lambda x:x[:3])
                            item['effective_kind']=chosen_kind; item['preprepared_layout']=chosen
                            item['effective_deg']=chosen.get('orientation_deg'); pair_items.append(item)

                for n,item in enumerate(pair_items,1):
                    kind=item['effective_kind']; pi=item['index']
                    wo_info=item.get('work_order') or {}; wo=str(wo_info.get('wo') or 'UNKNOWN')
                    template_key=(wo,kind)
                    inherited=last_pair_layout.get(template_key) if item.get('is_continuation') else None
                    self.status.set(f'Preparing table layout {n} of {len(pair_items)}...'); self.pump_analysis_ui()
                    layout=item.pop('preprepared_layout',None) or prepare_year15_pair_layout(
                        item['page'],idx,kind,inherited_layout=inherited,
                        preferred_deg=item.get('effective_deg') if item.get('is_continuation') else None)
                    roles=layout.get('role_indices',{})
                    if (not layout.get('column_boxes') or
                            not all(role in roles for role in ('up','down','value','date'))):
                        self.add_unprocessed_page(wo,pi+1,kind,'table layout could not be resolved safely')
                        item['skip_processing']=True
                        continue

                    if layout.get('inherited_layout'):
                        item['pair_layout']=layout
                        last_pair_layout[template_key]=layout
                        continue

                    fingerprint=layout.get('fingerprint') or f'{kind}-page-{pi+1}'
                    if fingerprint in confirmed_layouts:
                        apply_confirmed_layout(layout,confirmed_layouts[fingerprint])
                    else:
                        detected_roles=layout.get('role_indices',{})
                        if layout.get('confidence',0)>80 and all(k in detected_roles for k in ('up','down','value','date')):
                            confirmed_layouts[fingerprint]=dict(detected_roles)
                        else:
                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                                if dlg.result is None:
                                    self.status.set('Analysis cancelled.'); return
                                confirmed_layouts[fingerprint]=dlg.result
                                apply_confirmed_layout(layout,dlg.result)
                                save_layout_profile(fingerprint,layout,dlg.result)
                    item['pair_layout']=layout
                    last_pair_layout[template_key]=layout
'''
source = replace_between(source, layout_start, stage2_marker, new_layout_stage)

stage2_loop_start = "            ignored_pages=[]; validation_reports=[]; total_sources={}\n"
verify_marker = "            self.verify_length_totals(total_sources)\n"
new_stage2_loop = r'''            ignored_pages=[]; validation_reports=[]; total_sources={}
            for item in page_info:
                pi=item['index']; page=item['page']; txt=item['text']; kind=item.get('effective_kind',item['kind'])
                if kind=='workorder':
                    current_wo=confirmed_by_page[pi]
                    group_no += 1
                    current_list_kind=None
                    current_report_date=None
                    continue

                self.status.set(f'Processing spreadsheet pages: page {pi+1} of {len(doc)}...'); self.pump_analysis_ui()

                if kind=='trouble':
                    try:
                        ticket=parse_trouble_ticket(page,pi+1,current_wo,self.pdf_path.get())
                    except AnalysisCancelled:
                        raise
                    except Exception as exc:
                        self.add_unprocessed_page((current_wo or {}).get('wo'),pi+1,'trouble',f'trouble-ticket parser error: {exc}')
                        current_list_kind=None
                        continue
                    if ticket['ticket_key'] not in {t['ticket_key'] for t in self.trouble_tickets}:
                        self.trouble_tickets.append(ticket)
                        self.status.set(f'Processing page {pi+1} — {len(self.trouble_tickets)} trouble ticket(s) found...')
                        self.show_summary_ticket(len(self.trouble_tickets)-1,follow=True)
                    current_list_kind=None
                    continue

                if current_wo is None:
                    ignored_pages.append((pi+1,'no preceding confirmed work order'))
                    continue

                if kind in ('pipes','manholes','cleaning'):
                    current_list_kind=kind
                elif kind=='other' and current_list_kind:
                    kind=current_list_kind
                else:
                    ignored_pages.append((pi+1,'unrecognized or irrelevant document'))
                    continue

                if item.get('skip_processing'):
                    continue

                page_date=parse_date_text(txt)
                if page_date:
                    current_report_date=page_date
                if idx.get('profile') in ('year15','phase2_year1'):
                    use_date=current_wo.get('date') or current_report_date or page_date
                else:
                    use_date=current_report_date or current_wo.get('date') or parse_date_text(txt)

                emit=lambda rec: self.commit_extracted_record(rec,current_wo,use_date,idx,pi+1,processed)
                try:
                    if idx.get('profile') in ('year15', 'phase2_year1'):
                        if kind=='pipes':
                            data=parse_year15_pair_list(page,idx,'pipes',item.get('pair_layout'),emit,self.pump_analysis_ui,use_date)
                        elif kind=='cleaning':
                            data=parse_year15_pair_list(page,idx,'cleaning',item.get('pair_layout'),emit,self.pump_analysis_ui,use_date)
                        else:
                            data=parse_year15_manholes(page,idx,emit,self.pump_analysis_ui,item.get('effective_deg'))
                    else:
                        data=parse_pipe_list(page,idx,txt,emit,self.pump_analysis_ui) if kind=='pipes' else parse_manhole_list(page,idx,txt,emit,self.pump_analysis_ui)
                except AnalysisCancelled:
                    raise
                except Exception as exc:
                    self.add_unprocessed_page(current_wo.get('wo'),pi+1,kind,f'{kind} parser error: {exc}')
                    continue

                if not data:
                    self.add_unprocessed_page(current_wo.get('wo'),pi+1,kind,'zero readable asset rows')
                    continue

                if idx.get('profile') in ('year15','phase2_year1') and kind in ('pipes','cleaning'):
                    layout=item.get('pair_layout') or {}
                    check_kind='Cleaning' if kind=='cleaning' else 'Pipe'
                    total_sources.setdefault((str(current_wo.get('wo','')),check_kind),[]).append(
                        {'page':pi+1,'info':dict(layout.get('printed_total_info') or {}),
                         'continuation':bool(item.get('is_continuation'))})
                report=validate_page_rows(data,kind,txt,pi+1,item.get('pair_layout'),idx.get('profile'))
                validation_reports.append(report)

            incomplete_total_keys=set()
            for failure in self.unprocessed_pages:
                failure_kind=str(failure.get('kind') or '').lower()
                if failure_kind in ('pipes','pipe'):
                    incomplete_total_keys.add((str(failure.get('wo') or ''),'Pipe'))
                elif failure_kind=='cleaning':
                    incomplete_total_keys.add((str(failure.get('wo') or ''),'Cleaning'))
            safe_total_sources={key:value for key,value in total_sources.items() if key not in incomplete_total_keys}
            self.verify_length_totals(safe_total_sources)
'''
start = source.find(stage2_loop_start)
if start < 0:
    raise AssertionError('stage2 loop start missing')
end = source.find(verify_marker, start)
if end < 0:
    raise AssertionError('verify marker missing')
end += len(verify_marker)
source = source[:start] + new_stage2_loop.rstrip() + '\n' + source[end:]

old_status_block = r'''        if length_warnings or total_failures or other_warnings or validation_warning_count or ticket_reviews:
            bits=[]
            if total_failures: bits.append(f'{total_failures} TOTAL LENGTH VALIDATION FAILURE(S) — UPDATE MASTER BLOCKED')
            if length_warnings: bits.append(f'{length_warnings} length difference warning(s) > {LENGTH_DIFF_THRESHOLD:.1f}')
            if other_warnings: bits.append(f'{other_warnings} other row(s) need review')
            if validation_warning_count: bits.append(f'{validation_warning_count} page validation warning(s)')
            if ticket_reviews: bits.append(f'{ticket_reviews} trouble ticket(s) need review')
            self.status.set(f"Found {len(self.records)} master update row(s) and {len(self.trouble_tickets)} trouble ticket(s) from {group_no} work order(s); ignored {len(ignored_pages)} PDF page(s). " + '; '.join(bits) + '.')
        else:
            suffix=' All extracted items are ready.'
            self.status.set(f'Found {len(self.records)} master update row(s) and {len(self.trouble_tickets)} trouble ticket(s) from {group_no} work order(s); ignored {len(ignored_pages)} PDF page(s).'+suffix)
'''
new_status_block = r'''        unprocessed_count=len({(str(item.get('wo')),int(item.get('page') or 0)) for item in self.unprocessed_pages})
        if length_warnings or total_failures or other_warnings or validation_warning_count or ticket_reviews or unprocessed_count:
            bits=[]
            if unprocessed_count: bits.append(f'{unprocessed_count} PDF PAGE(S) COULD NOT BE PROCESSED — SEE TOP SUMMARY')
            if total_failures: bits.append(f'{total_failures} TOTAL LENGTH VALIDATION FAILURE(S) — UPDATE MASTER BLOCKED')
            if length_warnings: bits.append(f'{length_warnings} length difference warning(s) > {LENGTH_DIFF_THRESHOLD:.1f}')
            if other_warnings: bits.append(f'{other_warnings} other row(s) need review')
            if validation_warning_count: bits.append(f'{validation_warning_count} page validation warning(s)')
            if ticket_reviews: bits.append(f'{ticket_reviews} trouble ticket(s) need review')
            self.status.set(f"Found {len(self.records)} master update row(s) and {len(self.trouble_tickets)} trouble ticket(s) from {group_no} work order(s); ignored {len(ignored_pages)} PDF page(s). " + '; '.join(bits) + '.')
        else:
            suffix=' All extracted items are ready.'
            self.status.set(f'Found {len(self.records)} master update row(s) and {len(self.trouble_tickets)} trouble ticket(s) from {group_no} work order(s); ignored {len(ignored_pages)} PDF page(s).'+suffix)
'''
source = replace_once(source, old_status_block, new_status_block)

for required in (
    'def parse_pipe_list(', 'def parse_manhole_list(', 'def parse_year15_pair_list(',
    'def parse_year15_manholes(', 'def parse_trouble_ticket(',
    'def _year15_recover_vertical_rules(', 'inherited_layout=None',
    'def add_unprocessed_page(', 'safe_total_sources=',
    "item['is_continuation']=True", 'preferred_deg=orientation_deg'):
    if required not in source:
        raise AssertionError(required)

ast.parse(source)
APP.write_text(source,encoding='utf-8')
print('Applied v88 continuation + nonfatal-page patch.')
