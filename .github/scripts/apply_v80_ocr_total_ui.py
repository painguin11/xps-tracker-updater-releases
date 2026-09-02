from pathlib import Path
import re

APP = Path('working_source/app/reno_scan_updater.py')
UPDATER = Path('working_source/app/xps_update.py')
README = Path('working_source/app/README_XPS_Tracker_Updater.txt')
TEST = Path('working_source/tests/regression_v80_ocr_total_ui.py')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'{label}: expected source block not found; refusing broad edit')
    return text.replace(old, new, 1)


text = APP.read_text(encoding='utf-8')
text, n = re.subn(r"APP_VERSION = ['\"]\d+['\"]", "APP_VERSION = '80'", text, count=1)
if n != 1:
    raise SystemExit('APP_VERSION replacement failed')
text = replace_once(text, "OCR_CACHE_VERSION = 'v5'", "OCR_CACHE_VERSION = 'v6'", 'OCR cache version')

# Keep implausible far-future OCR years from becoming the packet's expected year.
old = '''def _parse_sheet_date_text_candidates(text, expected_date=None):\n    \"\"\"Return candidate sheet dates plus whether the printed year was read exactly.\n\n    OCR frequently damages the 4-digit year while leaving month/day usable.  When\n    an expected work-order/report date is available, its year may repair only the\n    year component; month/day still come from the printed cell.\n    \"\"\"\n    expected_year=expected_date.year if isinstance(expected_date,datetime) else None\n'''
new = '''def _plausible_sheet_year(year):\n    try:\n        year=int(year)\n    except Exception:\n        return False\n    # These packets are operational records, not future schedules. Allow older\n    # supported records plus a small clock/rollover cushion, but reject OCR years\n    # such as 2096 before they can become the table's expected year.\n    return 2020 <= year <= datetime.now().year + 2\n\n\ndef _parse_sheet_date_text_candidates(text, expected_date=None):\n    \"\"\"Return candidate sheet dates plus whether the printed year was read exactly.\n\n    OCR frequently damages the 4-digit year while leaving month/day usable.  When\n    an expected work-order/report date is available, its year may repair only the\n    year component; month/day still come from the printed cell.\n    \"\"\"\n    expected_year=(expected_date.year if isinstance(expected_date,datetime) and\n                   _plausible_sheet_year(expected_date.year) else None)\n'''
text = replace_once(text, old, new, 'plausible Year 15 date guard')
text = replace_once(
    text,
    "        if not (2020<=y<=2100 and 1<=m<=12 and 1<=d<=31):\n            continue\n",
    "        if not (_plausible_sheet_year(y) and 1<=m<=12 and 1<=d<=31):\n            continue\n",
    'date candidate plausibility')

# Resolve total-cell OCR conservatively: a repeated full-cell read wins before
# destructive grid removal or tighter crops are allowed to contribute.
old = '''def _choose_printed_total(cands):\n    \"\"\"Return a total-length OCR winner and whether its OCR vote is confident.\"\"\"\n    rounded=[round(float(x),2) for x in cands if 0<float(x)<1000000]\n    if not rounded: return None,False\n    counts={value:rounded.count(value) for value in set(rounded)}\n    most=max(counts.values())\n    winners=sorted(value for value,count in counts.items() if count==most)\n    if len(winners)!=1: return None,False\n    return winners[0],most>=2\n\n\ndef _read_pair_table_printed_total(img,bands,table,value_box,up_box=None,dn_box=None,date_box=None):\n'''
new = '''def _choose_printed_total(cands):\n    \"\"\"Return a total-length OCR winner and whether its OCR vote is confident.\"\"\"\n    rounded=[round(float(x),2) for x in cands if 0<float(x)<1000000]\n    if not rounded: return None,False\n    counts={value:rounded.count(value) for value in set(rounded)}\n    most=max(counts.values())\n    winners=sorted(value for value,count in counts.items() if count==most)\n    if len(winners)!=1: return None,False\n    return winners[0],most>=2\n\n\ndef _preferred_printed_total_candidates(direct,gridless,band_count):\n    \"\"\"Prefer the least-destructive total OCR source that is independently stable.\n\n    Tight crops and rule-removal are fallbacks, not equal votes. This prevents a\n    correctly repeated full-cell total from being outvoted by several damaged\n    variants while still letting rule-removal recover a total when the raw cell is\n    not independently stable.\n    \"\"\"\n    direct=list(direct or []); gridless=list(gridless or [])\n    value,confident=_choose_printed_total(direct)\n    if confident and _printed_total_value_is_plausible(value,band_count):\n        return direct,'direct full cell'\n    value,confident=_choose_printed_total(gridless)\n    if confident and _printed_total_value_is_plausible(value,band_count):\n        return gridless,'gridless fallback'\n    return direct+gridless,'combined fallback'\n\n\ndef _read_pair_table_printed_total(img,bands,table,value_box,up_box=None,dn_box=None,date_box=None):\n'''
text = replace_once(text, old, new, 'printed total source preference')

old = '''    def read_value(y1,y2):\n        cell=cut(value_box,y1,y2)\n        if cell is None or cell.size==0: return []\n        found=[]; width=cell.shape[1]\n        for ratio in (0,.015,.030,.045,.060):\n            pad=max(0,int(round(width*ratio)))\n            sample=cell[:,pad:width-pad] if pad and width>pad*2+4 else cell\n            found.extend(_ocr_digits(sample,True,fast_plain=True))\n        # Total digits commonly touch the grid border, so also remove the printed\n        # rules before OCR. This is what recovers 4476 from the 8-11 fixture.\n        found.extend(_ocr_gridless_number_candidates(cell,True))\n        if not found: found.extend(_ocr_digits(cell,True,fast_plain=False))\n        return found\n'''
new = '''    def read_value(y1,y2):\n        cell=cut(value_box,y1,y2)\n        if cell is None or cell.size==0: return []\n        # Start with the untouched full cell. Grid removal is intentionally only\n        # the second source because it can occasionally erase interior digits.\n        direct=_ocr_digits(cell,True,fast_plain=True)\n        gridless=_ocr_gridless_number_candidates(cell,True)\n        found,mode=_preferred_printed_total_candidates(direct,gridless,len(bands))\n        if mode!='combined fallback':\n            return found\n        # Only when neither primary source is independently stable do progressively\n        # tighter crops participate. They are fallbacks, not a pile of equal votes.\n        width=cell.shape[1]\n        for ratio in (.015,.030,.045,.060):\n            pad=max(0,int(round(width*ratio)))\n            if pad and width>pad*2+4:\n                found.extend(_ocr_digits(cell[:,pad:width-pad],True,fast_plain=True))\n        if not found: found.extend(_ocr_digits(cell,True,fast_plain=False))\n        return found\n'''
text = replace_once(text, old, new, 'total-cell OCR ladder')

# Keep the aligned-column OCR as primary, but if that single batch value is far
# from the master, verify only that cell with the established conservative reader.
old = '''        if kind=='cleaning':\n            value_candidates=list(batch_cleaning_values.get(band_index,[]))\n            if value_candidates:\n                value=_choose_cleaning_length(value_candidates,expected)\n            else:\n                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)\n                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)\n                value=_choose_cleaning_length(value_candidates,expected)\n                distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}\n                needs_consensus=(not value_candidates or value is None or len(distinct)>1 or\n                    (value is not None and expected not in (None,0) and\n                     abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))\n                if needs_consensus:\n                    consensus=list(value_candidates)\n                    width=value_cell.shape[1]\n                    for ratio in (.015,.030,.045,.060):\n                        pad=max(2,int(round(width*ratio)))\n                        if width>pad*2+4:\n                            consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))\n                    consensus.extend(_ocr_gridless_number_candidates(value_cell,True))\n                    value=_choose_cleaning_length(consensus,expected)\n'''
new = '''        if kind=='cleaning':\n            value_candidates=list(batch_cleaning_values.get(band_index,[]))\n            if value_candidates:\n                value=_choose_cleaning_length(value_candidates,expected)\n                batch_suspect=(value is None or (expected not in (None,0) and\n                    abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))\n                if batch_suspect:\n                    # The batch column reader is normally the cleanest source, but\n                    # a dropped digit can produce a single plausible-looking value.\n                    # Verify only that suspicious cell; do not use the total to\n                    # manufacture a replacement and do not rewrite unrelated rows.\n                    cell_candidates=_ocr_digits(value_cell,True,fast_plain=True)\n                    if not cell_candidates:\n                        cell_candidates=_ocr_digits(value_cell,True,fast_plain=False)\n                    consensus=list(value_candidates)+list(cell_candidates)\n                    cell_distinct={round(float(x),2) for x in cell_candidates if 0<float(x)<5000}\n                    if not cell_candidates or len(cell_distinct)>1:\n                        consensus.extend(_ocr_gridless_number_candidates(value_cell,True))\n                    if consensus:\n                        value_candidates=consensus\n                        value=_choose_cleaning_length(consensus,expected)\n            else:\n                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)\n                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)\n                value=_choose_cleaning_length(value_candidates,expected)\n                distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}\n                needs_consensus=(not value_candidates or value is None or len(distinct)>1 or\n                    (value is not None and expected not in (None,0) and\n                     abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))\n                if needs_consensus:\n                    consensus=list(value_candidates)\n                    width=value_cell.shape[1]\n                    for ratio in (.015,.030,.045,.060):\n                        pad=max(2,int(round(width*ratio)))\n                        if width>pad*2+4:\n                            consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))\n                    consensus.extend(_ocr_gridless_number_candidates(value_cell,True))\n                    value=_choose_cleaning_length(consensus,expected)\n'''
text = replace_once(text, old, new, 'suspicious batch cleaning fallback')

# For B&C packet tables, the work-order date is a safer year anchor than a noisy
# whole-page OCR date. Strong row-level evidence can still preserve a real outlier.
old = "                use_date=current_report_date or current_wo.get('date') or parse_date_text(txt)\n"
new = '''                if idx.get('profile') in ('year15','phase2_year1'):\n                    use_date=current_wo.get('date') or current_report_date or page_date\n                else:\n                    use_date=current_report_date or current_wo.get('date') or parse_date_text(txt)\n'''
text = replace_once(text, old, new, 'B&C date-source priority')

# UI state for work-order-level total outlines.
old = "        self.pdf_path=tk.StringVar(master=self); self.master_path=tk.StringVar(master=self); self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.pdf_hash=''\n        self._analysis_running=False; self.cancel_requested=False\n"
new = "        self.pdf_path=tk.StringVar(master=self); self.master_path=tk.StringVar(master=self); self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.pdf_hash=''\n        self._analysis_running=False; self.cancel_requested=False\n        self._total_outline_widgets=[]; self._total_outline_job=None; self._tree_yscroll=None\n"
text = replace_once(text, old, new, 'total outline state')

old = "        table_frame=ttk.LabelFrame(self,text='Extracted rows',padding=(8,7)); table_frame.pack(fill='both',expand=True,padx=14,pady=(6,10))\n        self.tree=ttk.Treeview(table_frame,columns=cols,show='headings',selectmode='browse')\n        xscroll=ttk.Scrollbar(table_frame,orient='horizontal',command=self.tree.xview)\n        yscroll=ttk.Scrollbar(table_frame,orient='vertical',command=self.tree.yview)\n        self.tree.configure(xscrollcommand=xscroll.set,yscrollcommand=yscroll.set)\n"
new = "        table_frame=ttk.LabelFrame(self,text='Extracted rows',padding=(8,7)); table_frame.pack(fill='both',expand=True,padx=14,pady=(6,10))\n        self.table_frame=table_frame\n        self.tree=ttk.Treeview(table_frame,columns=cols,show='headings',selectmode='browse')\n        xscroll=ttk.Scrollbar(table_frame,orient='horizontal',command=self.tree.xview)\n        yscroll=ttk.Scrollbar(table_frame,orient='vertical',command=self.tree.yview)\n        self._tree_yscroll=yscroll\n        self.tree.configure(xscrollcommand=xscroll.set,yscrollcommand=self._on_tree_yscroll)\n"
text = replace_once(text, old, new, 'tree outline frame setup')
text = replace_once(
    text,
    "        self.tree.bind('<Double-1>',self.edit_double_clicked)\n",
    "        self.tree.bind('<Double-1>',self.edit_double_clicked)\n        self.tree.bind('<Configure>',lambda _event:self._schedule_total_outlines(),add='+')\n",
    'tree outline resize binding')
text = replace_once(
    text,
    "        if hasattr(self,'tree'): self.tree.delete(*self.tree.get_children())\n",
    "        if hasattr(self,'tree'): self.tree.delete(*self.tree.get_children())\n        self._clear_total_outlines()\n",
    'clear total outlines with rows')

old = '''    def show_summary_record(self,index,follow=False):\n        \"\"\"Insert or refresh one summary row while analysis is still running.\"\"\"\n        r=self.records[index]\n        tags=()\n        if any(str(w).startswith('TOTAL LENGTH') for w in r.get('warnings',[])):\n            tags=('total_warning',)\n        elif str(r.get('status','')).startswith('LENGTH DIFF'):\n            tags=('length_warning',)\n        elif record_needs_review(r):\n            tags=('check_warning',)\n        values=(r['kind'],r['display_asset'],'' if r['video_length'] is None else f\"{r['video_length']:.1f}\",\n                fmt_date(r['date']),r['wo'],r['truck'],r['operator'],review_status(r))\n        iid=f'record:{index}'\n        if self.tree.exists(iid): self.tree.item(iid,values=values,tags=tags)\n        else: self.tree.insert('', 'end',iid=iid,values=values,tags=tags)\n        if follow: self.tree.see(iid)\n        # OCR runs synchronously on the GUI thread. update_idletasks() can leave\n        # native Windows painting queued until a long OCR loop ends, so process a\n        # complete Tk event cycle before starting the next row.\n        if getattr(self,'_analysis_running',False):\n            self.pump_analysis_ui()\n        else:\n            self.update_idletasks()\n'''
new = '''    def _on_tree_yscroll(self,first,last):\n        if self._tree_yscroll is not None:\n            self._tree_yscroll.set(first,last)\n        self._schedule_total_outlines()\n    def _clear_total_outlines(self):\n        for widget in list(getattr(self,'_total_outline_widgets',[]) or []):\n            try: widget.destroy()\n            except Exception: pass\n        self._total_outline_widgets=[]\n    def _schedule_total_outlines(self):\n        if not hasattr(self,'tree') or not hasattr(self,'table_frame'):\n            return\n        if getattr(self,'_total_outline_job',None) is not None:\n            try: self.after_cancel(self._total_outline_job)\n            except Exception: pass\n        try: self._total_outline_job=self.after_idle(self._draw_total_outlines)\n        except Exception: self._total_outline_job=None\n    def _draw_total_outlines(self):\n        self._total_outline_job=None\n        self._clear_total_outlines()\n        if not hasattr(self,'tree') or not self.tree.winfo_exists():\n            return\n        thickness=max(2,self.spx(2)); color='#d00000'\n        tree_x=self.tree.winfo_x(); tree_y=self.tree.winfo_y(); tree_w=max(1,self.tree.winfo_width())\n        for check in self.total_validations:\n            if check.get('passed'):\n                continue\n            indexed=self._total_check_records(check)\n            if not indexed:\n                continue\n            visible=[]\n            for record_index,_record in indexed:\n                iid=f'record:{record_index}'\n                if not self.tree.exists(iid):\n                    continue\n                bbox=self.tree.bbox(iid)\n                if bbox:\n                    visible.append((record_index,bbox))\n            if not visible:\n                continue\n            visible.sort(key=lambda item:item[0])\n            y_top=tree_y+min(box[1] for _,box in visible)\n            y_bottom=tree_y+max(box[1]+box[3] for _,box in visible)\n            height=max(thickness,y_bottom-y_top)\n            specs=[(tree_x,y_top,thickness,height),(tree_x+tree_w-thickness,y_top,thickness,height)]\n            first_index=indexed[0][0]; last_index=indexed[-1][0]\n            if any(i==first_index for i,_ in visible):\n                specs.append((tree_x,y_top,tree_w,thickness))\n            if any(i==last_index for i,_ in visible):\n                specs.append((tree_x,y_bottom-thickness,tree_w,thickness))\n            for x,y,width,line_height in specs:\n                frame=tk.Frame(self.table_frame,background=color,borderwidth=0,highlightthickness=0,takefocus=0)\n                frame.place(x=x,y=y,width=max(1,width),height=max(1,line_height))\n                frame.lift(); self._total_outline_widgets.append(frame)\n    def _total_warning_for_record_index(self,index):\n        for check in self.total_validations:\n            if check.get('passed') or check.get('first_record_index')!=index:\n                continue\n            return str(check.get('warning') or '')\n        return ''\n    def show_summary_record(self,index,follow=False):\n        \"\"\"Insert or refresh one summary row while analysis is still running.\"\"\"\n        r=self.records[index]\n        tags=()\n        if str(r.get('status','')).startswith('LENGTH DIFF'):\n            tags=('length_warning',)\n        elif record_needs_review(r):\n            tags=('check_warning',)\n        display_status=review_status(r)\n        group_warning=self._total_warning_for_record_index(index)\n        if group_warning:\n            display_status=group_warning if display_status=='Matched' else display_status+'; '+group_warning\n        values=(r['kind'],r['display_asset'],'' if r['video_length'] is None else f\"{r['video_length']:.1f}\",\n                fmt_date(r['date']),r['wo'],r['truck'],r['operator'],display_status)\n        iid=f'record:{index}'\n        if self.tree.exists(iid): self.tree.item(iid,values=values,tags=tags)\n        else: self.tree.insert('', 'end',iid=iid,values=values,tags=tags)\n        if follow: self.tree.see(iid)\n        self._schedule_total_outlines()\n        # OCR runs synchronously on the GUI thread. update_idletasks() can leave\n        # native Windows painting queued until a long OCR loop ends, so process a\n        # complete Tk event cycle before starting the next row.\n        if getattr(self,'_analysis_running',False):\n            self.pump_analysis_ui()\n        else:\n            self.update_idletasks()\n'''
text = replace_once(text, old, new, 'work-order total outline UI')

old = '''    def refresh_total_check(self,check,redraw=True):\n        indexed=self._total_check_records(check); rows=[r for _,r in indexed]\n        expected=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')\n        result=_length_total_result(rows,expected)\n        check.update(result)\n        trusted=bool(check.get('manual_verified') or check.get('pdf_total_confident'))\n        check['passed']=bool(result['matches'] and trusted)\n        for _,record in indexed:\n            record['warnings']=[w for w in record.get('warnings',[]) if not str(w).startswith('TOTAL LENGTH')]\n        if not check['passed']:\n            if expected is None:\n                warning='TOTAL LENGTH NEEDS VERIFICATION — PRINTED PDF TOTAL COULD NOT BE READ'\n            elif result['missing']:\n                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, \"\n                         f\"SUMMARY {result['summary_total']:g}; {result['missing']} LENGTH(S) MISSING\")\n            elif not trusted:\n                warning=(f\"TOTAL LENGTH NEEDS VERIFICATION — PDF TOTAL {expected:g}, \"\n                         f\"SUMMARY {result['summary_total']:g}\")\n            else:\n                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, \"\n                         f\"SUMMARY {result['summary_total']:g}, DIFF {abs(result['difference']):g} FT\")\n            check['warning']=warning\n            for _,record in indexed:\n                if warning not in record.setdefault('warnings',[]): record['warnings'].append(warning)\n        else:\n            check['warning']=''\n        if redraw:\n            for index,_ in indexed: self.show_summary_record(index)\n        return check['passed']\n'''
new = '''    def refresh_total_check(self,check,redraw=True):\n        indexed=self._total_check_records(check); rows=[r for _,r in indexed]\n        check['record_indices']=[index for index,_ in indexed]\n        check['first_record_index']=indexed[0][0] if indexed else None\n        expected=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')\n        result=_length_total_result(rows,expected)\n        check.update(result)\n        trusted=bool(check.get('manual_verified') or check.get('pdf_total_confident'))\n        check['passed']=bool(result['matches'] and trusted)\n        # Remove legacy row-level total warnings if this record set came from an\n        # older in-memory path. Total validation now belongs to the W/O group.\n        for _,record in indexed:\n            record['warnings']=[w for w in record.get('warnings',[]) if not str(w).startswith('TOTAL LENGTH')]\n        if not check['passed']:\n            if expected is None:\n                warning='TOTAL LENGTH NEEDS VERIFICATION — PRINTED PDF TOTAL COULD NOT BE READ'\n            elif result['missing']:\n                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, \"\n                         f\"SUMMARY {result['summary_total']:g}; {result['missing']} LENGTH(S) MISSING\")\n            elif not trusted:\n                warning=(f\"TOTAL LENGTH NEEDS VERIFICATION — PDF TOTAL {expected:g}, \"\n                         f\"SUMMARY {result['summary_total']:g}\")\n            else:\n                warning=(f\"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, \"\n                         f\"SUMMARY {result['summary_total']:g}, DIFF {abs(result['difference']):g} FT\")\n            check['warning']=warning\n        else:\n            check['warning']=''\n        if redraw:\n            for index,_ in indexed: self.show_summary_record(index)\n        self._schedule_total_outlines()\n        return check['passed']\n'''
text = replace_once(text, old, new, 'group-level total validation UI')
text = replace_once(
    text,
    "                    'The affected summary rows remain dark red and Update Master is blocked until the row lengths are corrected.',parent=self)\n",
    "                    'The work-order group remains outlined in red and Update Master is blocked until the row lengths are corrected. Rows with their own length difference remain highlighted red.',parent=self)\n",
    'total mismatch dialog wording')

APP.write_text(text, encoding='utf-8')

updater = UPDATER.read_text(encoding='utf-8')
updater, n = re.subn(r"CURRENT_VERSION = ['\"]\d+['\"]", 'CURRENT_VERSION = "80"', updater, count=1)
if n != 1:
    raise SystemExit('CURRENT_VERSION replacement failed')
UPDATER.write_text(updater, encoding='utf-8')

readme = README.read_text(encoding='utf-8')
heading = 'Version 80 OCR and total-review fixes'
if heading not in readme:
    readme += '''\n\nVersion 80 OCR and total-review fixes\n-------------------------------------\n- Printed total OCR now trusts stable full-cell reads before destructive grid-removal or crop fallbacks.\n- A suspicious aligned-column cleaning value is verified with conservative per-cell OCR before it remains a length-difference warning.\n- Implausible far-future table years are rejected, and B&C work-order dates are preferred as the year anchor.\n- Total-length failures are displayed once per work-order/activity group with a red outline instead of turning every row dark red.\n- Individual rows whose measured length differs from the master remain highlighted red.\n- OCR cache advances to v6 so stale total/length/date reads are not reused.\n'''
    README.write_text(readme, encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast
from datetime import datetime
import re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "APP_VERSION = '80'" in src
assert "OCR_CACHE_VERSION = 'v6'" in src
assert 'def _preferred_printed_total_candidates' in src
assert "return direct,'direct full cell'" in src
assert "return gridless,'gridless fallback'" in src
assert 'batch_suspect=' in src
assert 'cell_candidates=_ocr_digits(value_cell,True,fast_plain=True)' in src
assert 'def _plausible_sheet_year' in src
assert "use_date=current_wo.get('date') or current_report_date or page_date" in src
assert 'def _draw_total_outlines' in src
assert 'def _total_warning_for_record_index' in src
assert "tags=('total_warning',)" not in src
assert "record.setdefault('warnings',[]): record['warnings'].append(warning)" not in src
assert 'work-order group remains outlined in red' in src

# Execute only pure helpers so this regression remains independent of Windows/Tk.
tree=ast.parse(src)
names={'_printed_total_value_is_plausible','_choose_printed_total','_preferred_printed_total_candidates',
       '_plausible_sheet_year','_parse_sheet_date_text_candidates','_choose_cleaning_length'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'datetime':datetime,'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v80-helpers>','exec'),ns)

# Stable untouched OCR wins over a larger pile of damaged fallback reads.
cands,mode=ns['_preferred_printed_total_candidates']([8427,8427],[87]*12,24)
assert mode=='direct full cell' and ns['_choose_printed_total'](cands)[0]==8427
# If the raw cell is not independently stable, a stable rule-free read may recover it.
cands,mode=ns['_preferred_printed_total_candidates']([776],[4321]*5+[7]*2,18)
assert mode=='gridless fallback' and ns['_choose_printed_total'](cands)[0]==4321
# One bad batch read cannot beat two matching conservative cell reads.
assert ns['_choose_cleaning_length']([42,342,342],340)==342
# An absurd expected year must not overwrite a clearly printed plausible year.
result=ns['_parse_sheet_date_text_candidates']('8/17/2026',datetime(2096,8,17))
assert result and result[0][0].year==2026
# An absurd printed year is repaired only when a plausible packet year is available.
result=ns['_parse_sheet_date_text_candidates']('8/17/2096',datetime(2026,8,17))
assert result and result[0][0].year==2026
assert ns['_parse_sheet_date_text_candidates']('8/17/2096',None)==[]

print('v80 OCR/total/group-review regression passed.')
''',encoding='utf-8')

print('Applied v80 OCR and total-review fixes.')
