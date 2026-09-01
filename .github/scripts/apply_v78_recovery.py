from pathlib import Path
import re
import subprocess

APP = Path('working_source/app/reno_scan_updater.py')
UPDATER = Path('working_source/app/xps_update.py')
README = Path('working_source/app/README_XPS_Tracker_Updater.txt')
V75_TEST = Path('working_source/tests/regression_v75_811_ocr.py')
LENGTH_TEST = Path('working_source/tests/regression_length_totals.py')
GUARD = Path('working_source/tests/regression_v78_rollback.py')


def git_show(path: str) -> str:
    return subprocess.check_output(
        ['git', 'show', f'origin/v75-work:{path}'], text=True, encoding='utf-8'
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'{label}: expected source block not found; refusing broad edit')
    return text.replace(old, new, 1)


# Start from the last cleaning OCR implementation before total-driven reselection
# (v76) and simple-first OCR (v77) were introduced.
text = git_show('working_source/app/reno_scan_updater.py')
LENGTH_TEST.write_text(git_show('working_source/tests/regression_length_totals.py'), encoding='utf-8')
V75_TEST.write_text(git_show('working_source/tests/regression_v75_811_ocr.py'), encoding='utf-8')

# Keep only the useful v76 saved-layout improvement. A previously confirmed
# layout should be accepted without immediately showing the same dialog again.
old = """                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                            dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                            if dlg.result is None:
                                self.status.set('Analysis cancelled.'); return
                            confirmed_layouts[fingerprint]=dlg.result
                            apply_confirmed_layout(layout,dlg.result)
                            save_layout_profile(fingerprint,layout,dlg.result)
"""
new = """                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                                if dlg.result is None:
                                    self.status.set('Analysis cancelled.'); return
                                confirmed_layouts[fingerprint]=dlg.result
                                apply_confirmed_layout(layout,dlg.result)
                                save_layout_profile(fingerprint,layout,dlg.result)
"""
text = replace_once(text, old, new, 'saved-layout confirmation gate')

# Read cleaning lengths as one aligned column instead of asking Tesseract to
# recognize each tiny ruled cell in isolation. Each detected row becomes a
# separate padded line in a synthetic image. Only the table-edge pixels are
# removed; the printed digits themselves are not modified or inferred.
helper_marker = "def _choose_printed_total(cands):\n"
if helper_marker not in text:
    raise SystemExit('batch cleaning helper insertion marker not found')
helper = r'''def _batch_cleaning_length_candidates(img,bands,table,value_box,skip_band_index=None):
    """Read the printed Wheel Walk column in one OCR pass and map values to bands.

    Small isolated numeric cells are unusually sensitive to their top/right grid
    rules.  Here every normal-height value cell is trimmed just inside those rules,
    padded, stacked vertically, and OCRed as a column.  Results are mapped back by
    OCR y-position.  Missing rows simply fall back to the established per-cell OCR.
    No master length or printed total participates in this read.
    """
    if img is None or not bands or not table or not value_box:
        return {}
    left,right=table; h,w=img.shape[:2]; tw=max(1,right-left)
    heights=[max(1,b-a) for a,b in bands]
    typical=float(np.median(heights)) if heights else 1.0
    tiles=[]; tile_indices=[]
    x1=max(0,int(left+value_box[0]*tw)); x2=min(w,int(left+value_box[1]*tw))
    if x2-x1<8:
        return {}
    for band_index,(y1,y2) in enumerate(bands):
        if skip_band_index is not None and band_index==skip_band_index:
            continue
        band_h=max(1,y2-y1)
        # Tall bands are normally wrapped headers. If a real row is unusually
        # tall, the ordinary per-cell fallback below still handles it safely.
        if band_h>typical*1.45:
            continue
        cell=img[max(0,int(y1)):min(h,int(y2)),x1:x2].copy()
        if cell.size==0:
            continue
        ch,cw=cell.shape[:2]
        top=max(1,int(round(ch*.20)))
        bottom=max(1,int(round(ch*.04)))
        left_pad=max(0,int(round(cw*.02)))
        sample=cell[top:max(top+2,ch-bottom),left_pad:].copy()
        if sample.size==0:
            continue
        # Keep the right-aligned final digit intact. Erase only the final ~1.5%
        # containing the vertical grid stroke instead of cropping the right side.
        edge=max(1,int(round(sample.shape[1]*.015)))
        sample[:,-edge:]=255
        gray=cv2.cvtColor(sample,cv2.COLOR_RGB2GRAY)
        gray=cv2.resize(gray,None,fx=3.0,fy=3.0,interpolation=cv2.INTER_CUBIC)
        gray=cv2.copyMakeBorder(gray,12,12,20,20,cv2.BORDER_CONSTANT,value=255)
        tiles.append(gray); tile_indices.append(band_index)
    if not tiles:
        return {}
    width=max(tile.shape[1] for tile in tiles)
    padded=[]; spans=[]; cursor=0
    for band_index,tile in zip(tile_indices,tiles):
        if tile.shape[1]<width:
            tile=cv2.copyMakeBorder(tile,0,0,0,width-tile.shape[1],cv2.BORDER_CONSTANT,value=255)
        padded.append(tile)
        spans.append((band_index,cursor,cursor+tile.shape[0]))
        cursor+=tile.shape[0]
    stack=np.vstack(padded)
    try:
        data=pytesseract.image_to_data(
            stack,config='--psm 6 -c tessedit_char_whitelist=0123456789.',
            output_type=pytesseract.Output.DICT)
    except Exception:
        return {}
    found={}
    for i,raw in enumerate(data.get('text',[])):
        raw=str(raw or '').strip().replace(',','')
        values=re.findall(r'\d+(?:\.\d+)?',raw)
        if not values:
            continue
        try:
            yc=float(data['top'][i])+float(data['height'][i])/2.0
        except Exception:
            continue
        band_index=min(spans,key=lambda span:abs(yc-(span[1]+span[2])/2.0))[0]
        bucket=found.setdefault(band_index,[])
        for value in values:
            try:
                numeric=float(value)
                if 0<numeric<5000:
                    bucket.append(numeric)
            except Exception:
                pass
    return found


'''
text = text.replace(helper_marker, helper + helper_marker, 1)

# Build the column OCR result once per cleaning page, after the independently
# detected printed-total band is known so that total can never become a row value.
old = """    total_band_index=printed_total_info.get('band_index')

    endpoint_items={}
"""
new = """    total_band_index=printed_total_info.get('band_index')
    batch_cleaning_values=(
        _batch_cleaning_length_candidates(img,bands,table,val_box,total_band_index)
        if kind=='cleaning' else {})

    endpoint_items={}
"""
text = replace_once(text, old, new, 'batch cleaning page read')

# Use the column read first. If a particular band was not recognized, retain the
# proven v75 cell consensus/gridless fallback. Never use the master to rewrite a
# cleaning value merely because it is far away from the expected map length.
old = """        value_cell=cut(val_box)
        value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
        if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
        expected=match.get('expected') if match else None
        if kind=='cleaning':
            value=_choose_cleaning_length(value_candidates,expected)
            distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}
            needs_consensus=(not value_candidates or value is None or len(distinct)>1 or
                (value is not None and expected not in (None,0) and
                 abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))
            if needs_consensus:
                # Re-read inside several small horizontal margins.  This removes
                # the vertical grid rules that caused 2 -> 7 and 224 -> 22 while
                # retaining the full digit string.  New crop pixels also avoid
                # reusing a stale OCR-cache result from the border-touching crop.
                consensus=list(value_candidates)
                width=value_cell.shape[1]
                for ratio in (.015,.030,.045,.060):
                    pad=max(2,int(round(width*ratio)))
                    if width>pad*2+4:
                        consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                # If a digit touches or is distorted by a table rule, horizontal
                # trimming alone can repeatedly agree on the same wrong value
                # (for example 275 -> 75 or 224 -> 274).  Remove grid rules and
                # add those OCR observations to the same printed-value vote.
                consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                value=_choose_cleaning_length(consensus,expected)
        else:
            value=_choose_length(value_candidates,expected)
        if value is not None and expected not in (None,0) and abs(float(value)-float(expected))>max(100,float(expected)*1.5):
            # An implausible fast result gets the full OCR ensemble before review.
            expanded=_ocr_digits(cut(val_box),True,fast_plain=False)
            if expanded:
                value=_choose_length(list(value_candidates)+list(expanded),expected)
"""
new = """        value_cell=cut(val_box)
        expected=match.get('expected') if match else None
        if kind=='cleaning':
            value_candidates=list(batch_cleaning_values.get(band_index,[]))
            if value_candidates:
                value=_choose_cleaning_length(value_candidates,expected)
            else:
                value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
                if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
                value=_choose_cleaning_length(value_candidates,expected)
                distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}
                needs_consensus=(not value_candidates or value is None or len(distinct)>1 or
                    (value is not None and expected not in (None,0) and
                     abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))
                if needs_consensus:
                    consensus=list(value_candidates)
                    width=value_cell.shape[1]
                    for ratio in (.015,.030,.045,.060):
                        pad=max(2,int(round(width*ratio)))
                        if width>pad*2+4:
                            consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                    consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                    value=_choose_cleaning_length(consensus,expected)
        else:
            value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
            if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
            value=_choose_length(value_candidates,expected)
        if (kind!='cleaning' and value is not None and expected not in (None,0) and
                abs(float(value)-float(expected))>max(100,float(expected)*1.5)):
            # Keep the established pipe-video fallback unchanged. Cleaning values
            # remain exactly what OCR observed, even when they differ from master.
            expanded=_ocr_digits(cut(val_box),True,fast_plain=False)
            if expanded:
                value=_choose_length(list(value_candidates)+list(expanded),expected)
"""
text = replace_once(text, old, new, 'cleaning batch primary parser')

text, n = re.subn(r"APP_VERSION = ['\"]\d+['\"]", "APP_VERSION = '78'", text, count=1)
if n != 1:
    raise SystemExit('APP_VERSION replacement failed')
text, n = re.subn(r"OCR_CACHE_VERSION = ['\"]v\d+['\"]", "OCR_CACHE_VERSION = 'v5'", text, count=1)
if n != 1:
    raise SystemExit('OCR cache version replacement failed')
APP.write_text(text, encoding='utf-8')

updater = UPDATER.read_text(encoding='utf-8')
updater, n = re.subn(r"CURRENT_VERSION = ['\"]\d+['\"]", 'CURRENT_VERSION = "78"', updater, count=1)
if n != 1:
    raise SystemExit('CURRENT_VERSION replacement failed')
UPDATER.write_text(updater, encoding='utf-8')

# The v75 OCR fallback regression still applies; only its expected cache namespace changes.
test = V75_TEST.read_text(encoding='utf-8').replace("OCR_CACHE_VERSION = 'v3'", "OCR_CACHE_VERSION = 'v5'")
V75_TEST.write_text(test, encoding='utf-8')

readme = README.read_text(encoding='utf-8')
title = 'Version 78 cleaning OCR recovery'
if title not in readme:
    readme += """

Version 78 cleaning OCR recovery
--------------------------------
- Removes the v77 simple-first cleaning-length OCR strategy.
- Removes v76 automatic total-driven row reselection; the printed total validates rows but never silently solves them.
- Reads the detected Wheel Walk column as one aligned OCR column with table borders trimmed away, then maps each observed number back to its row.
- Retains the v75 per-cell consensus/grid-rule-removal OCR only when the column pass misses an individual row.
- Cleaning values are never replaced from the master just because the field length differs substantially.
- Keeps the saved-layout auto-accept improvement so confirmed table layouts do not prompt again unnecessarily.
- Uses OCR cache v5 so incorrect v76/v77 cached reads are never reused.
"""
    README.write_text(readme, encoding='utf-8')

GUARD.write_text("""from pathlib import Path

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "APP_VERSION = '78'" in src
assert "OCR_CACHE_VERSION = 'v5'" in src
assert 'def _batch_cleaning_length_candidates' in src
assert '_batch_cleaning_length_candidates(img,bands,table,val_box,total_band_index)' in src
assert 'value_candidates=list(batch_cleaning_values.get(band_index,[]))' in src
assert 'consensus.extend(_ocr_gridless_number_candidates(value_cell,True))' in src
assert "if (kind!='cleaning' and value is not None" in src
assert 'def _simple_cleaning_length_candidates' not in src
assert 'def _fallback_cleaning_length_candidates' not in src
assert 'def retry_total_length_ocr' not in src
assert 'OCR LENGTH RESELECTED USING VERIFIED PDF TOTAL' not in src
saved_gate = """ + repr("""if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)""") + """
assert saved_gate in src
print('v78 column cleaning OCR + fail-closed total guard passed.')
""", encoding='utf-8')

print('Applied v78 cleaning OCR recovery.')
