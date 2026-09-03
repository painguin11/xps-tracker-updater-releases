from pathlib import Path
import ast

SOURCE = Path('working_source/app/reno_scan_updater.py')
TEST = Path('working_source/tests/regression_v89_review_workflow.py')
src = SOURCE.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global src
    count = src.count(old)
    if count != 1:
        raise AssertionError(f'{label}: expected exactly one target, found {count}')
    src = src.replace(old, new, 1)


def replace_between(start_marker, end_marker, new_text, label):
    global src
    start = src.find(start_marker)
    if start < 0:
        raise AssertionError(f'{label}: missing start marker')
    end = src.find(end_marker, start)
    if end < 0:
        raise AssertionError(f'{label}: missing end marker')
    src = src[:start] + new_text + src[end:]


# Approved wording changes.
replace_once(
    "LENGTH_DIFF_THRESHOLD = 4.5\n",
    "LENGTH_DIFF_THRESHOLD = 4.5\nDUPLICATE_PIPE_REVIEW = 'Duplicate pipe - check IDs'\n",
    'duplicate pipe review constant',
)
replace_once("'date':'Activity Date'", "'date':'Date'", 'layout Date label')
replace_once(
    'Description preview unavailable',
    'Description preview unavailable — check PDF',
    'manhole description preview warning',
)
replace_once(
    'Check each scan image beside its field. OCR is only a pre-filled suggestion.',
    'Check each scan image beside its field, pre-filled text is only a suggestion.',
    'work-order OCR reminder',
)
replace_once(
    "raise ValueError(f'Individual activity length must be greater than 0 and no more than {MAX_ROW_LENGTH:g} ft.')",
    "raise ValueError('Enter a valid length')",
    'manual length validation message',
)
replace_once(
    "            kinds=', '.join(dict.fromkeys(str(item.get('kind') or '').title() for item in entries if item.get('kind')))\n"
    "            status=f\"PAGES {pages} COULD NOT BE PROCESSED\"\n"
    "            if kinds: status+=f\" — {kinds}\"\n",
    "            status=f\"PAGES {pages} COULD NOT BE PROCESSED\"\n",
    'unprocessed page suffix',
)

# Manual edits clear stale unmatched/MSA decisions before rematching.
replace_once(
    "def apply_manual_asset_edit(record,master_index,up=None,down=None,asset=None):\n"
    "    \"\"\"Apply an Edit Selected asset/node correction and immediately re-match it.\"\"\"\n"
    "    kind=record.get('kind')\n",
    "def apply_manual_asset_edit(record,master_index,up=None,down=None,asset=None):\n"
    "    \"\"\"Apply an Edit Selected asset/node correction and immediately re-match it.\"\"\"\n"
    "    kind=record.get('kind')\n"
    "    record.pop('_unmatched_ignored',None)\n"
    "    record.pop('_msa_rejected',None)\n",
    'manual review reset',
)

# Keep conservative internal matching statuses, but never expose AMBIGUOUS to users.
new_review_status = '''def review_status(record):
    parts=[]
    if int(record.get('part_count') or 0)>1:
        parts.append(f"MSA DETECTED — {int(record['part_count'])} PARTS COMBINED")
    status=str(record.get('status') or '')
    display_status=status
    if status=='NOT MATCHED' or status.startswith('AMBIGUOUS'):
        display_status=('PIPE NOT FOUND IN MASTER — CHECK MH IDS'
                        if record.get('kind') in ('Pipe','Cleaning')
                        else 'MH NOT FOUND IN MASTER — CHECK MH ID')
    if status.startswith(('NEW PIPE','NEW MANHOLE')) and 'new_asset_approved' in record:
        parts.append(f"{status} — {'APPROVED FOR MASTER' if record.get('new_asset_approved') else 'NOT APPROVED'}")
    elif display_status and display_status!='Matched':
        parts.append(display_status)
    parts.extend(record.get('warnings', []))
    return '; '.join(dict.fromkeys(parts)) if parts else 'Matched'


'''
replace_between(
    'def review_status(record):',
    'def record_needs_review(record):',
    new_review_status,
    'review status display mapping',
)

# Testable MSA arithmetic helpers.
msa_helpers = '''def pipe_group_physical_count(records):
    return sum(max(1,int(record.get('part_count') or 1)) for record in records)


def pipe_msa_difference(first,second):
    if int(first.get('part_count') or 1)!=1 or int(second.get('part_count') or 1)!=1:
        return None
    values=(first.get('video_length'),second.get('video_length'))
    expected=first.get('master_length')
    if expected is None:
        expected=second.get('master_length')
    if any(value is None for value in values) or expected is None:
        return None
    return abs((float(values[0])+float(values[1]))-float(expected))


'''
marker = 'def _length_part_snapshot(record):\n'
if marker not in src:
    raise AssertionError('MSA helper insertion marker missing')
src = src.replace(marker, msa_helpers + marker, 1)

# Arbitrary unmatched Add-to-Master rows have no safe base asset to copy. Insert a
# blank row with the surrounding formatting only, then populate the observed data.
blank_row_helper = '''def insert_blank_formatted_row_below(ws,base_row):
    """Insert a blank row while copying only the preceding row's formatting."""
    insert_row=int(base_row)+1
    last_col=max(1,int(ws.UsedRange.Columns.Count))
    ws.Rows(insert_row).Insert()
    try:
        source=ws.Range(ws.Cells(base_row,1),ws.Cells(base_row,last_col))
        destination=ws.Range(ws.Cells(insert_row,1),ws.Cells(insert_row,last_col))
        source.Copy()
        destination.PasteSpecial(Paste=-4122)  # xlPasteFormats
        try: ws.Application.CutCopyMode=False
        except Exception: pass
        try: ws.Rows(insert_row).RowHeight=ws.Rows(base_row).RowHeight
        except Exception: pass
    except Exception:
        pass
    return insert_row,last_col


'''
marker = 'def clear_master_columns(ws,row,columns):\n'
if marker not in src:
    raise AssertionError('blank-row insertion marker missing')
src = src.replace(marker, blank_row_helper + marker, 1)

# New reviewed decision dialogs.
dialogs = '''class MsaConfirmDialog(tk.Toplevel):
    def __init__(self,parent,first,second,difference):
        super().__init__(parent); self.result=None
        apply_app_icon(self)
        self.title('Confirm MSA'); self.transient(parent); self.grab_set(); self.resizable(False,False)
        pipe=f"{first.get('up','')} → {first.get('down','')}"
        text=(f"Two rows have the same Pipe IDs, but their combined length differs from the master by {difference:.1f} ft.\\n\\n"
              f"Pipe:\\n{pipe}\\n\\n"
              "Confirm that these are two parts of the same MSA?")
        ttk.Label(self,text=text,justify='left',wraplength=560).grid(row=0,column=0,columnspan=3,padx=16,pady=(16,12),sticky='w')
        buttons=ttk.Frame(self); buttons.grid(row=1,column=0,columnspan=3,pady=(0,14))
        ttk.Button(buttons,text='Confirm MSA',command=lambda:self.finish('confirm'),style='Primary.TButton').pack(side='left',padx=6)
        ttk.Button(buttons,text='Not MSA',command=lambda:self.finish('not_msa')).pack(side='left',padx=6)
        ttk.Button(buttons,text='Back to Summary',command=self.cancel).pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',self.cancel)
    def finish(self,value): self.result=value; self.destroy()
    def cancel(self): self.result=None; self.destroy()


class UnmatchedAssetDecisionDialog(tk.Toplevel):
    def __init__(self,parent,record):
        super().__init__(parent); self.result=None
        apply_app_icon(self)
        is_manhole=record.get('kind')=='Manhole'
        label='Manhole' if is_manhole else 'Pipe'
        self.title(f'{label} Not Found in Master'); self.transient(parent); self.grab_set(); self.resizable(False,False)
        header='MH NOT FOUND IN MASTER — CHECK MH ID' if is_manhole else 'PIPE NOT FOUND IN MASTER — CHECK MH IDS'
        scanned=record.get('display_asset') or record.get('asset') or ''
        noun='manhole' if is_manhole else 'pipe'
        text=(f"{header}\\n\\nScanned {noun}:\\n{scanned}\\n\\n"
              "This item is still not found in the master. Choose what to do with it before continuing the update.")
        ttk.Label(self,text=text,justify='left',wraplength=620).grid(row=0,column=0,columnspan=3,padx=16,pady=(16,12),sticky='w')
        buttons=ttk.Frame(self); buttons.grid(row=1,column=0,columnspan=3,pady=(0,14))
        ttk.Button(buttons,text='Add to Master',command=lambda:self.finish('add'),style='Primary.TButton').pack(side='left',padx=6)
        ttk.Button(buttons,text='Ignore',command=lambda:self.finish('ignore')).pack(side='left',padx=6)
        ttk.Button(buttons,text='Back to Summary',command=self.cancel).pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',self.cancel)
    def finish(self,value): self.result=value; self.destroy()
    def cancel(self): self.result=None; self.destroy()


'''
app_marker = 'class App(tk.Tk):\n'
if app_marker not in src:
    raise AssertionError('App marker missing')
src = src.replace(app_marker, dialogs + app_marker, 1)

# Retain a PDF crop for every Trouble Ticket field that actually comes from the PDF.
preview_insert = '''    wo_previews=(current_wo or {}).get('_field_previews') or {}
    wo_pages=(current_wo or {}).get('_field_preview_pages') or {}
    def ticket_preview(coords):
        value=_ticket_crop(img,*coords)
        return value.copy() if getattr(value,'size',0) else None
    ticket['_field_previews']={
        'pipe_id':ticket_preview((.360,.242,.690,.268)),
        'description':ticket_preview((.245,.582,.915,.800)),
        'date':ticket_preview((.690,.242,.915,.268)),
        'panel':ticket_preview((.690,.307,.915,.337)),
        'street_name':ticket_preview((.085,.307,.690,.337)),
        'area':ticket_preview((.085,.412,.590,.442)),
        'service_type':ticket_preview((.085,.445,.915,.505)),
        'upstream':ticket_preview((.085,.500,.360,.560)),
        'downstream':ticket_preview((.360,.500,.622,.560)),
        'map_length':ticket_preview((.622,.500,.718,.560)),
        'pipe_size':ticket_preview((.718,.500,.915,.560)),
    }
    ticket['_field_preview_pages']={key:[page_number] for key in ticket['_field_previews']}
    for key in ('wo','truck'):
        if key in wo_previews:
            ticket['_field_previews'][key]=wo_previews.get(key)
            ticket['_field_preview_pages'][key]=list(wo_pages.get(key) or [(current_wo or {}).get('_workorder_page') or page_number])
    if reported:
        ticket['_field_previews']['operator']=ticket_preview((.085,.242,.360,.268))
        ticket['_field_preview_pages']['operator']=[page_number]
    elif 'operator' in wo_previews:
        ticket['_field_previews']['operator']=wo_previews.get('operator')
        ticket['_field_preview_pages']['operator']=list(wo_pages.get('operator') or [(current_wo or {}).get('_workorder_page') or page_number])
'''
replace_once(
    "        'source_page_hash':hashlib.sha256(img.tobytes()).hexdigest(),\n"
    "    }\n"
    "    # A readable ticket date should win; the confirmed work-order date is a safe\n",
    "        'source_page_hash':hashlib.sha256(img.tobytes()).hexdigest(),\n"
    "    }\n" + preview_insert +
    "    # A readable ticket date should win; the confirmed work-order date is a safe\n",
    'Trouble Ticket previews',
)

# Edit Trouble Ticket now mirrors the row edit popup with a field crop beside each
# PDF-derived field. Status and Resolution Notes are program-only, so no fake crop.
new_edit_ticket = '''    def edit_trouble_ticket(self,index):
        ticket=self.trouble_tickets[index]
        win=tk.Toplevel(self); apply_app_icon(win); win.title('Edit trouble ticket'); win.transient(self); win.grab_set(); win.resizable(True,True)
        win.crop_photos=[]
        fields=[
            ('Pipe/MH ID','pipe_id',ticket.get('pipe_id','')),('Description','description',ticket.get('description','')),
            ('Status','tracker_status',ticket.get('tracker_status','Open')),('Resolution / Follow-up Notes','resolution_notes',ticket.get('resolution_notes','')),
            ('Date','date',fmt_date(ticket.get('date'))),('Work Order','wo',ticket.get('wo','')),
            ('Truck','truck',ticket.get('truck','')),('Operator','operator',ticket.get('operator','')),
            ('Panel','panel',ticket.get('panel','')),('Street','street_name',ticket.get('street_name','')),
            ('Area / Major Intersection','area',ticket.get('area','')),
            ('Service Type','service_type',ticket.get('service_type','')),('Upstream Manhole','upstream',ticket.get('upstream','')),
            ('Downstream Manhole','downstream',ticket.get('downstream','')),('Map Length','map_length','' if ticket.get('map_length') is None else str(ticket['map_length'])),
            ('Pipe Size','pipe_size',ticket.get('pipe_size','')),
        ]
        vars={}; previews=dict(ticket.get('_field_previews') or {}); preview_pages=dict(ticket.get('_field_preview_pages') or {})
        def add_ticket_preview(row,col,key):
            holder=ttk.Frame(win); holder.grid(row=row,column=col,padx=(0,12),pady=4,sticky='w')
            crop=previews.get(key)
            if crop is None or not getattr(crop,'size',0):
                if key not in ('tracker_status','resolution_notes'):
                    pages=preview_pages.get(key) or [ticket.get('source_page','?')]
                    ttk.Label(holder,text=_preview_unavailable_text(pages),foreground='#8A5200',wraplength=220).pack(anchor='w')
                return
            try:
                image=Image.fromarray(crop)
                if image.width<180:
                    scale=min(3.0,180.0/max(1,image.width))
                    image=image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.LANCZOS)
                image.thumbnail((250,82),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(image,master=win); win.crop_photos.append(photo)
                page=(preview_pages.get(key) or [ticket.get('source_page','?')])[0]
                ttk.Label(holder,text=f'PDF page {page}:').pack(anchor='w')
                ttk.Label(holder,image=photo).pack(anchor='w')
            except Exception:
                pages=preview_pages.get(key) or [ticket.get('source_page','?')]
                ttk.Label(holder,text=_preview_unavailable_text(pages),foreground='#8A5200').pack(anchor='w')
        for n,(label,key,value) in enumerate(fields):
            block=n%2; row=n//2; col=block*3
            ttk.Label(win,text=label+':').grid(row=row,column=col,padx=(10,5),pady=6,sticky='e')
            var=tk.StringVar(value=value); vars[label]=var
            if label=='Status':
                ttk.Combobox(win,textvariable=var,width=27,state='readonly',values=('Open','In Progress','Resolved','No Action Needed')).grid(row=row,column=col+1,padx=(0,8),pady=6,sticky='ew')
            else:
                ttk.Entry(win,textvariable=var,width=30).grid(row=row,column=col+1,padx=(0,8),pady=6,sticky='ew')
            add_ticket_preview(row,col+2,key)
        win.columnconfigure(1,weight=1); win.columnconfigure(4,weight=1)
        def save():
            try:
                raw_date=vars['Date'].get().strip()
                date=datetime.strptime(raw_date,'%m/%d/%Y') if raw_date else None
                raw_length=vars['Map Length'].get().strip()
                map_length=float(raw_length) if raw_length else None
            except Exception:
                messagebox.showerror('Invalid value','Use MM/DD/YYYY for Date and a number for Map Length.',parent=win); return
            ticket.update({
                'date':date,'pipe_id':canonical_asset_id(vars['Pipe/MH ID'].get()),'street_name':vars['Street'].get().strip(),
                'panel':vars['Panel'].get().strip(),'area':vars['Area / Major Intersection'].get().strip(),
                'service_type':vars['Service Type'].get().strip(),
                'upstream':canonical_asset_id(vars['Upstream Manhole'].get()),
                'downstream':canonical_asset_id(vars['Downstream Manhole'].get()),
                'map_length':map_length,'pipe_size':vars['Pipe Size'].get().strip(),
                'description':vars['Description'].get().strip(),'wo':vars['Work Order'].get().strip(),
                'truck':vars['Truck'].get().strip(),'operator':vars['Operator'].get().strip(),
                'reported_by':vars['Operator'].get().strip(),
                'tracker_status':vars['Status'].get().strip() or 'Open',
                'resolution_notes':vars['Resolution / Follow-up Notes'].get().strip(),
            })
            ticket['ticket_key']=trouble_ticket_key(ticket); ticket['review_status']=trouble_ticket_status(ticket)
            self.show_summary_ticket(index); win.destroy()
        ttk.Button(win,text='Save',command=save,style='Primary.TButton').grid(row=(len(fields)+1)//2,column=0,columnspan=6,pady=12)
        win.update_idletasks(); win.geometry(f'+{self.winfo_rootx()+30}+{self.winfo_rooty()+35}')
'''
replace_between(
    '    def edit_trouble_ticket(self,index):',
    '    def update_master(self):',
    new_edit_ticket,
    'Trouble Ticket edit popup',
)

# App-level MSA/duplicate and unmatched-resolution workflow.
app_methods = '''    def _refresh_record_rows_only(self):
        for iid in list(self.tree.get_children()):
            if str(iid).startswith(('record:','group-error:')):
                self.tree.delete(iid)
        for index in range(len(self.records)):
            self.show_summary_record(index)
        for check in self.total_validations:
            self.show_total_summary_error(check)
        self._schedule_total_outlines()

    def _pipe_duplicate_groups(self):
        groups={}
        for index,record in enumerate(self.records):
            if record.get('kind')!='Pipe':
                continue
            up=asset_key(record.get('up','')); down=asset_key(record.get('down',''))
            pipe_id=asset_key(record.get('asset',''))
            identity=('pipe_id',pipe_id) if pipe_id and not pipe_id.startswith('UNMATCHED') else (('pair',up,down) if up and down else None)
            if identity:
                groups.setdefault((str(record.get('wo','')),identity),[]).append(index)
        return groups

    def _merge_pipe_record_indices(self,first_index,second_index):
        first_index,second_index=sorted((int(first_index),int(second_index)))
        first=self.records[first_index]; second=self.records[second_index]
        for record in (first,second):
            record['warnings']=[w for w in record.get('warnings',[]) if w!=DUPLICATE_PIPE_REVIEW]
            record.pop('_duplicate_pipe_block',None); record.pop('_msa_pending',None); record.pop('_msa_rejected',None)
        combine_split_pipe_records(first,second)
        first['_msa_confirmed']=True
        self.records.pop(second_index)

    def resolve_pipe_duplicate_groups(self,prompt=False,update_mode=False):
        groups=self._pipe_duplicate_groups()
        duplicate_members={index for indices in groups.values() if len(indices)>1 for index in indices}
        for index,record in enumerate(self.records):
            if record.get('kind')!='Pipe': continue
            record['warnings']=[w for w in record.get('warnings',[]) if w!=DUPLICATE_PIPE_REVIEW]
            record.pop('_duplicate_pipe_block',None); record.pop('_msa_pending',None)
            if index not in duplicate_members:
                record.pop('_msa_rejected',None)
        changed=False; needs_refresh=bool(duplicate_members)
        # Resolve higher indexes first so popping a merged pair cannot invalidate
        # the indexes of an earlier independent pipe group.
        for _key,indices in sorted(groups.items(),key=lambda item:max(item[1]),reverse=True):
            records=[self.records[index] for index in indices]
            if pipe_group_physical_count(records)>=3:
                for record in records:
                    record.setdefault('warnings',[]).append(DUPLICATE_PIPE_REVIEW)
                    record['_duplicate_pipe_block']=True
                    record.pop('_msa_rejected',None)
                if update_mode:
                    self._refresh_record_rows_only()
                    messagebox.showwarning('Duplicate Pipe',DUPLICATE_PIPE_REVIEW,parent=self)
                    return False
                continue
            if len(indices)!=2:
                continue
            first_index,second_index=indices
            first=self.records[first_index]; second=self.records[second_index]
            difference=pipe_msa_difference(first,second)
            if difference is None:
                for record in (first,second):
                    record.setdefault('warnings',[]).append(DUPLICATE_PIPE_REVIEW)
                    record['_duplicate_pipe_block']=True
                if update_mode:
                    self._refresh_record_rows_only()
                    messagebox.showwarning('Duplicate Pipe',DUPLICATE_PIPE_REVIEW,parent=self)
                    return False
                continue
            rejected=bool(first.get('_msa_rejected') or second.get('_msa_rejected'))
            if difference<=LENGTH_DIFF_THRESHOLD and not rejected:
                self._merge_pipe_record_indices(first_index,second_index); changed=True
                continue
            for record in (first,second):
                record.setdefault('warnings',[]).append(DUPLICATE_PIPE_REVIEW)
                record['_msa_pending']=True
            if prompt and difference>LENGTH_DIFF_THRESHOLD:
                dlg=MsaConfirmDialog(self,first,second,difference); self.wait_window(dlg)
                if dlg.result=='confirm':
                    self._merge_pipe_record_indices(first_index,second_index); changed=True
                    continue
                if dlg.result=='not_msa':
                    first['_msa_rejected']=True; second['_msa_rejected']=True
                if update_mode:
                    self._refresh_record_rows_only()
                    return False
            elif update_mode:
                self._refresh_record_rows_only()
                messagebox.showwarning('Duplicate Pipe',DUPLICATE_PIPE_REVIEW,parent=self)
                return False
        if changed:
            for check in self.total_validations:
                self.refresh_total_check(check,redraw=False)
        if changed or needs_refresh:
            self._refresh_record_rows_only()
        return True

    def resolve_unmatched_for_update(self):
        for index,record in enumerate(self.records):
            if not record.get('skip_update') or record.get('new_asset_approved') or record.get('_unmatched_ignored'):
                continue
            status=str(record.get('status') or '')
            if not (status=='NOT MATCHED' or status.startswith('AMBIGUOUS')):
                continue
            dlg=UnmatchedAssetDecisionDialog(self,record); self.wait_window(dlg)
            if dlg.result is None:
                return False
            if dlg.result=='add':
                record['new_asset_approved']=True
                record['new_asset_append']=True
                record['status']='NEW MANHOLE' if record.get('kind')=='Manhole' else 'NEW PIPE'
                record.pop('_unmatched_ignored',None)
            else:
                record['_unmatched_ignored']=True
            self.show_summary_record(index)
        return True

'''
commit_marker = '    def commit_extracted_record(self,rec,current_wo,use_date,idx,page_number,processed):\n'
if commit_marker not in src:
    raise AssertionError('commit_extracted_record marker missing')
src = src.replace(commit_marker, app_methods + commit_marker, 1)

# Defer Pipe merging until all physical rows in the work order have been seen. This
# is what makes the 3+ duplicate rule possible.
commit_start = src.index('    def commit_extracted_record(self,rec,current_wo,use_date,idx,page_number,processed):')
merge_start = src.index('        split_identity=split_pipe_identity(rec)', commit_start)
append_pos = src.index('        self.records.append(rec)', merge_start)
src = src[:merge_start] + src[append_pos:]

# Resolve Pipe/MSA groups only after every page is parsed, before total validation.
replace_once(
    '            incomplete_total_keys=set()\n',
    '            self.resolve_pipe_duplicate_groups(prompt=True,update_mode=False)\n\n            incomplete_total_keys=set()\n',
    'post-analysis MSA resolution',
)

# Cleaning/Manhole keep generic duplicate handling. Pipe duplicates use the reviewed
# MSA-aware logic above.
replace_once(
    '        for row_i,r in enumerate(self.records):\n            key=',
    "        for row_i,r in enumerate(self.records):\n            if r.get('kind')=='Pipe':\n                continue\n            key=",
    'Pipe duplicate exclusion from generic duplicate pass',
)

# Editing IDs or lengths immediately reruns the duplicate/MSA rules so a typo can
# clear the warning before Update Master.
replace_once(
    "                    if old_length!=r.get('video_length'): r['_length_user_edited']=True\n",
    "                    if old_length!=r.get('video_length'):\n"
    "                        r['_length_user_edited']=True\n"
    "                        r.pop('_msa_rejected',None)\n",
    'length edit review reset',
)
replace_once(
    '            self.revalidate_total_checks_for_record(r)\n            self.show_summary_record(i)\n',
    '            self.revalidate_total_checks_for_record(r)\n'
    '            self.resolve_pipe_duplicate_groups(prompt=False,update_mode=False)\n'
    '            self._refresh_record_rows_only()\n',
    'rerun duplicate checks after edit',
)

# Update Master enforces unresolved MSA/duplicate decisions before any spreadsheet
# write, then resolves every truly unmatched row one-by-one.
replace_once(
    "    def update_master(self):\n"
    "        if not self.records and not self.trouble_tickets: messagebox.showwarning('Nothing to update','Analyze a PDF first.'); return\n",
    "    def update_master(self):\n"
    "        if not self.records and not self.trouble_tickets: messagebox.showwarning('Nothing to update','Analyze a PDF first.'); return\n"
    "        if not self.resolve_pipe_duplicate_groups(prompt=True,update_mode=True): return\n",
    'Update Master duplicate enforcement',
)
replace_once(
    "        bad=[r for r in self.records if not r.get('new_asset_approved') and (r['status']=='NOT MATCHED' or r.get('skip_update'))]\n"
    "        if bad and not messagebox.askyesno('Unmatched rows',f'{len(bad)} rows are not matched and will be skipped. Continue with matched rows?'): return\n",
    "        if not self.resolve_unmatched_for_update(): return\n"
    "        bad=[r for r in self.records if r.get('skip_update') and not r.get('new_asset_approved')]\n",
    'per-item unmatched update decisions',
)

# Keep established suffixed-asset insertion beneath a known base. Arbitrary unmatched
# Add-to-Master rows use a separate append path because copying an unrelated base row
# could import wrong master metadata.
replace_once(
    "                (r for r in self.records if r.get('new_asset_approved') and r.get('kind') in ('Pipe','Cleaning')),\n",
    "                (r for r in self.records if r.get('new_asset_approved') and not r.get('new_asset_append') and r.get('kind') in ('Pipe','Cleaning')),\n",
    'base Pipe insertion filter',
)
replace_once(
    "                (r for r in self.records if r.get('new_asset_approved') and r.get('kind')=='Manhole'),\n",
    "                (r for r in self.records if r.get('new_asset_approved') and not r.get('new_asset_append') and r.get('kind')=='Manhole'),\n",
    'base Manhole insertion filter',
)

append_pipe_rows = '''            append_pipe_rows=[r for r in self.records if r.get('new_asset_approved') and r.get('new_asset_append') and r.get('kind') in ('Pipe','Cleaning')]
            pipe_last=max([int(item.get('row') or 0) for item in cached.get('pipe_items',[])] or [pr])
            for r in append_pipe_rows:
                rr,last_col=insert_blank_formatted_row_below(ps,pipe_last); pipe_last=rr
                if profile in ('year15','phase2_year1'):
                    ps.Cells(rr,ph['upstream']).Value=master_text(r.get('up'))
                    ps.Cells(rr,ph['downstream']).Value=master_text(r.get('down'))
                    ps.Cells(rr,ph['pipe_id']).Value=f"{master_text(r.get('up'))}-{master_text(r.get('down'))}"
                    if r['kind']=='Cleaning':
                        ps.Cells(rr,ph['clean wheel walk']).Value=r['video_length']
                        write_excel_date(ps.Cells(rr,ph['clean date']),r['date'])
                        ps.Cells(rr,ph['clean w/o']).Value=master_text(r['wo'])
                        ps.Cells(rr,ph['clean truck']).Value=master_text(r['truck'])
                        ps.Cells(rr,ph['clean operator']).Value=master_text(r['operator'])
                    else:
                        ps.Cells(rr,ph['video length']).Value=r['video_length']
                        write_excel_date(ps.Cells(rr,ph['video date']),r['date'])
                        ps.Cells(rr,ph['video w/o']).Value=master_text(r['wo'])
                        ps.Cells(rr,ph['video truck']).Value=master_text(r['truck'])
                        ps.Cells(rr,ph['video operator']).Value=master_text(r['operator'])
                else:
                    if ph.get('upstream'): ps.Cells(rr,ph['upstream']).Value=master_text(r.get('up'))
                    if ph.get('downstream'): ps.Cells(rr,ph['downstream']).Value=master_text(r.get('down'))
                    pipe_name=r.get('asset') or f"{master_text(r.get('up'))}-{master_text(r.get('down'))}"
                    ps.Cells(rr,ph['pipe_id']).Value=master_text(pipe_name)
                    ps.Cells(rr,ph['video length']).Value=r['video_length']
                    write_excel_date(ps.Cells(rr,ph['date']),r['date'])
                    ps.Cells(rr,ph['w/o']).Value=master_text(r['wo'])
                    ps.Cells(rr,ph['truck']).Value=master_text(r['truck'])
                    ps.Cells(rr,ph['operator']).Value=master_text(r['operator'])
                highlight_approved_master_row(ps,rr,last_col)
                written+=1; log_rows.append(r)

'''
manhole_marker = '            approved_manhole_rows=sorted(\n'
if manhole_marker not in src:
    raise AssertionError('approved Manhole insertion marker missing')
src = src.replace(manhole_marker, append_pipe_rows + manhole_marker, 1)

append_manhole_rows = '''
            append_manhole_rows=[r for r in self.records if r.get('new_asset_approved') and r.get('new_asset_append') and r.get('kind')=='Manhole']
            manhole_last=max([int(item.get('row') or 0) for item in cached.get('manholes',{}).values()] or [mr])
            for r in append_manhole_rows:
                rr,last_col=insert_blank_formatted_row_below(ms,manhole_last); manhole_last=rr
                ms.Cells(rr,mh['st_id']).Value=master_text(r.get('asset'))
                write_excel_date(ms.Cells(rr,mh['date']),r['date'])
                ms.Cells(rr,mh['w/o']).Value=master_text(r['wo'])
                ms.Cells(rr,mh['truck']).Value=master_text(r['truck'])
                ms.Cells(rr,mh['operator']).Value=master_text(r['operator'])
                highlight_approved_master_row(ms,rr,last_col)
                written+=1; log_rows.append(r)
'''
ticket_marker = '\n            ticket_added=[]; ticket_skipped=0; ticket_existed=False\n'
if ticket_marker not in src:
    raise AssertionError('Trouble Ticket write marker missing')
src = src.replace(ticket_marker, append_manhole_rows + ticket_marker, 1)

# Fail before writing the source if any replacement produced invalid Python.
ast.parse(src)
SOURCE.write_text(src, encoding='utf-8')

TEST.write_text('''import ast\nfrom pathlib import Path\n\nSOURCE=Path("working_source/app/reno_scan_updater.py")\nsrc=SOURCE.read_text(encoding="utf-8")\ntree=ast.parse(src)\n\nfor required in (\n    "DUPLICATE_PIPE_REVIEW = 'Duplicate pipe - check IDs'",\n    "PIPE NOT FOUND IN MASTER — CHECK MH IDS",\n    "MH NOT FOUND IN MASTER — CHECK MH ID",\n    "class MsaConfirmDialog(tk.Toplevel):",\n    "class UnmatchedAssetDecisionDialog(tk.Toplevel):",\n    "def resolve_pipe_duplicate_groups(self,prompt=False,update_mode=False):",\n    "if pipe_group_physical_count(records)>=3:",\n    "difference=pipe_msa_difference(first,second)",\n    "def resolve_unmatched_for_update(self):",\n    "record['new_asset_append']=True",\n    "def insert_blank_formatted_row_below(ws,base_row):",\n    "Check each scan image beside its field, pre-filled text is only a suggestion.",\n    "Description preview unavailable — check PDF",\n    "'date':'Date'",\n    "raise ValueError('Enter a valid length')",\n    "ticket['_field_previews']={",\n    "('Pipe/MH ID','pipe_id'",\n    "self.resolve_pipe_duplicate_groups(prompt=True,update_mode=True)",\n    "self.resolve_pipe_duplicate_groups(prompt=True,update_mode=False)",\n):\n    assert required in src, required\n\nassert "messagebox.askyesno('Unmatched rows'" not in src\nassert 'if kinds: status+=' not in src\n\n# Exercise the pure MSA arithmetic helpers rather than testing only source text.\nwanted={'pipe_group_physical_count','pipe_msa_difference'}\nnodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted]\nmodule=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(module)\nns={}\nexec(compile(module,str(SOURCE),'exec'),ns)\na={'video_length':120.0,'master_length':301.0,'part_count':1}\nb={'video_length':180.0,'master_length':301.0,'part_count':1}\nassert ns['pipe_group_physical_count']([a,b])==2\nassert ns['pipe_msa_difference'](a,b)==1.0\nc={'video_length':10.0,'master_length':301.0,'part_count':1}\nassert ns['pipe_group_physical_count']([a,b,c])==3\n\nprint('v89 reviewed wording, unmatched decisions, duplicate/MSA safeguards, and Trouble Ticket previews passed.')\n''', encoding='utf-8')

print('Applied v89 reviewed UI and validation patch.')
