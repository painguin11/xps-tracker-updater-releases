from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
text=path.read_text(encoding='utf-8')

# Add pure date-evidence helpers immediately before _choose_length.
marker='def _choose_length(cands, expected=None):\n'
if marker not in text:
    raise SystemExit('choose_length marker not found')
helpers=r'''def _parse_sheet_date_text_candidates(text, expected_date=None):
    """Return candidate sheet dates plus whether the printed year was read exactly.

    OCR frequently damages the 4-digit year while leaving month/day usable.  When
    an expected work-order/report date is available, its year may repair only the
    year component; month/day still come from the printed cell.
    """
    expected_year=expected_date.year if isinstance(expected_date,datetime) else None
    tokens=re.findall(r'\d+',str(text or ''))
    out=[]
    for i in range(max(0,len(tokens)-2)):
        a_s,b_s,c_s=tokens[i:i+3]
        try: a,b,c=map(int,(a_s,b_s,c_s))
        except Exception: continue
        strong=False; repaired=False
        if 2020<=a<=2100:
            y,d,m=a,b,c; strong=len(a_s)==4
        else:
            m,d,y=a,b,c
            if y<100: y=2000+y
            strong=(len(c_s)==4 and 2020<=y<=2100)
        if expected_year and y!=expected_year:
            y=expected_year; repaired=True; strong=False
        if not (2020<=y<=2100 and 1<=m<=12 and 1<=d<=31):
            continue
        try: out.append((datetime(y,m,d),bool(strong and not repaired)))
        except Exception: pass
    return out


def _choose_sheet_date_evidence(texts, expected_date=None):
    """Choose one row date while preserving clearly printed full dates."""
    candidates=[]
    for txt in texts or []:
        candidates.extend(_parse_sheet_date_text_candidates(txt,expected_date))
    if not candidates:
        return {'date':None,'strong':False,'candidates':[]}
    strong_dates=[d for d,strong in candidates if strong]
    pool=strong_dates or [d for d,strong in candidates]
    counts={d:pool.count(d) for d in set(pool)}
    most=max(counts.values())
    winners=sorted((d for d,n in counts.items() if n==most))
    if strong_dates:
        chosen=winners[0]
        return {'date':chosen,'strong':True,'candidates':[d for d,_ in candidates]}
    if isinstance(expected_date,datetime) and expected_date in counts:
        chosen=expected_date
    else:
        chosen=winners[0]
    return {'date':chosen,'strong':False,'candidates':[d for d,_ in candidates]}


def _read_sheet_date_evidence(cell_img, expected_date=None):
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return {'date':None,'strong':False,'candidates':[]}
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    gray=cv2.resize(gray,None,fx=2.2,fy=2.2,interpolation=cv2.INTER_CUBIC)
    variants=[gray,cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    texts=[]
    for im in variants:
        for psm in (7,6):
            texts.append(cached_ocr_string(im,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/').strip())
    return _choose_sheet_date_evidence(texts,expected_date)


def _dominant_sheet_date(evidences, expected_date=None):
    """Return a repeated table date only when several rows independently support it."""
    dates=[ev.get('date') for ev in evidences or [] if ev.get('date') is not None]
    if not dates: return None
    counts={d:dates.count(d) for d in set(dates)}
    if isinstance(expected_date,datetime) and counts.get(expected_date,0)>=3:
        return expected_date
    ranked=sorted(((n,d) for d,n in counts.items()),reverse=True)
    best_n,best_d=ranked[0]
    second_n=ranked[1][0] if len(ranked)>1 else 0
    if best_n>=3 and best_n>second_n:
        return best_d
    return None


def _ocr_gridless_number_candidates(cell_img, decimal=False):
    """OCR a numeric cell after removing printed table rules.

    Total rows often put the digits directly against the bottom border; ordinary
    OCR can then see only one digit.  Morphologically removing horizontal/vertical
    rules keeps the number independent from the row grid.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0: return []
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    wl='0123456789.' if decimal else '0123456789'
    found=[]
    for threshold in (190,200,210,220):
        inv=cv2.threshold(gray,threshold,255,cv2.THRESH_BINARY_INV)[1]
        hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(8,int(cell_img.shape[1]*.45)),1))
        vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(8,int(cell_img.shape[0]*.45))))
        lines=cv2.bitwise_or(cv2.morphologyEx(inv,cv2.MORPH_OPEN,hk),
                             cv2.morphologyEx(inv,cv2.MORPH_OPEN,vk))
        clean=255-cv2.subtract(inv,lines)
        for psm in (11,6,7):
            raw=cached_ocr_string(clean,config=f'--psm {psm} -c tessedit_char_whitelist={wl}').strip()
            if decimal:
                for value in re.findall(r'\d+(?:\.\d+)?',raw.replace(',','')):
                    try: found.append(float(value))
                    except Exception: pass
            else:
                found.extend(re.findall(r'\d+',raw))
    return found


def _printed_total_value_is_plausible(value, band_count):
    if value is None: return False
    try: numeric=float(value)
    except Exception: return False
    if not (0<numeric<1000000): return False
    # A lone digit from a table with many rows is almost certainly a clipped OCR
    # fragment. Fail closed and ask the user rather than treating it as a total.
    if int(band_count or 0)>=6 and numeric<10: return False
    return True


'''
text=text.replace(marker,helpers+marker,1)

# Replace the printed-total reader so it checks a final in-grid total row first.
start=text.index('def _read_pair_table_printed_total(')
end=text.index('\ndef _resolve_printed_total_sources',start)
new_total=r'''def _read_pair_table_printed_total(img,bands,table,value_box,up_box=None,dn_box=None,date_box=None):
    """Read the printed activity total independently from the data-row lengths."""
    result={'found':False,'value':None,'confident':False,'candidates':[],'method':'not found'}
    if img is None or not bands or not table or not value_box: return result
    left,right=table; h,w=img.shape[:2]; tw=max(1,right-left)

    def cut(box,y1,y2):
        if not box: return None
        return img[max(0,int(y1)):min(h,int(y2)),
                   max(0,int(left+box[0]*tw)):min(w,int(left+box[1]*tw))]

    def read_value(y1,y2):
        cell=cut(value_box,y1,y2)
        if cell is None or cell.size==0: return []
        found=[]; width=cell.shape[1]
        for ratio in (0,.015,.030,.045,.060):
            pad=max(0,int(round(width*ratio)))
            sample=cell[:,pad:width-pad] if pad and width>pad*2+4 else cell
            found.extend(_ocr_digits(sample,True,fast_plain=True))
        # Total digits commonly touch the grid border, so also remove the printed
        # rules before OCR. This is what recovers 4476 from the 8-11 fixture.
        found.extend(_ocr_gridless_number_candidates(cell,True))
        if not found: found.extend(_ocr_digits(cell,True,fast_plain=False))
        return found

    def neighbor_has_number(box,y1,y2):
        cell=cut(box,y1,y2)
        if cell is None or cell.size==0: return False
        txt=' '.join(ocr_text(cell,psm) for psm in (6,11))
        return bool(re.search(r'\d{2,}',txt))

    def date_signal(y1,y2):
        cell=cut(date_box,y1,y2)
        if cell is None or getattr(cell,'size',0)==0: return False
        return _parse_sheet_date(cell) is not None

    def blank_total_row(y1,y2,method):
        candidates=read_value(y1,y2)
        if not candidates: return None
        if neighbor_has_number(up_box,y1,y2) or neighbor_has_number(dn_box,y1,y2) or date_signal(y1,y2):
            return None
        value,confident=_choose_printed_total(candidates)
        if not _printed_total_value_is_plausible(value,len(bands)):
            value=None; confident=False
        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':method}

    # Explicit TOTAL label, when present.
    for y1,y2 in list(bands)[-4:]:
        row=img[max(0,y1):min(h,y2),max(0,left):min(w,right)]
        if row.size==0: continue
        row_text=' '.join(ocr_text(row,psm) for psm in (6,11)).lower()
        compact=re.sub(r'[^a-z]+','',row_text)
        if not any(token in compact for token in ('total','tota','totai','totl')): continue
        candidates=read_value(y1,y2)
        value,confident=_choose_printed_total(candidates)
        if not _printed_total_value_is_plausible(value,len(bands)):
            value=None; confident=False
        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':'labelled total row'}

    # Some B&C sheets include the numeric total as the FINAL DETECTED GRID BAND.
    # v71/v72 incorrectly assumed the total was always below bands[-1], causing
    # 4476 on 8-11-2026 to be skipped and a stray single 4 to be accepted instead.
    in_grid=blank_total_row(bands[-1][0],bands[-1][1],'in-grid footer total')
    if in_grid is not None:
        return in_grid

    # Other sheets put one blank footer row immediately below the final detected
    # data band. Keep that path as a fallback.
    typical=float(statistics.median(max(1,b-a) for a,b in bands))
    fy1=max(0,int(bands[-1][1]-typical*.05))
    fy2=min(h,int(bands[-1][1]+typical*2.10))
    below=blank_total_row(fy1,fy2,'blank footer total')
    return below if below is not None else result

'''
text=text[:start]+new_total+text[end+1:]

# Pair-list parser: pre-read date evidence for the whole table, then correct only
# weak OCR using a repeated dominant date. Strong full YYYY dates are preserved.
old_sig="def parse_year15_pair_list(page, master_index, kind, prepared=None, on_row=None, on_progress=None):"
new_sig="def parse_year15_pair_list(page, master_index, kind, prepared=None, on_row=None, on_progress=None, expected_date=None):"
if old_sig not in text: raise SystemExit('pair parser signature not found')
text=text.replace(old_sig,new_sig,1)

marker='    endpoint_items={}\n'
insert=r'''    expected_date=expected_date if isinstance(expected_date,datetime) else None
    date_reads={}
    for date_band_index,(date_y1,date_y2) in enumerate(bands):
        date_cell=img[date_y1:date_y2,
                      max(0,int(left+date_box[0]*tw)):min(w,int(left+date_box[1]*tw))]
        date_reads[date_band_index]=_read_sheet_date_evidence(date_cell,expected_date)
    dominant_date=_dominant_sheet_date(list(date_reads.values()),expected_date)

'''
if marker not in text: raise SystemExit('endpoint_items marker not found')
text=text.replace(marker,insert+marker,1)

old="""        d=_parse_sheet_date(cut(date_box))\n        endpoint_signal=any(re.search(r'\\d',x) for x in up_obs+dn_obs)\n"""
new="""        date_evidence=date_reads.get(band_index,{'date':None,'strong':False,'candidates':[]})\n        d=date_evidence.get('date')\n        endpoint_signal=any(re.search(r'\\d',x) for x in up_obs+dn_obs)\n        if dominant_date is not None and (match or endpoint_signal) and not date_evidence.get('strong'):\n            d=dominant_date\n"""
if old not in text: raise SystemExit('row date block not found')
text=text.replace(old,new,1)

old_p="data=parse_year15_pair_list(page,idx,'pipes',item.get('pair_layout'),emit,self.pump_analysis_ui)"
new_p="data=parse_year15_pair_list(page,idx,'pipes',item.get('pair_layout'),emit,self.pump_analysis_ui,use_date)"
old_c="data=parse_year15_pair_list(page,idx,'cleaning',item.get('pair_layout'),emit,self.pump_analysis_ui)"
new_c="data=parse_year15_pair_list(page,idx,'cleaning',item.get('pair_layout'),emit,self.pump_analysis_ui,use_date)"
if old_p not in text or old_c not in text: raise SystemExit('pair parser call not found')
text=text.replace(old_p,new_p,1).replace(old_c,new_c,1)

path.write_text(text,encoding='utf-8')

# Pure/static regression for the newly discovered failures.
test=Path('working_source/tests/regression_v73_total_dates.py')
test.write_text(r'''import ast,re
from datetime import datetime
from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
text=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(text)
wanted={'_parse_sheet_date_text_candidates','_choose_sheet_date_evidence','_dominant_sheet_date','_printed_total_value_is_plausible'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
ns={'re':re,'datetime':datetime}; exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),ns)
expected=datetime(2026,8,11)
strong=ns['_choose_sheet_date_evidence'](['8/11/2026'],expected)
assert strong['date']==expected and strong['strong']
weak=ns['_choose_sheet_date_evidence'](['8/11/9026'],expected)
assert weak['date']==expected and not weak['strong']
other=ns['_choose_sheet_date_evidence'](['8/12/2026'],expected)
assert other['date']==datetime(2026,8,12) and other['strong']
reads=[
 {'date':datetime(2026,8,17),'strong':False},
 {'date':datetime(2026,1,11),'strong':False},
 {'date':datetime(2026,2,11),'strong':False},
 {'date':expected,'strong':False},{'date':expected,'strong':False},
 {'date':expected,'strong':False},{'date':expected,'strong':True},{'date':expected,'strong':False},
 {'date':datetime(2026,9,11),'strong':False},
]
assert ns['_dominant_sheet_date'](reads,expected)==expected
assert not ns['_printed_total_value_is_plausible'](4,19)
assert ns['_printed_total_value_is_plausible'](4476,19)
assert 'in-grid footer total' in text
assert '_ocr_gridless_number_candidates(cell,True)' in text
assert 'dominant_date=_dominant_sheet_date' in text
assert "self.pump_analysis_ui,use_date)" in text
print('v73 total-row and date-consensus safeguards passed.')
''',encoding='utf-8')
