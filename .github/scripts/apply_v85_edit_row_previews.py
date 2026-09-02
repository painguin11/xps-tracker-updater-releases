from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v85_edit_row_previews.py')
src=APP.read_text(encoding='utf-8')

# Helper for the exact user-facing fallback wording.
anchor="""class ConfirmDialog(tk.Toplevel):\n"""
helper="""def _preview_unavailable_text(pages):\n    \"\"\"Describe where to verify a field when its image crop is unavailable.\"\"\"\n    if isinstance(pages,(list,tuple,set)):\n        values=[str(page).strip() for page in pages if str(page).strip()]\n    else:\n        raw=str(pages or '').strip()\n        values=[part.strip() for part in raw.split(',') if part.strip()]\n    values=list(dict.fromkeys(values))\n    if len(values)>1:\n        return 'Preview unavailable — check PDF pages ' + ', '.join(values) + '.'\n    return 'Preview unavailable — check PDF page ' + (values[0] if values else 'unknown') + '.'\n\n\nclass ConfirmDialog(tk.Toplevel):\n"""
if src.count(anchor)!=1:
    raise SystemExit('ConfirmDialog anchor not found exactly once')
src=src.replace(anchor,helper)

# Preserve the physical page alongside each split-pipe length crop.
old="""def _length_part_snapshot(record):\n    \"\"\"Retain one physical PDF row so split-pipe rereads stay part-by-part.\"\"\"\n    return {'value':record.get('video_length'),\n            'cell':record.get('_length_value_cell'),\n            'expanded':record.get('_length_expanded_cell')}\n"""
new="""def _length_part_snapshot(record):\n    \"\"\"Retain one physical PDF row so split-pipe rereads/previews stay part-by-part.\"\"\"\n    return {'value':record.get('video_length'),\n            'cell':record.get('_length_value_cell'),\n            'expanded':record.get('_length_expanded_cell'),\n            'page':record.get('source_page')}\n"""
if src.count(old)!=1:
    raise SystemExit('length part snapshot block not found exactly once')
src=src.replace(old,new)

# Pair-table rows retain the exact value/date cells used by the parser.
old="""        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe','asset':asset,\n             'up':up,'down':down,'video_length':value,'row_date':d,'status':status}\n        rec['_length_value_cell']=value_cell.copy() if getattr(value_cell,'size',0) else None\n"""
new="""        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe','asset':asset,\n             'up':up,'down':down,'video_length':value,'row_date':d,'status':status}\n        date_cell=cut(date_box)\n        rec['_field_previews']={\n            'activity_value':value_cell.copy() if getattr(value_cell,'size',0) else None,\n            'date':date_cell.copy() if getattr(date_cell,'size',0) else None,\n        }\n        rec['_length_value_cell']=value_cell.copy() if getattr(value_cell,'size',0) else None\n"""
if src.count(old)!=1:
    raise SystemExit('pair-row preview block not found exactly once')
src=src.replace(old,new)

# Manhole token rows retain a row-level crop of the printed date area.
old="""            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                 'video_length':None,'row_date':row_date,'status':status}\n            if item is None: rec['skip_update']=True\n"""
new="""            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n                 'video_length':None,'row_date':row_date,'status':status}\n            preview_half=max(8,int(round(h*.018)))\n            date_preview=img[max(0,int(yc)-preview_half):min(h,int(yc)+preview_half),int(w*.60):w]\n            rec['_field_previews']={'date':date_preview.copy() if getattr(date_preview,'size',0) else None}\n            if item is None: rec['skip_update']=True\n"""
if src.count(old)!=1:
    raise SystemExit('manhole token preview block not found exactly once')
src=src.replace(old,new)

# Manhole grid rows already have the exact date cell available.
old="""        date_img=img[y1:y2,int(left+.74*tw):right]\n        rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n             'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n"""
new="""        date_img=img[y1:y2,int(left+.74*tw):right]\n        rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',\n             'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}\n        rec['_field_previews']={'date':date_img.copy() if getattr(date_img,'size',0) else None}\n"""
if src.count(old)!=1:
    raise SystemExit('manhole grid preview block not found exactly once')
src=src.replace(old,new)

# Carry the same work-order crops shown in Confirm Work Order into later row edits.
old="""                dlg=ConfirmDialog(self,item['guesses']); self.wait_window(dlg)\n                if dlg.result is None:\n                    self.status.set('Analysis cancelled.'); return\n                confirmed_by_page[item['index']]=dlg.result\n                self.groups.append(dlg.result.copy())\n"""
new="""                dlg=ConfirmDialog(self,item['guesses']); self.wait_window(dlg)\n                if dlg.result is None:\n                    self.status.set('Analysis cancelled.'); return\n                guesses=item['guesses']\n                def confirmed_preview(key):\n                    crop=guesses.get(key)\n                    if crop is None: crop=guesses.get('preview')\n                    return crop.copy() if getattr(crop,'size',0) else None\n                dlg.result['_field_previews']={\n                    'wo':confirmed_preview('wo_preview'),\n                    'truck':confirmed_preview('truck_preview'),\n                    'operator':confirmed_preview('operator_preview'),\n                }\n                dlg.result['_field_preview_pages']={\n                    'wo':[item['index']+1],'truck':[item['index']+1],'operator':[item['index']+1]}\n                dlg.result['_workorder_page']=item['index']+1\n                confirmed_by_page[item['index']]=dlg.result\n                # Persistent confirmation history needs values, not large image arrays.\n                self.groups.append({key:value for key,value in dlg.result.items() if not key.startswith('_')})\n"""
if src.count(old)!=1:
    raise SystemExit('work-order confirmation preview block not found exactly once')
src=src.replace(old,new)

# Merge page-specific activity/date crops with the confirmed work-order crops.
old="""        rec_date=rec.pop('row_date',None) or use_date\n        rec.update({'wo':current_wo['wo'],'truck':current_wo['truck'],\n                    'operator':current_wo['operator'],'date':rec_date})\n        if rec['kind'] in ('Pipe','Cleaning'):\n"""
new="""        rec_date=rec.pop('row_date',None) or use_date\n        rec.update({'wo':current_wo['wo'],'truck':current_wo['truck'],\n                    'operator':current_wo['operator'],'date':rec_date})\n        field_previews=dict(rec.get('_field_previews') or {})\n        field_pages={key:list(value) if isinstance(value,(list,tuple)) else [value]\n                     for key,value in (rec.get('_field_preview_pages') or {}).items()}\n        for key in ('activity_value','date'):\n            field_pages.setdefault(key,[page_number])\n        wo_previews=current_wo.get('_field_previews') or {}\n        wo_pages=current_wo.get('_field_preview_pages') or {}\n        for key in ('wo','truck','operator'):\n            if key in wo_previews: field_previews[key]=wo_previews.get(key)\n            field_pages[key]=list(wo_pages.get(key) or [current_wo.get('_workorder_page') or page_number])\n        rec['_field_previews']=field_previews\n        rec['_field_preview_pages']=field_pages\n        if rec['kind'] in ('Pipe','Cleaning'):\n"""
if src.count(old)!=1:
    raise SystemExit('record commit preview block not found exactly once')
src=src.replace(old,new)

# Replace the plain edit form with field-specific PDF previews and page fallbacks.
old="""        win=tk.Toplevel(self); apply_app_icon(win); win.title('Edit extracted row'); win.transient(self); win.grab_set()\n        fields=['Activity Value','Date','W/O','Truck','Operator']; vars={}\n        values=[('' if r['video_length'] is None else str(r['video_length'])),fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n        for n,(lab,val) in enumerate(zip(fields,values)):\n            ttk.Label(win,text=lab+':').grid(row=n,column=0,padx=8,pady=6,sticky='e'); v=tk.StringVar(value=val); vars[lab]=v; ttk.Entry(win,textvariable=v,width=30).grid(row=n,column=1,padx=8,pady=6)\n        def save():\n"""
new="""        win=tk.Toplevel(self); apply_app_icon(win); win.title('Edit extracted row'); win.transient(self); win.grab_set()\n        win.crop_photos=[]\n        fields=[('Activity Value','activity_value'),('Date','date'),('W/O','wo'),('Truck','truck'),('Operator','operator')]; vars={}\n        values=[('' if r['video_length'] is None else str(r['video_length'])),fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n        field_previews=dict(r.get('_field_previews') or {})\n        field_pages=dict(r.get('_field_preview_pages') or {})\n\n        def preview_items(key):\n            crops=[]; pages=[]\n            if key=='activity_value' and int(r.get('part_count') or 0)>1:\n                for part in r.get('_length_part_reads',[]) or []:\n                    crop=part.get('cell')\n                    if crop is None: crop=part.get('expanded')\n                    if getattr(crop,'size',0):\n                        crops.append(crop); pages.append(part.get('page'))\n            if not crops:\n                raw=field_previews.get(key)\n                raw_items=list(raw) if isinstance(raw,(list,tuple)) else [raw]\n                crops=[crop for crop in raw_items if getattr(crop,'size',0)]\n                pages=list(field_pages.get(key) or [])\n            if not pages:\n                pages=list(r.get('source_pages') or [])\n                if not pages and r.get('source_page') is not None: pages=[r.get('source_page')]\n            return crops,pages\n\n        def add_preview(row,key):\n            holder=ttk.Frame(win); holder.grid(row=row,column=2,padx=(6,12),pady=4,sticky='w')\n            crops,pages=preview_items(key)\n            if not crops:\n                ttk.Label(holder,text=_preview_unavailable_text(pages),foreground='#8A5200').pack(anchor='w')\n                return\n            for crop_index,crop in enumerate(crops):\n                try:\n                    image=Image.fromarray(crop)\n                    if image.width<260:\n                        scale=min(3.0,260.0/max(1,image.width))\n                        image=image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.LANCZOS)\n                    image.thumbnail((400,82),Image.Resampling.LANCZOS)\n                    photo=ImageTk.PhotoImage(image,master=win); win.crop_photos.append(photo)\n                    line=ttk.Frame(holder); line.pack(anchor='w',pady=1)\n                    page=pages[crop_index] if crop_index<len(pages) else (pages[0] if pages else r.get('source_page','?'))\n                    ttk.Label(line,text=f'PDF page {page}:',width=12).pack(side='left',padx=(0,5))\n                    ttk.Label(line,image=photo).pack(side='left')\n                except Exception:\n                    ttk.Label(holder,text=_preview_unavailable_text(pages),foreground='#8A5200').pack(anchor='w')\n                    break\n\n        ttk.Label(win,text=r.get('display_asset') or r.get('asset',''),font=('Segoe UI',11,'bold')).grid(\n            row=0,column=0,columnspan=3,padx=12,pady=(12,6),sticky='w')\n        for n,((lab,key),val) in enumerate(zip(fields,values),1):\n            ttk.Label(win,text=lab+':').grid(row=n,column=0,padx=8,pady=6,sticky='e')\n            v=tk.StringVar(value=val); vars[lab]=v\n            ttk.Entry(win,textvariable=v,width=30).grid(row=n,column=1,padx=8,pady=6,sticky='w')\n            add_preview(n,key)\n        ttk.Label(win,text='Compare each value with its PDF image before saving.',foreground='#8A5200').grid(\n            row=len(fields)+1,column=0,columnspan=3,padx=12,pady=(4,2),sticky='w')\n        win.columnconfigure(2,weight=1)\n        def save():\n"""
if src.count(old)!=1:
    raise SystemExit('edit form block not found exactly once')
src=src.replace(old,new)

# The Save button moves down one row because the dialog now has a title and hint.
old="""        ttk.Button(win,text='Save',command=save,style='Primary.TButton').grid(row=len(fields),column=0,columnspan=2,pady=10)\n"""
new="""        ttk.Button(win,text='Save',command=save,style='Primary.TButton').grid(row=len(fields)+2,column=0,columnspan=3,pady=(6,12))\n        win.update_idletasks(); win.geometry(f'+{self.winfo_rootx()+70}+{self.winfo_rooty()+60}')\n"""
if src.count(old)!=1:
    raise SystemExit('edit save-button block not found exactly once')
src=src.replace(old,new)

APP.write_text(src,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "'activity_value':value_cell.copy()" in src
assert "rec['_field_previews']={'date':date_img.copy()" in src
assert "dlg.result['_field_previews']" in src
assert "'wo':confirmed_preview('wo_preview')" in src
assert "'truck':confirmed_preview('truck_preview')" in src
assert "'operator':confirmed_preview('operator_preview')" in src
assert "rec['_field_preview_pages']=field_pages" in src
assert "'page':record.get('source_page')" in src
assert "if key=='activity_value' and int(r.get('part_count') or 0)>1:" in src
assert "Compare each value with its PDF image before saving." in src

# Execute the fallback-label helper without importing Windows-only dependencies.
tree=ast.parse(src)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_preview_unavailable_text')
ns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<preview-fallback>','exec'),ns)
label=ns['_preview_unavailable_text']
assert label([4])=='Preview unavailable — check PDF page 4.'
assert label([2,3])=='Preview unavailable — check PDF pages 2, 3.'
assert label('10')=='Preview unavailable — check PDF page 10.'

# Confirm the edit form requests previews for every editable field.
edit=src[src.index('    def edit_selected(self):'):src.index('    def edit_trouble_ticket(self,index):')]
for key in ('activity_value','date','wo','truck','operator'):
    assert repr(key) in edit
assert '_preview_unavailable_text(pages)' in edit

print('v85 edit-row PDF preview regression passed.')
''',encoding='utf-8')

print('Applied v85 edit-row PDF preview patch.')
