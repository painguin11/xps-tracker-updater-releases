from pathlib import Path
import zipfile, hashlib, shutil, os

root=Path('.')
app=root/'working_source/app/reno_scan_updater.py'
text=app.read_text(encoding='utf-8')
if "APP_VERSION = '72'" in text:
    text=text.replace("APP_VERSION = '72'","APP_VERSION = '73'",1)
elif "APP_VERSION = '73'" not in text:
    raise SystemExit('Unexpected APP_VERSION')
app.write_text(text,encoding='utf-8')

updater=root/'working_source/app/xps_update.py'
text=updater.read_text(encoding='utf-8')
if 'CURRENT_VERSION = "72"' in text:
    text=text.replace('CURRENT_VERSION = "72"','CURRENT_VERSION = "73"',1)
elif 'CURRENT_VERSION = "73"' not in text:
    raise SystemExit('Unexpected CURRENT_VERSION')
updater.write_text(text,encoding='utf-8')

readme=root/'working_source/app/README_XPS_Tracker_Updater.txt'
text=readme.read_text(encoding='utf-8')
if 'Version 73 total/date reliability' not in text:
    text += '''\n\nVersion 73 total/date reliability\n---------------------------------\n- Reads numeric totals inside the final detected grid row as well as totals below the grid.\n- Removes table rules before total OCR so border-touching digits are not clipped.\n- Rejects implausible lone-digit totals on multi-row tables instead of trusting them.\n- Uses repeated B&C table-date evidence to correct weak OCR while preserving clearly read full dates.\n'''
readme.write_text(text,encoding='utf-8')

source=app.read_text(encoding='utf-8')
for required in ("APP_VERSION = '73'",'def _ocr_gridless_number_candidates','in-grid footer total','def _dominant_sheet_date','def _read_sheet_date_evidence','def _year15_compact_grid_bands','TOTAL LENGTH VALIDATION FAILURE(S) — UPDATE MASTER BLOCKED','def parse_trouble_ticket'):
    if required not in source: raise SystemExit(f'Missing required source marker: {required}')
if 'CURRENT_VERSION = "73"' not in updater.read_text(encoding='utf-8'):
    raise SystemExit('Updater version mismatch')

release_dir=root/'.release_v73'
if release_dir.exists(): shutil.rmtree(release_dir)
package=release_dir/'XPS_Tracker_Updater'
package.mkdir(parents=True)
for item in (root/'working_source/app').iterdir():
    dest=package/item.name
    if item.is_dir(): shutil.copytree(item,dest)
    else: shutil.copy2(item,dest)
for pycache in release_dir.rglob('__pycache__'): shutil.rmtree(pycache)
for pyc in release_dir.rglob('*.pyc'): pyc.unlink()

release_zip=root/'XPS_Tracker_Updater_v73.zip'
source_zip=root/'XPS_Tracker_Updater_Source_v73.zip'
for p in (release_zip,source_zip):
    if p.exists(): p.unlink()
with zipfile.ZipFile(release_zip,'w',zipfile.ZIP_DEFLATED) as z:
    for p in package.rglob('*'):
        if p.is_file(): z.write(p,p.relative_to(release_dir))
with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as z:
    for base in (root/'working_source/app',root/'working_source/tests'):
        for p in base.rglob('*'):
            if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts:
                z.write(p,p.relative_to(root/'working_source'))

sha=hashlib.sha256(release_zip.read_bytes()).hexdigest()
(root/'v73.sha256').write_text(sha+'\n',encoding='utf-8')
print(sha)
