from pathlib import Path

src = Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

native_gate = "if layout.get('confidence',0)>=100 and all(k in detected_roles for k in ('up','down','value','date')):"
assert native_gate in src, '100% native-layout auto-accept gate was removed'

saved_gate = """if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)"""
assert saved_gate in src, 'saved 100% layout still falls through to the confirmation dialog'

print('v76 100%/saved layout auto-confirm safeguard passed.')
