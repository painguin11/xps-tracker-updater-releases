from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'app' / 'reno_scan_updater.py'
s = SOURCE.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count}')
    s = s.replace(old, new, 1)


# 1) MSA confirmation: show both physical PDF rows and their ID/length crops.
start = s.index('class MsaConfirmDialog(tk.Toplevel):')
end = s.index('\n\nclass NewAssetApprovalDialog', start)
new_dialog = r'''class MsaConfirmDialog(tk.Toplevel):
    def __init__(self,parent,first,second,difference):
        super().__init__(parent); self.result=None; self.crop_photos=[]
        apply_app_icon(self)
        self.title('Confirm MSA'); self.transient(parent); self.grab_set(); self.resizable(False,False)
        pipe=f"{first.get('up','')} → {first.get('down','')}"
        first_length=first.get('video_length'); second_length=second.get('video_length')
        combined=(float(first_length)+float(second_length)
                  if first_length is not None and second_length is not None else None)
        master=first.get('master_length')
        if master is None: master=second.get('master_length')
        details=[]
        if combined is not None: details.append(f"Combined PDF length: {_format_pdf_number(combined)} ft")
        if master is not None: details.append(f"Master length: {_format_pdf_number(master)} ft")
        details.append(f"Difference: {difference:.1f} ft")
        text=(f"Two rows have the same Pipe IDs.\n\n"
              f"Pipe: {pipe}\n"
              + '\n'.join(details) + "\n\n"
              "Compare both printed rows below, then confirm whether they are two parts of the same MSA.")
        ttk.Label(self,text=text,justify='left',wraplength=780).grid(row=0,column=0,columnspan=2,padx=16,pady=(16,8),sticky='w')

        preview_frame=ttk.LabelFrame(self,text='PDF MSA verification',padding=10)
        preview_frame.grid(row=1,column=0,columnspan=2,padx=16,pady=(0,12),sticky='ew')

        def add_part(column,label,record):
            part=ttk.Frame(preview_frame); part.grid(row=0,column=column,padx=8,sticky='nw')
            page=record.get('source_page','?')
            ttk.Label(part,text=f"{label} — PDF page {page}",font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,5))
            previews=dict(record.get('_field_previews') or {})
            preview_pages=dict(record.get('_field_preview_pages') or {})
            specs=(('Upstream ID',record.get('up') or '','upstream'),
                   ('Downstream ID',record.get('down') or '','downstream'),
                   ('Length',_format_pdf_number(record.get('video_length')),'activity_value'))
            for field_label,value,key in specs:
                block=ttk.Frame(part); block.pack(anchor='w',fill='x',pady=3)
                ttk.Label(block,text=f'{field_label}: {value}',font=('Segoe UI',9,'bold')).pack(anchor='w')
                raw=previews.get(key)
                raw_items=list(raw) if isinstance(raw,(list,tuple)) else [raw]
                crops=[crop for crop in raw_items if getattr(crop,'size',0)]
                pages=list(preview_pages.get(key) or [])
                if not pages:
                    pages=list(record.get('source_pages') or [])
                    if not pages and record.get('source_page') is not None: pages=[record.get('source_page')]
                if not crops:
                    ttk.Label(block,text=_preview_unavailable_text(pages),foreground='#8A5200').pack(anchor='w')
                    continue
                for crop_index,crop in enumerate(crops):
                    try:
                        image=Image.fromarray(crop)
                        if image.width<220:
                            scale=min(3.0,220.0/max(1,image.width))
                            image=image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.LANCZOS)
                        image.thumbnail((340,78),Image.Resampling.LANCZOS)
                        photo=ImageTk.PhotoImage(image,master=self); self.crop_photos.append(photo)
                        crop_page=pages[crop_index] if crop_index<len(pages) else (pages[0] if pages else page)
                        line=ttk.Frame(block); line.pack(anchor='w',pady=1)
                        ttk.Label(line,text=f'Page {crop_page}:',width=8).pack(side='left',padx=(0,4))
                        ttk.Label(line,image=photo).pack(side='left')
                    except Exception:
                        ttk.Label(block,text=_preview_unavailable_text(pages),foreground='#8A5200').pack(anchor='w')
                        break

        add_part(0,'Part 1',first); add_part(1,'Part 2',second)
        preview_frame.columnconfigure(0,weight=1); preview_frame.columnconfigure(1,weight=1)

        buttons=ttk.Frame(self); buttons.grid(row=2,column=0,columnspan=2,pady=(0,14))
        ttk.Button(buttons,text='Confirm MSA',command=lambda:self.finish('confirm'),style='Primary.TButton').pack(side='left',padx=6)
        ttk.Button(buttons,text='Not MSA',command=lambda:self.finish('not_msa')).pack(side='left',padx=6)
        ttk.Button(buttons,text='Back to Summary',command=self.cancel).pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.update_idletasks(); self.geometry(f'+{parent.winfo_rootx()+45}+{parent.winfo_rooty()+35}')
    def finish(self,value): self.result=value; self.destroy()
    def cancel(self): self.result=None; self.destroy()
'''
s = s[:start] + new_dialog + s[end:]

# 2) Make a rejected MSA decision explicit in Live Summary.
replace_once(
"""def review_status(record):
    parts=[]
""",
"""def review_status(record):
    parts=[]
    if record.get('_msa_rejected'):
        parts.append('NOT MSA — EDIT ROW TO CHANGE DECISION')
""",
'rejected MSA summary status')

# 3) Do not erase a prior Not-MSA decision merely by opening/saving Edit Selected.
# Clear it only if the pipe identity actually changes; length edits already clear it.
replace_once(
"""    record.pop('_unmatched_ignored',None)
    record.pop('_msa_rejected',None)
    def clear_asset_decision_if_changed(new_identity):
        if new_identity==old_identity:
            return
""",
"""    record.pop('_unmatched_ignored',None)
    def clear_asset_decision_if_changed(new_identity):
        if new_identity==old_identity:
            return
        record.pop('_msa_rejected',None)
""",
'identity-scoped MSA rejection')

# 4) Preserve authoritative NEW PIPE suffix evidence ahead of all lossy endpoint
# fallbacks. The existing independent suffix confirmation still decides whether
# the letter is real; only after that may a false suffix collapse back to master.
pair_start=s.index('def parse_year15_pair_list')
pair_end=s.index('\ndef parse_year15_manholes',pair_start)
pair=s[pair_start:pair_end]
for comment in (
    '# Some clean R2 prefixes are consistently read as 2/22/32/52.',
    '# If grid/prefix damage erased EC/DN/R2 but both endpoint numbers are',
    '# Escalate only uncertain endpoint cells to the slower OCR ensemble.',
):
    comment_pos=pair.index(comment)
    if_pos=pair.rfind('        if not match:',0,comment_pos)
    if if_pos < 0:
        raise SystemExit(f'Could not locate fallback condition before: {comment}')
    pair=pair[:if_pos] + "        if not match and match_status!='NEW PIPE':" + pair[if_pos+len('        if not match:'):]
s=s[:pair_start]+pair+s[pair_end:]

# 5) Add an explicit way to revisit a rejected/pending two-row MSA from Edit Selected.
merge_marker='    def _merge_pipe_record_indices(self,first_index,second_index):\n'
insert_at=s.index(merge_marker,s.index('class App(tk.Tk):'))
helper=r'''    def _msa_pair_indices_for_record(self,index):
        try: index=int(index)
        except Exception: return None
        for indices in self._pipe_duplicate_groups().values():
            if index not in indices or len(indices)!=2:
                continue
            records=[self.records[i] for i in indices]
            if pipe_group_physical_count(records)!=2:
                return None
            if pipe_msa_difference(records[0],records[1]) is None:
                return None
            return tuple(indices)
        return None

    def review_msa_for_record(self,index,parent=None):
        pair=self._msa_pair_indices_for_record(index)
        if not pair:
            messagebox.showinfo('MSA Review','This row is not currently part of a reviewable two-row MSA pair.',parent=parent or self)
            return None
        first_index,second_index=pair
        first=self.records[first_index]; second=self.records[second_index]
        difference=pipe_msa_difference(first,second)
        dlg=MsaConfirmDialog(parent or self,first,second,difference); self.wait_window(dlg)
        if dlg.result=='confirm':
            self._merge_pipe_record_indices(first_index,second_index)
            for check in self.total_validations:
                self.refresh_total_check(check,redraw=False)
            self._refresh_record_rows_only()
            self.status.set('MSA decision changed: the two Pipe rows are now combined.')
            return 'confirm'
        if dlg.result=='not_msa':
            for record in (first,second):
                record.setdefault('warnings',[]).append(DUPLICATE_PIPE_REVIEW)
                record['_msa_pending']=True; record['_msa_rejected']=True
            self._refresh_record_rows_only()
            return 'not_msa'
        return None

'''
s=s[:insert_at]+helper+s[insert_at:]

# Replace the single Save button with Save + reversible MSA review when applicable.
replace_once(
"""        ttk.Button(win,text='Save',command=save,style='Primary.TButton').grid(row=len(fields)+2,column=0,columnspan=3,pady=(6,12))
        win.update_idletasks(); win.geometry(f'+{self.winfo_rootx()+70}+{self.winfo_rooty()+60}')
""",
"""        buttons=ttk.Frame(win); buttons.grid(row=len(fields)+2,column=0,columnspan=3,pady=(6,12))
        ttk.Button(buttons,text='Save',command=save,style='Primary.TButton').pack(side='left',padx=6)
        if (r.get('kind')=='Pipe' and (r.get('_msa_rejected') or r.get('_msa_pending')) and
                self._msa_pair_indices_for_record(i)):
            def review_msa():
                result=self.review_msa_for_record(i,win)
                if result=='confirm': win.destroy()
            ttk.Button(buttons,text='Review / Change MSA Decision',command=review_msa).pack(side='left',padx=6)
        win.update_idletasks(); win.geometry(f'+{self.winfo_rootx()+70}+{self.winfo_rooty()+60}')
""",
'Edit Selected MSA review button')

SOURCE.write_text(s,encoding='utf-8')
print('Applied post-v95 MSA preview/reversal and suffix-priority changes.')
