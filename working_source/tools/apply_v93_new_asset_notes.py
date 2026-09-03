from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
s=APP.read_text(encoding='utf-8')
assert "APP_VERSION = '92'" in s, 'v93-work must remain on v92 version until publish'
assert s.count('highlight_approved_master_row(ps,rr,last_col)')==2
assert s.count('highlight_approved_master_row(ms,rr,last_col)')==2
assert "append_note(ps.Cells(rr,notes_col),'NEW PIPE')" not in s
assert "append_note(ms.Cells(rr,notes_col),'NEW MANHOLE')" not in s

s=s.replace(
    '                highlight_approved_master_row(ps,rr,last_col)\n',
    "                notes_col=ph.get('notes')\n"
    "                if notes_col: append_note(ps.Cells(rr,notes_col),'NEW PIPE')\n"
    '                highlight_approved_master_row(ps,rr,last_col)\n'
)
s=s.replace(
    '                highlight_approved_master_row(ms,rr,last_col)\n',
    "                notes_col=mh.get('notes')\n"
    "                if notes_col: append_note(ms.Cells(rr,notes_col),'NEW MANHOLE')\n"
    '                highlight_approved_master_row(ms,rr,last_col)\n'
)

assert s.count("append_note(ps.Cells(rr,notes_col),'NEW PIPE')")==2
assert s.count("append_note(ms.Cells(rr,notes_col),'NEW MANHOLE')")==2
APP.write_text(s,encoding='utf-8')
print('Applied v93 new Pipe/Manhole master-note markers.')
