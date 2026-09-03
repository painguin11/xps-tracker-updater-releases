from pathlib import Path

SOURCE=Path('working_source/app/reno_scan_updater.py')
s=SOURCE.read_text(encoding='utf-8')
assert "APP_VERSION = '92'" in s  # development branch stays on production version until publish

# Approved new pipe rows must be marked in the master Notes column whether they
# are inserted below a detected base row or appended through Add to Master.
assert s.count("append_note(ps.Cells(rr,notes_col),'NEW PIPE')") >= 2

# Approved new manholes need the same explicit note for both insertion paths.
assert s.count("append_note(ms.Cells(rr,notes_col),'NEW MANHOLE')") >= 2

# Notes remain optional for master layouts without a Notes column.
assert "notes_col=ph.get('notes')" in s
assert "notes_col=mh.get('notes')" in s

print('v93 new Pipe/Manhole master-note regression passed')
