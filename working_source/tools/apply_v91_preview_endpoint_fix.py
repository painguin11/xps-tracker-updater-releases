from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v91_new_asset_preview_and_endpoint_recovery.py')
s=SOURCE.read_text(encoding='utf-8')

old_endpoint='''def _endpoint_digit_tokens(cell_img):
    """Return numeric strings actually OCR-observed in one endpoint cell."""
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    out=[]
    for value in _ocr_digits(cell_img,False,fast_plain=False):
        token=re.sub(r'\\D','',str(value or ''))
        if token and token not in out:
            out.append(token)
    return out
'''
new_endpoint='''def _endpoint_digit_tokens(cell_img):
    """Return numeric strings actually OCR-observed in one endpoint cell.

    The normal endpoint OCR keeps the complete printed ID.  This fallback is used
    only after pair matching has already failed, so add an independent borderless,
    padded digit read as well.  It repairs cases where a vertical table rule makes
    a cell such as DN-1912 unreadable as a full ID while its printed numeric body is
    still visible.  The caller still requires both OCR-observed endpoint numbers to
    identify exactly one existing master pipe; no endpoint is invented from master
    data and legitimate non-master pairs remain review-only.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return []
    out=[]
    def add(value):
        token=re.sub(r'\\D','',str(value or ''))
        if token and token not in out:
            out.append(token)
    for value in _ocr_digits(cell_img,False,fast_plain=False):
        add(value)

    # Give an unresolved grid cell a genuinely independent view.  Cropping the
    # edge rules and adding white padding changes both the framing and OCR cache
    # key, so a stale/failed tight-cell result cannot suppress this recovery pass.
    h,w=cell_img.shape[:2]
    trim_x=max(2,int(round(w*.035))); trim_y=max(1,int(round(h*.08)))
    inner=(cell_img[trim_y:h-trim_y,trim_x:w-trim_x]
           if w>trim_x*2+8 and h>trim_y*2+6 else cell_img)
    if getattr(inner,'size',0):
        gray=cv2.cvtColor(inner,cv2.COLOR_RGB2GRAY)
        gray=cv2.resize(gray,None,fx=3.4,fy=3.4,interpolation=cv2.INTER_CUBIC)
        variants=(gray,cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1])
        for image in variants:
            padded=cv2.copyMakeBorder(image,18,18,28,28,cv2.BORDER_CONSTANT,value=255)
            for psm in (7,13):
                text=cached_ocr_string(
                    padded,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789'
                )
                for token in re.findall(r'\\d+',str(text or '')):
                    add(token)
    return out
'''
assert old_endpoint in s, 'endpoint digit helper changed unexpectedly'
s=s.replace(old_endpoint,new_endpoint,1)

marker='''\n\nclass UnmatchedAssetDecisionDialog(tk.Toplevel):\n'''
assert marker in s, 'unmatched dialog marker not found'
new_dialog=r'''

class NewAssetApprovalDialog(tk.Toplevel):
    """Preserve the immediate suffixed-new-asset Yes/No flow with PDF ID crops."""
    def __init__(self,parent,record,base_info):
        super().__init__(parent); self.result=False; self.crop_photos=[]
        apply_app_icon(self)
        is_manhole=record.get('kind')=='Manhole'
        label='Manhole' if is_manhole else 'Pipe'
        noun='manhole' if is_manhole else 'pipe'
        self.title(f'New {label} Detected'); self.transient(parent); self.grab_set(); self.resizable(False,False)
        scanned=(record.get('asset') or record.get('display_asset') or '') if is_manhole else f"{record.get('up','')} -> {record.get('down','')}"
        text=(f"{record.get('status','NEW '+label.upper())}\n\nScanned asset:\n{scanned}\n\n"
              f"Existing base {noun}:\n{base_info.get('base_asset','')}\n\n"
              f"Add the new {noun} directly below its base row in the master?\n\n"
              'The inserted master row will be highlighted green.')
        ttk.Label(self,text=text,justify='left',wraplength=720).grid(row=0,column=0,columnspan=3,padx=16,pady=(16,8),sticky='w')

        previews=dict(record.get('_field_previews') or {})
        preview_pages=dict(record.get('_field_preview_pages') or {})
        preview_frame=ttk.LabelFrame(self,text='PDF ID verification',padding=10)
        preview_frame.grid(row=1,column=0,columnspan=3,padx=16,pady=(0,12),sticky='ew')
        preview_specs=([('Manhole ID',record.get('asset') or '', 'asset')] if is_manhole else
                       [('Upstream ID',record.get('up') or '', 'upstream'),
                        ('Downstream ID',record.get('down') or '', 'downstream')])
        for column,(field_label,value,key) in enumerate(preview_specs):
            block=ttk.Frame(preview_frame); block.grid(row=0,column=column,padx=8,sticky='nw')
            ttk.Label(block,text=f'{field_label}: {value}',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,4))
            crop=previews.get(key)
            pages=list(preview_pages.get(key) or [])
            if not pages:
                pages=list(record.get('source_pages') or [])
                if not pages and record.get('source_page') is not None: pages=[record.get('source_page')]
            if crop is None or not getattr(crop,'size',0):
                ttk.Label(block,text=_preview_unavailable_text(pages),foreground='#8A5200').pack(anchor='w')
                continue
            try:
                image=Image.fromarray(crop)
                if image.width<260:
                    scale=min(3.0,260.0/max(1,image.width))
                    image=image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.LANCZOS)
                image.thumbnail((360,95),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(image,master=self); self.crop_photos.append(photo)
                page=pages[0] if pages else record.get('source_page','?')
                ttk.Label(block,text=f'PDF page {page}:').pack(anchor='w')
                ttk.Label(block,image=photo).pack(anchor='w',pady=(2,0))
            except Exception:
                ttk.Label(block,text=_preview_unavailable_text(pages),foreground='#8A5200').pack(anchor='w')
        for column in range(len(preview_specs)): preview_frame.columnconfigure(column,weight=1)

        buttons=ttk.Frame(self); buttons.grid(row=2,column=0,columnspan=3,pady=(0,14))
        ttk.Button(buttons,text='Yes',command=lambda:self.finish(True),style='Primary.TButton').pack(side='left',padx=6)
        ttk.Button(buttons,text='No',command=lambda:self.finish(False)).pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',lambda:self.finish(False))
        self.update_idletasks(); self.geometry(f'+{parent.winfo_rootx()+70}+{parent.winfo_rooty()+55}')
    def finish(self,value): self.result=bool(value); self.destroy()
'''
s=s.replace(marker,new_dialog+marker,1)

old_approval='''                rec['new_asset_approved']=messagebox.askyesno(
                    f'New {label.title()} Detected',
                    f"{rec['status']}\\n\\nScanned asset:\\n{rec['display_asset']}\\n\\n"
                    f"Existing base {label}:\\n{base_info['base_asset']}\\n\\n"
                    f"Add the new {label} directly below its base row in the master?\\n\\n"
                    'The inserted master row will be highlighted green.')
'''
new_approval='''                dlg=NewAssetApprovalDialog(self,rec,base_info); self.wait_window(dlg)
                rec['new_asset_approved']=bool(dlg.result)
'''
assert old_approval in s, 'legacy new-asset askyesno block changed unexpectedly'
s=s.replace(old_approval,new_approval,1)
SOURCE.write_text(s,encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast, re
import numpy as np
import cv2

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')

# Suffixed NEW PIPE / NEW MANHOLE approvals must use a crop-capable Yes/No dialog,
# not the old messagebox path.
start=s.index('class NewAssetApprovalDialog')
end=s.index('\n\nclass UnmatchedAssetDecisionDialog',start)
d=s[start:end]
for required in ('PDF ID verification',"'upstream'","'downstream'","'asset'",
                 'ImageTk.PhotoImage(image,master=self)',"text='Yes'","text='No'"):
    assert required in d, required
commit_start=s.index('    def commit_extracted_record')
commit_end=s.index('\n    def analyze',commit_start)
commit=s[commit_start:commit_end]
assert 'NewAssetApprovalDialog(self,rec,base_info)' in commit
assert "messagebox.askyesno(\n                    f'New {label.title()} Detected'" not in commit

# Simulate the Windows failure mode: normal digit OCR returns nothing, but the
# independent padded endpoint view sees the printed numeric body.  No real OCR or
# customer fixture is required for this deterministic fallback-unit check.
tree=ast.parse(s)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_endpoint_digit_tokens')
ns={'cv2':cv2,'re':re,'_ocr_digits':lambda *_a,**_k:[],
    'cached_ocr_string':lambda *_a,**_k:'1912'}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
cell=np.full((28,90,3),255,dtype=np.uint8)
assert ns['_endpoint_digit_tokens'](cell)==['1912']

# The downstream recovery remains conservative: both OCR-observed numeric bodies
# must identify exactly one existing directional master pair.
for name in ('_asset_body_digits','_digit_token_matches_asset_body','_resolve_pipe_pair_from_endpoint_digits'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
reads=iter((['1911'],['1912']))
ns['_endpoint_digit_tokens']=lambda _cell: next(reads)
master={'pipe_items':[
    {'row':109,'up':'DN-1911','down':'DN-1912','up_key':'DN1911','down_key':'DN1912'},
    {'row':110,'up':'DN-1913','down':'DN-1911','up_key':'DN1913','down_key':'DN1911'},
]}
resolved=ns['_resolve_pipe_pair_from_endpoint_digits'](cell,cell,master)
assert resolved and resolved['up']=='DN-1911' and resolved['down']=='DN-1912', resolved

# A legitimate pair that simply does not exist in the master is still unresolved.
reads=iter((['1698'],['1697']))
ns['_endpoint_digit_tokens']=lambda _cell: next(reads)
assert ns['_resolve_pipe_pair_from_endpoint_digits'](cell,cell,master) is None
print('v91 new-asset preview + conservative endpoint recovery regression passed')
''',encoding='utf-8')
print('Applied v91 preview/endpoint patch and wrote regression.')
