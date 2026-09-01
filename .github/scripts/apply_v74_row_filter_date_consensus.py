from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
text=path.read_text(encoding='utf-8')

# Strengthen date evidence: record per-date vote counts so an isolated bad full-date
# OCR does not defeat an overwhelming same-table date consensus.
old="""def _choose_sheet_date_evidence(texts, expected_date=None):\n    \"\"\"Choose one row date while preserving clearly printed full dates.\"\"\"\n    candidates=[]\n    for txt in texts or []:\n        candidates.extend(_parse_sheet_date_text_candidates(txt,expected_date))\n    if not candidates:\n        return {'date':None,'strong':False,'candidates':[]}\n    strong_dates=[d for d,strong in candidates if strong]\n    pool=strong_dates or [d for d,strong in candidates]\n    counts={d:pool.count(d) for d in set(pool)}\n    most=max(counts.values())\n    winners=sorted((d for d,n in counts.items() if n==most))\n    if strong_dates:\n        chosen=winners[0]\n        return {'date':chosen,'strong':True,'candidates':[d for d,_ in candidates]}\n    if isinstance(expected_date,datetime) and expected_date in counts:\n        chosen=expected_date\n    else:\n        chosen=winners[0]\n    return {'date':chosen,'strong':False,'candidates':[d for d,_ in candidates]}\n"""
new="""def _choose_sheet_date_evidence(texts, expected_date=None):\n    \"\"\"Choose one row date and retain vote strength for table-level reconciliation.\"\"\"\n    candidates=[]\n    for txt in texts or []:\n        candidates.extend(_parse_sheet_date_text_candidates(txt,expected_date))\n    if not candidates:\n        return {'date':None,'strong':False,'candidates':[],'votes':{},'strong_votes':{}}\n    all_dates=[d for d,_ in candidates]\n    strong_dates=[d for d,strong in candidates if strong]\n    votes={d:all_dates.count(d) for d in set(all_dates)}\n    strong_votes={d:strong_dates.count(d) for d in set(strong_dates)}\n    pool=strong_dates or all_dates\n    counts={d:pool.count(d) for d in set(pool)}\n    most=max(counts.values())\n    winners=sorted((d for d,n in counts.items() if n==most))\n    if strong_dates:\n        chosen=winners[0]\n        return {'date':chosen,'strong':True,'candidates':all_dates,'votes':votes,'strong_votes':strong_votes}\n    if isinstance(expected_date,datetime) and expected_date in counts:\n        chosen=expected_date\n    else:\n        chosen=winners[0]\n    return {'date':chosen,'strong':False,'candidates':all_dates,'votes':votes,'strong_votes':strong_votes}\n"""
if old not in text:
    raise SystemExit('date evidence block not found')
text=text.replace(old,new,1)

# Add helper deciding whether an outlier date has enough repeated OCR support to
# remain distinct from an overwhelming table/work-order date.
marker="def _read_sheet_date_evidence(cell_img, expected_date=None):\n"
helper="""def _date_outlier_is_well_supported(evidence, dominant_date):\n    \"\"\"Keep a different date only when multiple OCR passes independently support it.\"\"\"\n    if not evidence or dominant_date is None: return False\n    date=evidence.get('date')\n    if date is None or date==dominant_date: return True\n    strong_votes=(evidence.get('strong_votes') or {}).get(date,0)\n    total_votes=(evidence.get('votes') or {}).get(date,0)\n    # One lucky/misread full-year pass is not enough. Requiring at least two\n    # independent strong reads (or three total matching reads) preserves genuine\n    # mixed-date tables while correcting isolated 01/01/2026-style OCR failures.\n    return strong_votes>=2 or total_votes>=3\n\n\n"""
if marker not in text:
    raise SystemExit('read date evidence marker not found')
text=text.replace(marker,helper+marker,1)

# Make the total reader identify which detected grid band contains the total so
# the row parser can skip it explicitly instead of hoping OCR signals suppress it.
text=text.replace("result={'found':False,'value':None,'confident':False,'candidates':[],'method':'not found'}",
                  "result={'found':False,'value':None,'confident':False,'candidates':[],'method':'not found','band_index':None}",1)
text=text.replace("def blank_total_row(y1,y2,method):",
                  "def blank_total_row(y1,y2,method,band_index=None):",1)
text=text.replace("return {'found':True,'value':value,'confident':confident,\n                'candidates':candidates,'method':method}",
                  "return {'found':True,'value':value,'confident':confident,\n                'candidates':candidates,'method':method,'band_index':band_index}",1)
# Labelled totals may be in one of the last four bands; enumerate so we know which.
old_label="""    for y1,y2 in list(bands)[-4:]:\n        row=img[max(0,y1):min(h,y2),max(0,left):min(w,right)]\n"""
new_label="""    tail_start=max(0,len(bands)-4)\n    for band_index,(y1,y2) in enumerate(list(bands)[-4:],tail_start):\n        row=img[max(0,y1):min(h,y2),max(0,left):min(w,right)]\n"""
if old_label not in text: raise SystemExit('labelled total loop not found')
text=text.replace(old_label,new_label,1)
text=text.replace("return {'found':True,'value':value,'confident':confident,\n                'candidates':candidates,'method':'labelled total row'}",
                  "return {'found':True,'value':value,'confident':confident,\n                'candidates':candidates,'method':'labelled total row','band_index':band_index}",1)
text=text.replace("in_grid=blank_total_row(bands[-1][0],bands[-1][1],'in-grid footer total')",
                  "in_grid=blank_total_row(bands[-1][0],bands[-1][1],'in-grid footer total',len(bands)-1)",1)
# Below-grid totals remain outside the band list, so band_index stays None.
text=text.replace("below=blank_total_row(fy1,fy2,'blank footer total')",
                  "below=blank_total_row(fy1,fy2,'blank footer total',None)",1)

# In the pair parser, read the printed total before parsing rows, and structurally
# exclude its band. Then reject unmatched edge/header/footer noise before any date
# consensus can turn it into an apparently valid row.
old="""    dominant_date=_dominant_sheet_date(list(date_reads.values()),expected_date)\n\n    endpoint_items={}\n"""
new="""    dominant_date=_dominant_sheet_date(list(date_reads.values()),expected_date)\n    printed_total_info=_read_pair_table_printed_total(\n        img,bands,table,val_box,up_box,dn_box,date_box)\n    total_band_index=printed_total_info.get('band_index')\n\n    endpoint_items={}\n"""
if old not in text: raise SystemExit('dominant date parser block not found')
text=text.replace(old,new,1)

# Add a stronger asset-like signal helper before the main band loop.
old="""    rows=[]; seen=set()\n    typical_band=float(np.median([max(1,b-a) for a,b in bands]))\n    for band_index,(y1,y2) in enumerate(bands):\n"""
new="""    rows=[]; seen=set()\n    typical_band=float(np.median([max(1,b-a) for a,b in bands]))\n    def has_asset_digit_signal(observations):\n        for raw in observations or []:\n            key=asset_key(raw)\n            if len(re.findall(r'\\d',key))>=2:\n                return True\n        return False\n    for band_index,(y1,y2) in enumerate(bands):\n        if total_band_index is not None and band_index==total_band_index:\n            # The printed total is validation evidence, never an asset row.\n            continue\n"""
if old not in text: raise SystemExit('rows loop block not found')
text=text.replace(old,new,1)

old="""        date_evidence=date_reads.get(band_index,{'date':None,'strong':False,'candidates':[]})\n        d=date_evidence.get('date')\n        endpoint_signal=any(re.search(r'\\d',x) for x in up_obs+dn_obs)\n        if dominant_date is not None and (match or endpoint_signal) and not date_evidence.get('strong'):\n            d=dominant_date\n        # Skip the header, footer total, and wrapped-comment continuation band.\n        # A tall retained header or final total can occasionally produce digit-like\n        # OCR noise even though it is neither a master pair nor a dated data row.\n        edge_band=band_index in (0,len(bands)-1)\n        tall_band=(y2-y1)>typical_band*1.45\n        if d is None and not match and (edge_band or tall_band): continue\n        if d is None and not endpoint_signal: continue\n"""
new="""        date_evidence=date_reads.get(band_index,{'date':None,'strong':False,'candidates':[],'votes':{},'strong_votes':{}})\n        d=date_evidence.get('date')\n        endpoint_signal=has_asset_digit_signal(up_obs) and has_asset_digit_signal(dn_obs)\n        # Structural filtering happens BEFORE date repair. Header labels such as\n        # UPMI/WOM and footer OCR noise must never become rows merely because a\n        # dominant table date can be inferred.\n        edge_band=band_index in (0,len(bands)-1)\n        tall_band=(y2-y1)>typical_band*1.45\n        if not match and (edge_band or tall_band) and not endpoint_signal:\n            continue\n        if not match and not endpoint_signal:\n            continue\n        if dominant_date is not None and (match or endpoint_signal):\n            if d is None or not _date_outlier_is_well_supported(date_evidence,dominant_date):\n                d=dominant_date\n        if d is None:\n            continue\n"""
if old not in text: raise SystemExit('date/edge filtering block not found')
text=text.replace(old,new,1)

old="""    prepared['printed_total_info']=_read_pair_table_printed_total(\n        img,bands,table,val_box,up_box,dn_box,date_box)\n    return rows\n"""
new="""    prepared['printed_total_info']=printed_total_info\n    return rows\n"""
if old not in text: raise SystemExit('printed total footer call not found')
text=text.replace(old,new,1)

path.write_text(text,encoding='utf-8')

# Static/pure regression guards for the exact v73 regression mechanisms.
test=Path('working_source/tests/regression_v74_row_filtering.py')
test.write_text(r'''import ast,re\nfrom datetime import datetime\nfrom pathlib import Path\n\nSOURCE=Path('working_source/app/reno_scan_updater.py')\ntext=SOURCE.read_text(encoding='utf-8')\ntree=ast.parse(text)\nwanted={'_date_outlier_is_well_supported'}\nnodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]\nns={}; exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)\ndom=datetime(2026,8,11)\nbad={'date':datetime(2026,1,1),'votes':{datetime(2026,1,1):1},'strong_votes':{datetime(2026,1,1):1}}\nassert not ns['_date_outlier_is_well_supported'](bad,dom)\nreal={'date':datetime(2026,8,12),'votes':{datetime(2026,8,12):3},'strong_votes':{datetime(2026,8,12):2}}\nassert ns['_date_outlier_is_well_supported'](real,dom)\nassert "'band_index':None" in text\nassert "'in-grid footer total',len(bands)-1" in text\nassert "if total_band_index is not None and band_index==total_band_index:" in text\nassert 'Structural filtering happens BEFORE date repair' in text\nassert 'has_asset_digit_signal(up_obs) and has_asset_digit_signal(dn_obs)' in text\nassert "prepared['printed_total_info']=printed_total_info" in text\nprint('v74 header/footer exclusion and date-outlier safeguards passed.')\n''',encoding='utf-8')
