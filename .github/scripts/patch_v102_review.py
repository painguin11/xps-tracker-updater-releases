from pathlib import Path

app = Path('working_source/app/reno_scan_updater.py')
text = app.read_text(encoding='utf-8')
assert "APP_VERSION = '101'" in text, 'expected v101 development source'

old_preview = """            if crop is not None and getattr(crop,'size',0):
                image=Image.fromarray(crop); image.thumbnail((420,125),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(image,master=self); self.crop_photos.append(photo)
                ttk.Label(self,image=photo).grid(row=next_row,column=2,sticky='w',padx=(6,12),pady=4)
"""
new_preview = """            if crop is not None and getattr(crop,'size',0):
                # The Manhole survey count is often handwritten very small inside
                # the large description box. Show substantially more pixels than
                # the normal field previews so the user can verify the count.
                image=Image.fromarray(crop)
                image.thumbnail((720,300),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(image,master=self); self.crop_photos.append(photo)
                ttk.Label(self,image=photo).grid(row=next_row,column=2,sticky='w',padx=(6,12),pady=4)
"""
assert text.count(old_preview) == 1, 'manhole count preview baseline changed'
text = text.replace(old_preview, new_preview, 1)

new_dialogs = r'''

class DiscardWorkOrdersDialog(tk.Toplevel):
    """Choose one or more analyzed work orders to remove from the pending update."""
    def __init__(self,parent,work_orders,initial_wo=''):
        super().__init__(parent); self.result=None; self.work_orders=list(work_orders or [])
        apply_app_icon(self)
        self.title('Discard Work Order(s)'); self.transient(parent); self.grab_set(); self.resizable(False,True)
        ttk.Label(self,text='Select the complete work order(s) to discard from this pending update.',
                  font=('Segoe UI',11,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',padx=14,pady=(14,5))
        ttk.Label(self,text='Discarding here does not change the master spreadsheet. Only the work orders left in the review will be written when Update Master is clicked.',
                  wraplength=720,justify='left').grid(row=1,column=0,columnspan=2,sticky='w',padx=14,pady=(0,10))
        frame=ttk.Frame(self); frame.grid(row=2,column=0,columnspan=2,sticky='nsew',padx=14,pady=(0,10))
        self.listbox=tk.Listbox(frame,selectmode=tk.EXTENDED,exportselection=False,width=82,
                                height=max(4,min(12,len(self.work_orders))),font=('Segoe UI',10))
        scroll=ttk.Scrollbar(frame,orient='vertical',command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.grid(row=0,column=0,sticky='nsew'); scroll.grid(row=0,column=1,sticky='ns')
        frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
        initial=str(initial_wo or '').strip(); preselected=False
        for index,item in enumerate(self.work_orders):
            wo=str(item.get('wo') or '').strip()
            rows=int(item.get('rows') or 0); tickets=int(item.get('tickets') or 0)
            validations=int(item.get('validation_items') or 0)
            label=f'W/O {wo} — {rows} extracted row(s), {tickets} trouble ticket(s)'
            if validations: label+=f', {validations} validation item(s)'
            self.listbox.insert('end',label)
            if initial and wo==initial:
                self.listbox.selection_set(index); self.listbox.see(index); preselected=True
        if not preselected and len(self.work_orders)==1:
            self.listbox.selection_set(0)
        buttons=ttk.Frame(self); buttons.grid(row=3,column=0,columnspan=2,pady=(0,14))
        ttk.Button(buttons,text='Cancel',command=self.cancel).pack(side='left',padx=6)
        ttk.Button(buttons,text='Discard Selected Work Order(s)',command=self.accept,style='Danger.TButton').pack(side='left',padx=6)
        self.listbox.bind('<Double-1>',lambda _event:self.accept())
        self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.rowconfigure(2,weight=1); self.columnconfigure(0,weight=1)
        self.update_idletasks(); self.geometry(f'+{parent.winfo_rootx()+80}+{parent.winfo_rooty()+70}')
    def accept(self):
        selected=list(self.listbox.curselection())
        if not selected:
            messagebox.showinfo('Discard Work Order(s)','Select at least one work order.',parent=self); return
        self.result=[str(self.work_orders[index].get('wo') or '').strip() for index in selected]
        self.destroy()
    def cancel(self): self.result=None; self.destroy()


class ProblemWorkOrdersDialog(tk.Toplevel):
    """Offer a whole-W/O escape hatch when Update Master sees unresolved review items."""
    def __init__(self,parent,problems):
        super().__init__(parent); self.result=None; self.problems=dict(problems or {})
        apply_app_icon(self)
        self.title('Problem Work Orders'); self.transient(parent); self.grab_set(); self.resizable(False,True)
        ttk.Label(self,text='Some work orders are not fully green / ready.',font=('Segoe UI',11,'bold')).grid(
            row=0,column=0,columnspan=2,sticky='w',padx=14,pady=(14,5))
        ttk.Label(self,text=(
            'You can ignore the entire problem work order(s) and continue updating only the clean work orders, '
            'continue with the existing review/prompts, or return to the summary without writing anything.'),
            wraplength=760,justify='left').grid(row=1,column=0,columnspan=2,sticky='w',padx=14,pady=(0,10))
        box=tk.Text(self,width=92,height=max(5,min(14,len(self.problems)*2+2)),wrap='word',font=('Segoe UI',10),
                    relief='solid',borderwidth=1,background='white')
        box.grid(row=2,column=0,columnspan=2,sticky='nsew',padx=14,pady=(0,10))
        for wo,reasons in self.problems.items():
            box.insert('end',f"W/O {wo}: {', '.join(reasons)}\n")
        box.configure(state='disabled')
        buttons=ttk.Frame(self); buttons.grid(row=3,column=0,columnspan=2,pady=(0,14))
        ttk.Button(buttons,text='Back to Review',command=self.cancel).pack(side='left',padx=6)
        ttk.Button(buttons,text='Continue Current Review Flow',command=lambda:self.finish('continue')).pack(side='left',padx=6)
        ttk.Button(buttons,text='Ignore Problem Work Orders & Continue',command=lambda:self.finish('ignore'),style='Danger.TButton').pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.rowconfigure(2,weight=1); self.columnconfigure(0,weight=1)
        self.update_idletasks(); self.geometry(f'+{parent.winfo_rootx()+65}+{parent.winfo_rooty()+60}')
    def finish(self,value): self.result=value; self.destroy()
    def cancel(self): self.result=None; self.destroy()
'''
marker = '\n\nclass TotalLengthVerifyDialog(tk.Toplevel):'
assert text.count(marker) == 1, 'TotalLengthVerifyDialog marker changed'
text = text.replace(marker, new_dialogs + marker, 1)

old_controls = """        ttk.Button(controls,text='Edit Selected',command=self.edit_selected).pack(side='left',padx=8)
        ttk.Button(controls,text='2. Update Master',command=self.update_master,style='Success.TButton').pack(side='left',padx=8)
"""
new_controls = """        ttk.Button(controls,text='Edit Selected',command=self.edit_selected).pack(side='left',padx=8)
        ttk.Button(controls,text='Discard Work Order(s)',command=self.discard_work_orders).pack(side='left',padx=8)
        ttk.Button(controls,text='2. Update Master',command=self.update_master,style='Success.TButton').pack(side='left',padx=8)
"""
assert text.count(old_controls) == 1, 'main review controls baseline changed'
text = text.replace(old_controls, new_controls, 1)

new_methods = r'''    def _work_order_choices(self):
        """Return current review work orders in packet order with discard counts."""
        order=[]; seen=set()
        def remember(value):
            wo=str(value or '').strip()
            if wo and wo!='UNKNOWN' and wo not in seen:
                seen.add(wo); order.append(wo)
        for group in self.groups: remember(group.get('wo'))
        for collection in (self.records,self.trouble_tickets,self.total_validations,
                           self.manhole_count_validations,self.unprocessed_pages):
            for item in collection: remember(item.get('wo'))
        choices=[]
        for wo in order:
            same=lambda item:str(item.get('wo') or '').strip()==wo
            choices.append({
                'wo':wo,
                'rows':sum(1 for item in self.records if same(item)),
                'tickets':sum(1 for item in self.trouble_tickets if same(item)),
                'validation_items':(
                    sum(1 for item in self.total_validations if same(item))+
                    sum(1 for item in self.manhole_count_validations if same(item))+
                    sum(1 for item in self.unprocessed_pages if same(item))),
            })
        return choices

    def _selected_work_order(self):
        try:
            selected=self.tree.selection()
            return str(self.tree.set(selected[0],'wo')).strip() if selected else ''
        except Exception:
            return ''

    def _problem_work_orders(self):
        """Return visible/relevant review problems grouped by complete work order."""
        problems={}
        def add(wo,reason):
            wo=str(wo or '').strip()
            if not wo or wo=='UNKNOWN': return
            bucket=problems.setdefault(wo,[])
            if reason not in bucket: bucket.append(reason)
        row_counts={}
        for record in self.records:
            if record_needs_review(record):
                wo=str(record.get('wo') or '').strip(); row_counts[wo]=row_counts.get(wo,0)+1
        for wo,count in row_counts.items(): add(wo,f'{count} extracted row(s) need review')
        ticket_counts={}
        for ticket in self.trouble_tickets:
            if trouble_ticket_status(ticket).startswith('Review'):
                wo=str(ticket.get('wo') or '').strip(); ticket_counts[wo]=ticket_counts.get(wo,0)+1
        for wo,count in ticket_counts.items(): add(wo,f'{count} trouble ticket(s) need review')
        for check in self.total_validations:
            if not check.get('passed'): add(check.get('wo'),f"{check.get('kind','')} total length is not verified")
        for check in self.manhole_count_validations:
            if not check.get('passed'): add(check.get('wo'),'Manhole count mismatch')
        page_counts={}
        for item in self.unprocessed_pages:
            wo=str(item.get('wo') or '').strip(); page_counts[wo]=page_counts.get(wo,0)+1
        for wo,count in page_counts.items(): add(wo,f'{count} PDF page(s) could not be processed')
        return problems

    def _discard_work_order_set(self,work_orders):
        """Remove whole W/O groups from every pending write/validation collection."""
        selected={str(wo).strip() for wo in (work_orders or []) if str(wo).strip()}
        if not selected: return (0,0)
        belongs=lambda item:str(item.get('wo') or '').strip() in selected
        removed_rows=sum(1 for item in self.records if belongs(item))
        removed_tickets=sum(1 for item in self.trouble_tickets if belongs(item))
        self.records=[item for item in self.records if not belongs(item)]
        self.trouble_tickets=[item for item in self.trouble_tickets if not belongs(item)]
        self.groups=[item for item in self.groups if not belongs(item)]
        self.total_validations=[item for item in self.total_validations if not belongs(item)]
        self.manhole_count_validations=[item for item in self.manhole_count_validations if not belongs(item)]
        self.unprocessed_pages=[item for item in self.unprocessed_pages if not belongs(item)]
        return removed_rows,removed_tickets

    def _rebuild_review_tree(self):
        """Re-index every visible review row after a whole-work-order removal."""
        try: vertical_position=self.tree.yview()[0]
        except Exception: vertical_position=0.0
        self._clear_total_outlines(); self.tree.delete(*self.tree.get_children())
        for index in range(len(self.records)): self.show_summary_record(index)
        for index in range(len(self.trouble_tickets)): self.show_summary_ticket(index)
        for check in self.total_validations: self.refresh_total_check(check,redraw=False)
        self.refresh_unprocessed_summary()
        for check in self.manhole_count_validations: self.show_manhole_count_summary(check)
        try:
            self.tree.update_idletasks(); self.tree.yview_moveto(vertical_position)
        except Exception: pass
        self._schedule_total_outlines()

    def discard_work_orders(self):
        """Manual review control for removing complete work orders before write."""
        if getattr(self,'_analysis_running',False):
            messagebox.showinfo('Analysis In Progress','Finish or cancel the current analysis before discarding a work order.',parent=self); return
        choices=self._work_order_choices()
        if not choices:
            messagebox.showinfo('Discard Work Order(s)','There are no analyzed work orders to discard.',parent=self); return
        dlg=DiscardWorkOrdersDialog(self,choices,self._selected_work_order()); self.wait_window(dlg)
        if not dlg.result: return
        selected={str(wo).strip() for wo in dlg.result if str(wo).strip()}
        selected_items=[item for item in choices if item['wo'] in selected]
        details='\n'.join(f"W/O {item['wo']}: {item['rows']} extracted row(s), {item['tickets']} trouble ticket(s)" for item in selected_items)
        if not messagebox.askyesno(
                'Discard Work Order(s)',
                'Discard all analyzed data for the selected work order(s)?\n\n'+details+
                '\n\nTheir extracted rows, trouble tickets, and validation items will be removed from this review. '
                'The master spreadsheet is not changed now. Update Master will write only the work orders that remain.',
                parent=self):
            return
        removed_rows,removed_tickets=self._discard_work_order_set(selected)
        self._rebuild_review_tree()
        discarded=', '.join(sorted(selected)); remaining=self._work_order_choices()
        if self.records or self.trouble_tickets:
            self.status.set(
                f'Discarded W/O {discarded}: removed {removed_rows} extracted row(s) and {removed_tickets} trouble ticket(s). '
                f'{len(remaining)} work order(s) remain; Update Master will process only the remaining items.')
        else:
            self.status.set(f'Discarded W/O {discarded}. Nothing remains to update from the analyzed work orders.')

    def resolve_problem_work_orders_for_update(self):
        """Offer to exclude all not-green W/Os while preserving the legacy review path."""
        problems=self._problem_work_orders()
        if not problems: return True
        dlg=ProblemWorkOrdersDialog(self,problems); self.wait_window(dlg)
        if dlg.result is None: return False
        if dlg.result=='continue': return True
        if dlg.result!='ignore': return False
        selected=set(problems)
        removed_rows,removed_tickets=self._discard_work_order_set(selected)
        self._rebuild_review_tree()
        discarded=', '.join(sorted(selected))
        if not self.records and not self.trouble_tickets:
            messagebox.showinfo('Nothing Left To Update',
                f'Ignored problem W/O {discarded}. No clean work orders remain to update.',parent=self)
            self.status.set('All problem work orders were ignored; nothing remains to update.')
            return False
        self.status.set(
            f'Ignored problem W/O {discarded}: removed {removed_rows} extracted row(s) and {removed_tickets} trouble ticket(s). '
            'Continuing Update Master with only the remaining work orders.')
        return True

'''
marker = '    def cancel_current_process(self):\n'
assert text.count(marker) == 1, 'cancel_current_process marker changed'
text = text.replace(marker, new_methods + marker, 1)

old_update = """    def update_master(self):
        if not self.records and not self.trouble_tickets: messagebox.showwarning('Nothing to update','Analyze a PDF first.'); return
        if not self.resolve_pipe_duplicate_groups(prompt=True,update_mode=True): return
"""
new_update = """    def update_master(self):
        if not self.records and not self.trouble_tickets: messagebox.showwarning('Nothing to update','Analyze a PDF first.'); return
        if not self.resolve_problem_work_orders_for_update(): return
        if not self.records and not self.trouble_tickets: messagebox.showwarning('Nothing to update','No work orders remain in the pending update.'); return
        if not self.resolve_pipe_duplicate_groups(prompt=True,update_mode=True): return
"""
assert text.count(old_update) == 1, 'update_master entry baseline changed'
text = text.replace(old_update, new_update, 1)

app.write_text(text, encoding='utf-8')

test = Path('working_source/tests/regression_v102_discard_work_orders.py')
test.write_text(r'''from pathlib import Path
s=(Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py').read_text(encoding='utf-8')

# Manual discard supports multiple W/Os while Edit Selected remains single-row.
d=s[s.index('class DiscardWorkOrdersDialog'):s.index('\n\nclass ProblemWorkOrdersDialog',s.index('class DiscardWorkOrdersDialog'))]
for token in ("selectmode=tk.EXTENDED","Discard Selected Work Order(s)","self.result=[str(self.work_orders[index].get('wo')"):
    assert token in d,token
assert "selectmode='browse'" in s
assert "text='Discard Work Order(s)',command=self.discard_work_orders" in s

# Update Master has an explicit whole-W/O option for not-green groups while the
# previous review path remains available.
p=s[s.index('class ProblemWorkOrdersDialog'):s.index('\n\nclass TotalLengthVerifyDialog',s.index('class ProblemWorkOrdersDialog'))]
for token in ('Ignore Problem Work Orders & Continue','Continue Current Review Flow','Back to Review'):
    assert token in p,token
u=s[s.index('    def update_master(self):'):]
assert u.index('self.resolve_problem_work_orders_for_update()') < u.index('self.resolve_pipe_duplicate_groups(prompt=True,update_mode=True)')

# Whole-W/O removal clears everything that can later write or block that W/O.
m=s[s.index('    def _discard_work_order_set(self,work_orders):'):s.index('\n    def _rebuild_review_tree',s.index('    def _discard_work_order_set(self,work_orders):'))]
for token in (
    'self.records=[item for item in self.records if not belongs(item)]',
    'self.trouble_tickets=[item for item in self.trouble_tickets if not belongs(item)]',
    'self.groups=[item for item in self.groups if not belongs(item)]',
    'self.total_validations=[item for item in self.total_validations if not belongs(item)]',
    'self.manhole_count_validations=[item for item in self.manhole_count_validations if not belongs(item)]',
    'self.unprocessed_pages=[item for item in self.unprocessed_pages if not belongs(item)]',
): assert token in m,token

# Problem grouping covers red/review rows, trouble tickets, failed totals/counts,
# and unprocessed pages instead of looking at only one validation mechanism.
g=s[s.index('    def _problem_work_orders(self):'):s.index('\n    def _discard_work_order_set',s.index('    def _problem_work_orders(self):'))]
for token in ('record_needs_review(record)','trouble_ticket_status(ticket)',"not check.get('passed')",'self.unprocessed_pages'):
    assert token in g,token

# The Manhole count confirmation retains its source crop but displays it larger.
c=s[s.index('class ConfirmDialog'):s.index('\n\nclass DiscardWorkOrdersDialog',s.index('class ConfirmDialog'))]
assert 'description_preview' in c
assert 'image.thumbnail((720,300),Image.Resampling.LANCZOS)' in c
assert 'image.thumbnail((420,125),Image.Resampling.LANCZOS)' not in c
print('v102 work-order discard / problem-WO / Manhole preview regression passed')
''',encoding='utf-8')
