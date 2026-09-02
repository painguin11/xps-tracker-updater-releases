from pathlib import Path
p=Path('working_source/app/reno_scan_updater.py')
s=p.read_text(encoding='utf-8')
old="""            if kind=='Cleaning' and not all_rows:
                reread=_conservative_cleaning_reread(record.get('_length_value_cell') or record.get('_cleaning_value_cell'))
            else:
"""
new="""            if kind=='Cleaning' and not all_rows:
                cell=record.get('_length_value_cell')
                if cell is None:
                    cell=record.get('_cleaning_value_cell')
                reread=_conservative_cleaning_reread(cell)
            else:
"""
if old not in s: raise SystemExit('target cleaning reread block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

t=Path('working_source/tests/regression_v83_length_recovery.py')
ts=t.read_text(encoding='utf-8')
ts += "\nassert \"record.get('_length_value_cell') or record.get('_cleaning_value_cell')\" not in s\nassert \"cell=record.get('_length_value_cell')\" in s\nprint('v83 numpy cell-selection regression passed')\n"
t.write_text(ts,encoding='utf-8')
print('fixed numpy image selection')
