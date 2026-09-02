from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
text=APP.read_text(encoding='utf-8')
old="'search_pattern': r'(?<![A-Z0-9])(\\d+)(?![A-Z0-9])',"
new="'search_pattern': r'(?<![A-Z0-9-])(\\d+)(?![A-Z0-9-])',"
if old not in text:
    raise SystemExit('Reno numeric asset rule not found')
text=text.replace(old,new,1)
APP.write_text(text,encoding='utf-8')
print('Tightened Reno numeric token boundary.')
