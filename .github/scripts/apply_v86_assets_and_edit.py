from pathlib import Path
p=Path('working_source/app/reno_scan_updater.py')
s=p.read_text()

anchor="""def _ocr_known_r2_candidates(cell_img, known_items, asset_format=None):\n"""
helper=r'''def _batch_pair_endpoint_candidates(img,bands,table,box,asset_format=None):
    """Read an endpoint column as one image and map complete IDs back to row bands.

    Grid strokes can damage the first one or two characters when each cell is OCRed
    alone. The same printed ID is often clean when Tesseract sees the whole aligned
    column. This is supplemental evidence only: candidates still must resolve through
    the normal master pair matcher/new-asset safeguards.
    """
    if img is None or not bands or not table or not box:
        return {}
    left,right=table; tw=max(1,right-left); h,w=img.shape[:2]
    x1=max(0,int(left+box[0]*tw)); x2=min(w,int(left+box[1]*tw))
    y_top=max(0,int(bands[0][0])); y_bottom=min(h,int(bands[-1][1]))
    if x2<=x1 or y_bottom<=y_top:
        return {}
    crop=img[y_top:y_bottom,x1:x2]
    gray=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
    scale=3.0
    gray=cv2.resize(gray,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
    out={}
    for psm in (6,11):
        try:
            data=pytesseract.image_to_data(gray,config=f'--psm {psm}',output_type=pytesseract.Output.DICT)
        except Exception:
            continue
        for i,raw in enumerate(data.get('text',[])):
            text=str(raw or '').strip()
            if not text: continue
            tokens=_printed_asset_tokens(text,asset_format)
            if not tokens: continue
            try:
                yc=y_top+(float(data['top'][i])+float(data['height'][i])/2.0)/scale
            except Exception:
                continue
            band_index=next((bi for bi,(a,b) in enumerate(bands) if a<=yc<=b),None)
            if band_index is None: continue
            values=out.setdefault(band_index,[])
            for token in tokens:
                if token not in values: values.append(token)
    return out


def _ocr_known_r2_candidates(cell_img, known_items, asset_format=None):
'''
if s.count(anchor)!=1: raise SystemExit('batch helper anchor')
s=s.replace(anchor,helper)

old="""    for endpoint_key,manhole_item in master_index.get('manholes',{}).items():\n        endpoint_items[asset_key(endpoint_key)]=manhole_item.get('asset') or str(endpoint_key)\n    rows=[]; seen=set()\n"""
new="""    for endpoint_key,manhole_item in master_index.get('manholes',{}).items():\n        endpoint_items[asset_key(endpoint_key)]=manhole_item.get('asset') or str(endpoint_key)\n    batch_up_endpoints=_batch_pair_endpoint_candidates(img,bands,table,up_box,asset_format)\n    batch_dn_endpoints=_batch_pair_endpoint_candidates(img,bands,table,dn_box,asset_format)\n    rows=[]; seen=set()\n"""
if s.count(old)!=1: raise SystemExit('batch maps anchor')
s=s.replace(old,new)

old="""        up_obs=read_id(up_box,True); dn_obs=read_id(dn_box,True)\n        match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n"""
new="""        up_obs=read_id(up_box,True); dn_obs=read_id(dn_box,True)\n        up_obs=list(dict.fromkeys(up_obs+list(batch_up_endpoints.get(band_index,[]))))\n        dn_obs=list(dict.fromkeys(dn_obs+list(batch_dn_endpoints.get(band_index,[]))))\n        match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)\n"""
if s.count(old)!=1: raise SystemExit('row batch evidence anchor')
s=s.replace(old,new)

old="""        rec['_field_previews']={\n            'activity_value':value_cell.copy() if getattr(value_cell,'size',0) else None,\n            'date':date_cell.copy() if getattr(date_cell,'size',0) else None,\n        }\n"""
new="""        up_preview=cut(up_box); dn_preview=cut(dn_box)\n        rec['_field_previews']={\n            'upstream':up_preview.copy() if getattr(up_preview,'size',0) else None,\n            'downstream':dn_preview.copy() if getattr(dn_preview,'size',0) else None,\n            'activity_value':value_cell.copy() if getattr(value_cell,'size',0) else None,\n            'date':date_cell.copy() if getattr(date_cell,'size',0) else None,\n        }\n"""
if s.count(old)!=1: raise SystemExit('pair preview anchor')
s=s.replace(old,new)

old="""            preview_half=max(8,int(round(h*.018)))\n            date_preview=img[max(0,int(yc)-preview_half):min(h,int(yc)+preview_half),int(w*.60):w]\n            rec['_field_previews']={'date':date_preview.copy() if getattr(date_preview,'size',0) else None}\n"""
new="""            preview_half=max(8,int(round(h*.018)))\n            asset_preview=img[max(0,int(yc)-preview_half):min(h,int(yc)+preview_half),0:int(w*.38)]\n            date_preview=img[max(0,int(yc)-preview_half):min(h,int(yc)+preview_half),int(w*.60):w]\n            rec['_field_previews']={\n                'asset':asset_preview.copy() if getattr(asset_preview,'size',0) else None,\n                'date':date_preview.copy() if getattr(date_preview,'size',0) else None}\n"""
if s.count(old)!=1: raise SystemExit('mh token preview anchor')
s=s.replace(old,new)

old="""        rec['_field_previews']={'date':date_img.copy() if getattr(date_img,'size',0) else None}\n"""
new="""        rec['_field_previews']={\n            'asset':id_img.copy() if getattr(id_img,'size',0) else None,\n            'date':date_img.copy() if getattr(date_img,'size',0) else None}\n"""
if s.count(old)!=1: raise SystemExit('mh grid preview anchor')
s=s.replace(old,new)

old="""        for key in ('activity_value','date'):\n            field_pages.setdefault(key,[page_number])\n"""
new="""        for key in ('upstream','downstream','asset','activity_value','date'):\n            field_pages.setdefault(key,[page_number])\n"""
if s.count(old)!=1: raise SystemExit('field pages anchor')
s=s.replace(old,new)

anchor="""def refresh_length_status(record):\n"""
helper=r'''def apply_manual_asset_edit(record,master_index,up=None,down=None,asset=None):
    """Apply an Edit Selected asset/node correction and immediately re-match it."""
    kind=record.get('kind')
    if kind in ('Pipe','Cleaning'):
        up=canonical_asset_id(up); down=canonical_asset_id(down)
        if not up or not down:
            raise ValueError('Upstream Node and Downstream Node are required.')
        match,status=_resolve_pipe_pair([up],[down],master_index)
        record['up']=up; record['down']=down
        if match:
            record['up']=match['up']; record['down']=match['down']; record['asset']=match.get('pipe_id','')
            record['master_length']=match.get('expected'); record['skip_update']=False; record['status']='Matched'
        else:
            record['asset']=''; record['master_length']=None; record['skip_update']=True; record['status']=status
        record['display_asset']=f"{record['up']} -> {record['down']}" + (f"  (pipe {record.get('asset')})" if record.get('asset') else '')
        record['display_asset_base']=record['display_asset']
        refresh_length_status(record)
        if not match: record['status']=status
        return bool(match)
    if kind=='Manhole':
        asset=canonical_asset_id(asset)
        if not asset: raise ValueError('Asset is required.')
        item,status=_resolve_full_asset([asset],master_index.get('manholes',{}))
        record['asset']=item.get('asset') if item else asset
        record['asset_key']=item.get('asset_key') if item else asset_key(asset)
        record['display_asset']=record['asset']; record['display_asset_base']=record['asset']
        record['skip_update']=not bool(item); record['status']='Matched' if item else status
        return bool(item)
    return False


def refresh_length_status(record):
'''
if s.count(anchor)!=1: raise SystemExit('manual edit helper anchor')
s=s.replace(anchor,helper)

old="""        fields=[('Activity Value','activity_value'),('Date','date'),('W/O','wo'),('Truck','truck'),('Operator','operator')]; vars={}\n        values=[('' if r['video_length'] is None else str(r['video_length'])),fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n"""
new="""        if r.get('kind') in ('Pipe','Cleaning'):\n            fields=[('Upstream Node','upstream'),('Downstream Node','downstream'),('Activity Value','activity_value'),\n                    ('Date','date'),('W/O','wo'),('Truck','truck'),('Operator','operator')]\n            values=[r.get('up',''),r.get('down',''),('' if r['video_length'] is None else str(r['video_length'])),\n                    fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n        else:\n            fields=[('Asset','asset'),('Date','date'),('W/O','wo'),('Truck','truck'),('Operator','operator')]\n            values=[r.get('asset',''),fmt_date(r['date']),r['wo'],r['truck'],r['operator']]\n        vars={}\n"""
if s.count(old)!=1: raise SystemExit('edit fields anchor')
s=s.replace(old,new)

old="""                old_length=r.get('video_length')\n                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())\n                if r.get('kind') in ('Pipe','Cleaning') and r.get('video_length') is not None and not _valid_row_length_value(r.get('video_length')):\n                    raise ValueError(f'Individual activity length must be greater than 0 and no more than {MAX_ROW_LENGTH:g} ft.')\n                if r.get('kind')=='Cleaning' and old_length!=r.get('video_length'):\n                    r['_length_user_edited']=True\n                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()\n"""
new="""                old_length=r.get('video_length')\n                if r.get('kind') in ('Pipe','Cleaning'):\n                    r['video_length']=None if not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())\n                    if r.get('video_length') is not None and not _valid_row_length_value(r.get('video_length')):\n                        raise ValueError(f'Individual activity length must be greater than 0 and no more than {MAX_ROW_LENGTH:g} ft.')\n                    apply_manual_asset_edit(r,self.master_index,vars['Upstream Node'].get(),vars['Downstream Node'].get())\n                    if old_length!=r.get('video_length'): r['_length_user_edited']=True\n                else:\n                    r['video_length']=None\n                    apply_manual_asset_edit(r,self.master_index,asset=vars['Asset'].get())\n                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()\n"""
if s.count(old)!=1: raise SystemExit('edit save anchor')
s=s.replace(old,new)

p.write_text(s)
print('patched v86 assets/edit')
