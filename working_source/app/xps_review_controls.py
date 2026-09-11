import re

import reno_scan_updater as base


tk=base.tk
ttk=base.ttk
messagebox=base.messagebox
Image=base.Image
ImageTk=base.ImageTk


class EnhancedConfirmDialog(tk.Toplevel):
    """v101 work-order confirmation with a larger Manhole-count source image."""
    def __init__(self,parent,guesses):
        super().__init__(parent); self.result=None
        base.apply_app_icon(self)
        self.guessed_date=guesses.get('date')
        self.title('Confirm Work Order'); self.transient(parent); self.grab_set()
        self.resizable(False,False)
        ttk.Label(self,text='Confirm Work Order Information',font=('Segoe UI',12,'bold')).grid(
            row=0,column=0,columnspan=3,padx=12,pady=(12,8),sticky='w')
        self.vars={}
        vals=[('W/O',guesses.get('wo',''),'wo_preview'),
              ('Operator (full name)',guesses.get('operator',''),'operator_preview'),
              ('Truck',guesses.get('truck',''),'truck_preview')]
        self.crop_photos=[]
        for row,(label,value,preview_key) in enumerate(vals,1):
            ttk.Label(self,text=label+':').grid(row=row,column=0,sticky='e',padx=(12,6),pady=6)
            var=tk.StringVar(value=value); self.vars[label]=var
            entry=ttk.Entry(self,textvariable=var,width=34)
            entry.grid(row=row,column=1,sticky='w',padx=6,pady=6)
            if not str(value).strip(): entry.focus_set()
            crop=Image.fromarray(guesses.get(preview_key,guesses['preview']))
            crop.thumbnail((360,75))
            photo=ImageTk.PhotoImage(crop); self.crop_photos.append(photo)
            ttk.Label(self,image=photo).grid(row=row,column=2,sticky='w',padx=(6,12),pady=4)

        next_row=4
        self.manhole_count_var=None
        if guesses.get('expect_manhole_count'):
            ttk.Label(self,text='Expected Manholes:').grid(
                row=next_row,column=0,sticky='e',padx=(12,6),pady=6)
            self.manhole_count_var=tk.StringVar(value=str(guesses.get('manhole_count_guess') or ''))
            count_entry=ttk.Entry(self,textvariable=self.manhole_count_var,width=12)
            count_entry.grid(row=next_row,column=1,sticky='w',padx=6,pady=6)
            if not self.manhole_count_var.get().strip(): count_entry.focus_set()
            crop=guesses.get('description_preview')
            if crop is not None and getattr(crop,'size',0):
                image=Image.fromarray(crop)
                # This is deliberately much larger than the ordinary field crops:
                # the written MH count can be very small in the description box.
                image.thumbnail((720,300),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(image,master=self); self.crop_photos.append(photo)
                ttk.Label(self,image=photo).grid(
                    row=next_row,column=2,sticky='w',padx=(6,12),pady=4)
            else:
                ttk.Label(self,text='Description preview unavailable — check PDF',foreground='#8A5200').grid(
                    row=next_row,column=2,sticky='w',padx=(6,12),pady=4)
            next_row+=1

        self.initials_var=tk.StringVar(value=base.operator_master_name(self.vars['Operator (full name)'].get()))
        ttk.Label(self,text='Operator:').grid(row=next_row,column=0,sticky='e',padx=(12,6),pady=5)
        ttk.Label(self,textvariable=self.initials_var,font=('Segoe UI',10,'bold')).grid(
            row=next_row,column=1,sticky='w',padx=6,pady=5)
        self.vars['Operator (full name)'].trace_add(
            'write',lambda *_: self.initials_var.set(
                base.operator_master_name(self.vars['Operator (full name)'].get()) or 'NEEDS FIRST + LAST'))
        next_row+=1
        ttk.Label(self,text='Check each scan image beside its field, pre-filled text is only a suggestion.',
                  foreground='#8A5200').grid(row=next_row,column=0,columnspan=3,padx=12,pady=(5,8))
        next_row+=1
        buttons=ttk.Frame(self); buttons.grid(row=next_row,column=0,columnspan=3,pady=(0,12))
        ttk.Button(buttons,text='Cancel',command=self.cancel).pack(side='left',padx=6)
        ttk.Button(buttons,text='Confirm',command=self.ok,style='Primary.TButton').pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',self.cancel)

    def ok(self):
        wo=self.vars['W/O'].get().strip()
        truck=self.vars['Truck'].get().strip().upper()
        full_op=self.vars['Operator (full name)'].get().strip()
        if not re.fullmatch(r'\d{4,5}',wo):
            messagebox.showwarning('Work order number','W/O must be 4 or 5 digits.',parent=self); return
        if not re.fullmatch(r'[A-Z]{2}\d{2}',truck):
            messagebox.showwarning('Check truck','Truck must be exactly 2 letters followed by 2 numbers, such as CT01.',parent=self); return
        master_op=base.operator_master_name(full_op)
        if not master_op:
            messagebox.showwarning('Operator name','Confirm or enter the operator name.',parent=self); return
        expected_manhole_count=None
        if self.manhole_count_var is not None:
            raw_count=self.manhole_count_var.get().strip()
            if not re.fullmatch(r'\d{1,3}',raw_count) or int(raw_count)<1:
                messagebox.showwarning(
                    'Manhole count',
                    'Enter the total number of Manhole surveys written in the Description of work performed section.',
                    parent=self); return
            expected_manhole_count=int(raw_count)
        self.result={'wo':wo,'truck':truck,'operator':master_op,'operator_full':full_op,
                     'date':self.guessed_date,'expected_manhole_count':expected_manhole_count}
        self.destroy()

    def cancel(self):
        self.result=None; self.destroy()


class DiscardWorkOrdersDialog(tk.Toplevel):
    def __init__(self,parent,work_orders,initial_wo=''):
        super().__init__(parent); self.result=None; self.work_orders=list(work_orders or [])
        base.apply_app_icon(self)
        self.title('Discard Work Order(s)'); self.transient(parent); self.grab_set(); self.resizable(False,True)
        ttk.Label(self,text='Select the complete work order(s) to discard from this pending update.',
                  font=('Segoe UI',11,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',padx=14,pady=(14,5))
        ttk.Label(self,text=(
            'Discarding here does not change the master spreadsheet. Only the work orders left in the review '
            'will be written when Update Master is clicked.'),wraplength=720,justify='left').grid(
            row=1,column=0,columnspan=2,sticky='w',padx=14,pady=(0,10))
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
            label=f"W/O {wo} — {int(item.get('rows') or 0)} extracted row(s), {int(item.get('tickets') or 0)} trouble ticket(s)"
            validations=int(item.get('validation_items') or 0)
            if validations: label+=f', {validations} validation item(s)'
            self.listbox.insert('end',label)
            if initial and wo==initial:
                self.listbox.selection_set(index); self.listbox.see(index); preselected=True
        if not preselected and len(self.work_orders)==1: self.listbox.selection_set(0)
        buttons=ttk.Frame(self); buttons.grid(row=3,column=0,columnspan=2,pady=(0,14))
        ttk.Button(buttons,text='Cancel',command=self.cancel).pack(side='left',padx=6)
        ttk.Button(buttons,text='Discard Selected Work Order(s)',command=self.accept,
                   style='Danger.TButton').pack(side='left',padx=6)
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

    def cancel(self):
        self.result=None; self.destroy()


class ProblemWorkOrdersDialog(tk.Toplevel):
    def __init__(self,parent,problems):
        super().__init__(parent); self.result=None; self.problems=dict(problems or {})
        base.apply_app_icon(self)
        self.title('Problem Work Orders'); self.transient(parent); self.grab_set(); self.resizable(False,True)
        ttk.Label(self,text='Some work orders are not fully green / ready.',font=('Segoe UI',11,'bold')).grid(
            row=0,column=0,columnspan=2,sticky='w',padx=14,pady=(14,5))
        ttk.Label(self,text=(
            'Ignore the entire problem work order(s) and update only the clean work orders, continue through '
            'the existing individual review prompts, or return to the summary without writing anything.'),
            wraplength=760,justify='left').grid(row=1,column=0,columnspan=2,sticky='w',padx=14,pady=(0,10))
        box=tk.Text(self,width=92,height=max(5,min(14,len(self.problems)*2+2)),wrap='word',
                    font=('Segoe UI',10),relief='solid',borderwidth=1,background='white')
        box.grid(row=2,column=0,columnspan=2,sticky='nsew',padx=14,pady=(0,10))
        for wo,reasons in self.problems.items(): box.insert('end',f"W/O {wo}: {', '.join(reasons)}\n")
        box.configure(state='disabled')
        buttons=ttk.Frame(self); buttons.grid(row=3,column=0,columnspan=2,pady=(0,14))
        ttk.Button(buttons,text='Back to Review',command=self.cancel).pack(side='left',padx=6)
        ttk.Button(buttons,text='Continue Current Review Flow',command=lambda:self.finish('continue')).pack(side='left',padx=6)
        ttk.Button(buttons,text='Ignore Problem Work Orders & Continue',command=lambda:self.finish('ignore'),
                   style='Danger.TButton').pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.rowconfigure(2,weight=1); self.columnconfigure(0,weight=1)
        self.update_idletasks(); self.geometry(f'+{parent.winfo_rootx()+65}+{parent.winfo_rooty()+60}')

    def finish(self,value):
        self.result=value; self.destroy()

    def cancel(self):
        self.result=None; self.destroy()


class App(base.App):
    def build_ui(self):
        super().build_ui()
        controls=self.analyze_button.master
        update_button=None
        for child in controls.winfo_children():
            try:
                if child.cget('text')=='2. Update Master':
                    update_button=child; break
            except Exception:
                pass
        self.discard_workorders_button=ttk.Button(
            controls,text='Discard Work Order(s)',command=self.discard_work_orders)
        pack_args={'side':'left','padx':8}
        if update_button is not None: pack_args['before']=update_button
        self.discard_workorders_button.pack(**pack_args)

    def _work_order_choices(self):
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
        problems={}
        def add(wo,reason):
            wo=str(wo or '').strip()
            if not wo or wo=='UNKNOWN': return
            bucket=problems.setdefault(wo,[])
            if reason not in bucket: bucket.append(reason)
        row_counts={}
        for record in self.records:
            if base.record_needs_review(record):
                wo=str(record.get('wo') or '').strip(); row_counts[wo]=row_counts.get(wo,0)+1
        for wo,count in row_counts.items(): add(wo,f'{count} extracted row(s) need review')
        ticket_counts={}
        for ticket in self.trouble_tickets:
            if base.trouble_ticket_status(ticket).startswith('Review'):
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
        except Exception:
            pass
        self._schedule_total_outlines()

    def discard_work_orders(self):
        if getattr(self,'_analysis_running',False):
            messagebox.showinfo('Analysis In Progress',
                                'Finish or cancel the current analysis before discarding a work order.',parent=self)
            return
        choices=self._work_order_choices()
        if not choices:
            messagebox.showinfo('Discard Work Order(s)','There are no analyzed work orders to discard.',parent=self); return
        dlg=DiscardWorkOrdersDialog(self,choices,self._selected_work_order()); self.wait_window(dlg)
        if not dlg.result: return
        selected={str(wo).strip() for wo in dlg.result if str(wo).strip()}
        selected_items=[item for item in choices if item['wo'] in selected]
        details='\n'.join(
            f"W/O {item['wo']}: {item['rows']} extracted row(s), {item['tickets']} trouble ticket(s)"
            for item in selected_items)
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

    def update_master(self):
        if not self.records and not self.trouble_tickets:
            messagebox.showwarning('Nothing to update','Analyze a PDF first.'); return
        if not self.resolve_problem_work_orders_for_update(): return
        if not self.records and not self.trouble_tickets:
            messagebox.showwarning('Nothing to update','No work orders remain in the pending update.'); return
        return super().update_master()


# The core analyzer resolves ConfirmDialog through its own module globals.
base.ConfirmDialog=EnhancedConfirmDialog


if __name__=='__main__':
    base.configure_windows_identity()
    App().mainloop()
