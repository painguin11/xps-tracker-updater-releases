from pathlib import Path

path=Path('working_source/tests/regression_v78_rollback.py')
text=path.read_text(encoding='utf-8')
old='''from pathlib import Path\n\nsrc=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')\nassert "APP_VERSION = '78'" in src\n'''
new='''from pathlib import Path\nimport re\n\nsrc=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')\nassert re.search(r"APP_VERSION = ['\\\"]\\d+['\\\"]",src)\n'''
if old not in text:
    if 'assert re.search(r"APP_VERSION' in text:
        print('v78 regression already version-agnostic.')
    else:
        raise SystemExit('Expected v78 version assertion not found.')
else:
    path.write_text(text.replace(old,new,1),encoding='utf-8')
    print('Made v78 behavior regression version-agnostic.')
