from pathlib import Path

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
saved_gate = "if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):\n                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'\n                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))\n                            else:\n                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)"
assert saved_gate in src
print('v78 column cleaning OCR + fail-closed total guard passed.')
