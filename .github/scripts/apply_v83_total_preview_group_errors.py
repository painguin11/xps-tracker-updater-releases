from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
src=path.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global src
    if old not in src:
        raise SystemExit(f'missing patch target: {label}')
    src=src.replace(old,new,1)

replace_once(
"result={'found':False,'value':None,'confident':False,'candidates':[],'method':'not found','band_index':None}",
"result={'found':False,'value':None,'confident':False,'candidates':[],'method':'not found','band_index':None,'preview':None}",
'printed total default preview')

replace_once(
"""    def blank_total_row(y1,y2,method,band_index=None):
        candidates=read_value(y1,y2)
        if not candidates: return None
        if neighbor_has_number(up_box,y1,y2) or neighbor_has_number(dn_box,y1,y2) or date_signal(y1,y2):
            return None
        value,confident=_choose_printed_total(candidates)
        if not _printed_total_value_is_plausible(value,len(bands)):
            value=None; confident=False
        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':method,'band_index':band_index}
""",
"""    def blank_total_row(y1,y2,method,band_index=None):
        candidates=read_value(y1,y2)
        if not candidates: return None
        if neighbor_has_number(up_box,y1,y2) or neighbor_has_number(dn_box,y1,y2) or date_signal(y1,y2):
            return None
        value,confident=_choose_printed_total(candidates)
        if not _printed_total_value_is_plausible(value,len(bands)):
            value=None; confident=False
        preview=cut(value_box,y1,y2)
        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':method,'band_index':band_index,
                'preview':preview.copy() if preview is not None and getattr(preview,'size',0) else None}
""",
'blank total preview')

replace_once(
"""        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':'labelled total row','band_index':band_index}
""",
"""        preview=cut(value_box,y1,y2)
        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':'labelled total row','band_index':band_index,
                'preview':preview.copy() if preview is not None and getattr(preview,'size',0) else None}
""",
'labelled total preview')

# v82 regression exposed a typo: callers pass "pipes", so the singular check
# prevented the suffix corroboration guard from ever running on pair-table pipes.
replace_once(
"if kind=='pipe' and not match and match_status=='NEW PIPE':",
"if kind=='pipes' and not match and match_status=='NEW PIPE':",
'pipe suffix guard kind')

marker='\n\nclass ProgressFillButton(tk.Canvas):\n'
if marker not in src:
    raise SystemExit('missing TotalLengthVerifyDialog insertion point')
dialog=r'''

class TotalLengthVerifyDialog(tk.Toplevel):
    """Verify a printed activity total while showing the exact PDF total crop."""
    def __init__(self,parent,check,initial=''):
        super().__init__(parent); self.result=None; self.crop_photos=[]
        apply_app_icon(self)
        self.title('Verify Total Length'); self.transient(parent); self.grab_set(); self.resizable(False,False)
        ttk.Label(self,text=f"Work Order {check.get('wo','')} — {check.get('kind','')}",
                  font=('Segoe UI',12,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',padx=14,pady=(12,5))

        preview_row=1; previews=0
        for source in check.get('sources',[]) or []:
            info=source.get('info') or {}; crop=info.get('preview')
            if crop is None or not getattr(crop,'size',0):
                continue
            try:
                image=Image.fromarray(crop)
                if image.width<360:
                    scale=min(3.0,360.0/max(1,image.width))
                    image=image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.LANCZOS)
                image.thumbnail((560,130),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(image,master=self); self.crop_photos.append(photo)
                ttk.Label(self,text=f"PDF page {source.get('page','?')} printed total:").grid(
                    row=preview_row,column=0,sticky='ne',padx=(14,8),pady=5)
                ttk.Label(self,image=photo).grid(row=preview_row,column=1,sticky='w',padx=(0,14),pady=5)
                preview_row+=1; previews+=1
            except Exception:
                continue
        if not previews:
            ttk.Label(self,text='Printed-total image was not available for this check.',foreground='#8A5200').grid(
                row=preview_row,column=0,columnspan=2,sticky='w',padx=14,pady=5)
            preview_row+=1

        page_text=', '.join(str(p) for p in check.get('pages',[])) or 'unknown'
        expected=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')
        details=(f"PDF page(s): {page_text}\n"
                 f"PDF total read: {initial or 'UNREADABLE'}\n"
                 f"Summary length total: {check.get('summary_total',0):g}\n")
        if expected is not None:
            details+=f"Difference: {abs(check.get('difference') or 0):g} ft\n"
        details+=f"Missing summary lengths: {check.get('missing',0)}"
        ttk.Label(self,text=details,justify='left').grid(row=preview_row,column=0,columnspan=2,sticky='w',padx=14,pady=(7,8))
        preview_row+=1

        ttk.Label(self,text='Verified TOTAL LENGTH:').grid(row=preview_row,column=0,sticky='e',padx=(14,8),pady=6)
        self.value=tk.StringVar(value=initial)
        entry=ttk.Entry(self,textvariable=self.value,width=24); entry.grid(row=preview_row,column=1,sticky='w',padx=(0,14),pady=6)
        entry.focus_set(); entry.select_range(0,'end')
        preview_row+=1
        ttk.Label(self,text='This corrects only the OCR of the printed total; it does not change any row length.\nThe master update remains blocked until the verified total and summary lengths match exactly.',
                  foreground='#8A5200',justify='left').grid(row=preview_row,column=0,columnspan=2,sticky='w',padx=14,pady=(5,8))
        preview_row+=1
        buttons=ttk.Frame(self); buttons.grid(row=preview_row,column=0,columnspan=2,pady=(0,12))
        ttk.Button(buttons,text='Cancel',command=self.cancel).pack(side='left',padx=6)
        ttk.Button(buttons,text='Use Verified Total',command=self.ok,style='Primary.TButton').pack(side='left',padx=6)
        self.bind('<Return>',lambda _event:self.ok()); self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.update_idletasks(); self.geometry(f'+{parent.winfo_rootx()+80}+{parent.winfo_rooty()+70}')
    def ok(self):
        try:
            value=float(self.value.get().replace(',','').strip())
            if value<=0: raise ValueError
        except Exception:
            messagebox.showerror('Invalid total','Enter a positive numeric total length.',parent=self); return
        self.result=value; self.destroy()
    def cancel(self): self.result=None; self.destroy()
'''
src=src.replace(marker,dialog+marker,1)

old_methods=r'''    def _total_warning_for_record_index(self,index):
        for check in self.total_validations:
            if check.get('passed') or check.get('first_record_index')!=index:
                continue
            return str(check.get('warning') or '')
        return ''
'''
new_methods=r'''    def _total_error_iid(self,check):
        key=f"{check.get('wo','')}|{check.get('kind','')}|total-length"
        return 'group-error:'+hashlib.sha1(key.encode()).hexdigest()[:16]
    def show_total_summary_error(self,check,follow=False):
        """Give work-order-wide total failures their own Live Summary row."""
        iid=self._total_error_iid(check)
        warning=str(check.get('warning') or '')
        if check.get('passed') or not warning:
            if self.tree.exists(iid): self.tree.delete(iid)
            return
        values=('','','','',str(check.get('wo','')),'','',warning)
        tags=('total_warning',)
        if self.tree.exists(iid):
            self.tree.item(iid,values=values,tags=tags)
        else:
            children=list(self.tree.get_children())
            same_wo=[]
            for child in children:
                try:
                    if str(self.tree.set(child,'wo'))==str(check.get('wo','')):
                        same_wo.append(self.tree.index(child))
                except Exception:
                    pass
            insert_at=(max(same_wo)+1) if same_wo else 'end'
            self.tree.insert('','end' if insert_at=='end' else insert_at,iid=iid,values=values,tags=tags)
        if follow: self.tree.see(iid)
'''
replace_once(old_methods,new_methods,'group total summary helpers')

replace_once(
"""        display_status=review_status(r)
        group_warning=self._total_warning_for_record_index(index)
        if group_warning:
            display_status=group_warning if display_status=='Matched' else display_status+'; '+group_warning
""",
"""        display_status=review_status(r)
""",
'keep group warnings off asset rows')

replace_once(
"""        if redraw:
            for index,_ in indexed: self.show_summary_record(index)
        self._schedule_total_outlines()
""",
"""        if redraw:
            for index,_ in indexed: self.show_summary_record(index)
        self.show_total_summary_error(check)
        self._schedule_total_outlines()
""",
'refresh dedicated group error row')

old_prompt=r'''        while True:
            raw=simpledialog.askstring(
                'Verify Total Length',
                f"Work Order {check.get('wo','')} — {check.get('kind','')}\n\n"
                f"PDF page(s): {page_text}\n"
                f"PDF total read: {initial or 'UNREADABLE'}\n"
                f"Summary length total: {check.get('summary_total',0):g}\n"
                + (f"Difference: {abs(check.get('difference') or 0):g} ft\n" if expected is not None else '') +
                f"Missing summary lengths: {check.get('missing',0)}\n\n"
                'Enter the TOTAL LENGTH you verify by looking at the PDF.\n'
                'Changing this value corrects only the OCR of the printed total; it does not change any row length.\n\n'
                'The master update remains blocked until the verified total and the summary lengths match exactly.',
                initialvalue=initial,parent=self)
            if raw is None: return False
            try:
                verified=float(str(raw).replace(',','').strip())
                if verified<=0: raise ValueError
            except Exception:
                messagebox.showerror('Invalid total','Enter a positive numeric total length.',parent=self)
                continue
            check['verified_total']=verified; check['manual_verified']=True
            # A corrected total is a new validation target. Give the same suspect
            # cells one conservative reread before asking the user to edit rows.
            if check.get('kind')=='Cleaning':
                self._retry_cleaning_total_mismatch(check,force=True)
            passed=self.refresh_total_check(check)
            if passed:
                messagebox.showinfo('Total Length Verified',
                    f"Work Order {check.get('wo','')} {check.get('kind','')} now reconciles exactly at {verified:g} ft.",parent=self)
            else:
                messagebox.showwarning('Total Still Does Not Match',
                    f"The verified PDF total is {verified:g} ft, but the summary currently totals {check.get('summary_total',0):g} ft.\n\n"
                    'The work-order group remains outlined in red and Update Master is blocked until the row lengths are corrected. Rows with their own length difference remain highlighted red.',parent=self)
            return passed
'''
new_prompt=r'''        dlg=TotalLengthVerifyDialog(self,check,initial); self.wait_window(dlg)
        if dlg.result is None: return False
        verified=float(dlg.result)
        check['verified_total']=verified; check['manual_verified']=True
        # A corrected total is a new validation target. Give the same suspect
        # cells one conservative reread before asking the user to edit rows.
        if check.get('kind')=='Cleaning':
            self._retry_cleaning_total_mismatch(check,force=True)
        passed=self.refresh_total_check(check)
        if passed:
            messagebox.showinfo('Total Length Verified',
                f"Work Order {check.get('wo','')} {check.get('kind','')} now reconciles exactly at {verified:g} ft.",parent=self)
        else:
            messagebox.showwarning('Total Still Does Not Match',
                f"The verified PDF total is {verified:g} ft, but the summary currently totals {check.get('summary_total',0):g} ft.\n\n"
                'The work-order group remains outlined in red and Update Master is blocked until the row lengths are corrected. Rows with their own length difference remain highlighted red.',parent=self)
        return passed
'''
replace_once(old_prompt,new_prompt,'image total verification popup')

replace_once(
"""        if iid.startswith('ticket:'):
            self.edit_trouble_ticket(int(iid.split(':',1)[1]))
            return
        i=int(iid.split(':',1)[1]); r=self.records[i]
""",
"""        if iid.startswith('ticket:'):
            self.edit_trouble_ticket(int(iid.split(':',1)[1]))
            return
        if iid.startswith('group-error:'):
            messagebox.showinfo('Work Order Validation','This row is a work-order-wide validation message, not an individual asset row.',parent=self)
            return
        i=int(iid.split(':',1)[1]); r=self.records[i]
""",
'non-editable group error row')

path.write_text(src,encoding='utf-8')

# Keep the v82 suffix regression aligned with the actual plural parser kind.
test=Path('working_source/tests/regression_v82_suffix_guard.py')
txt=test.read_text(encoding='utf-8')
old="assert \"if kind=='pipe' and not match and match_status=='NEW PIPE':\" in src"
new="assert \"if kind=='pipes' and not match and match_status=='NEW PIPE':\" in src"
if old not in txt: raise SystemExit('missing suffix regression target')
test.write_text(txt.replace(old,new,1),encoding='utf-8')

reg=Path('working_source/tests/regression_v83_total_preview_group_errors.py')
reg.write_text(r'''from pathlib import Path

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

# The total reader must retain the exact PDF value-cell pixels used as evidence.
assert "'preview':None" in src
assert "preview=cut(value_box,y1,y2)" in src
assert "'preview':preview.copy()" in src

# The verification UI is no longer a text-only simpledialog; it displays each
# available source-page total crop and returns the verified numeric value.
assert 'class TotalLengthVerifyDialog(tk.Toplevel):' in src
assert "PDF page {source.get('page','?')} printed total:" in src
assert 'ImageTk.PhotoImage(image,master=self)' in src
assert 'dlg=TotalLengthVerifyDialog(self,check,initial); self.wait_window(dlg)' in src

# Group-wide total failures get their own neutral/blank summary row instead of
# being appended to the first asset row.
assert 'def show_total_summary_error(self,check,follow=False):' in src
assert "values=('','','','',str(check.get('wo','')),'','',warning)" in src
assert "tags=('total_warning',)" in src
assert 'self.show_total_summary_error(check)' in src
assert '_total_warning_for_record_index' not in src
assert 'group_warning=' not in src
assert "if iid.startswith('group-error:'):" in src

# Pair parser is called with kind='pipes'; the suffix guard must use that same value.
assert "if kind=='pipes' and not match and match_status=='NEW PIPE':" in src
assert "if kind=='pipe' and not match and match_status=='NEW PIPE':" not in src

print('v83 total preview and group-error summary regression passed.')
''',encoding='utf-8')
print('v83 total preview/group-error patch applied')
