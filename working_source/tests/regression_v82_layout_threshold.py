from pathlib import Path

src = Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

new = "if layout.get('confidence',0)>80 and all(k in detected_roles for k in ('up','down','value','date')):"
old = "if layout.get('confidence',0)>=100 and all(k in detected_roles for k in ('up','down','value','date')):"
assert new in src
assert old not in src
assert 'A complete native detection above 80% confidence is reliable enough' in src

# Auto-accept still requires all four mapped roles; lowering confidence alone
# must never bypass confirmation for an incomplete layout.
assert "all(k in detected_roles for k in ('up','down','value','date'))" in new

print('v82 layout confidence threshold regression passed.')
