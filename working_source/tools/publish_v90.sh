#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from pathlib import Path
import re

app = Path('working_source/app/reno_scan_updater.py')
text = app.read_text(encoding='utf-8')
new, count = re.subn(r"^APP_VERSION\s*=\s*['\"]89['\"]", "APP_VERSION = '90'", text, count=1, flags=re.M)
if count != 1:
    raise SystemExit('Expected exactly one APP_VERSION 89 assignment')
app.write_text(new, encoding='utf-8')

updater = Path('working_source/app/xps_update.py')
text = updater.read_text(encoding='utf-8')
new, count = re.subn(r'^CURRENT_VERSION\s*=\s*["\']89["\']', 'CURRENT_VERSION = "90"', text, count=1, flags=re.M)
if count != 1:
    raise SystemExit('Expected exactly one CURRENT_VERSION 89 assignment')
updater.write_text(new, encoding='utf-8')

readme = Path('working_source/app/README_XPS_Tracker_Updater.txt')
text = readme.read_text(encoding='utf-8').rstrip() + '\n\n'
section = '''Version 90 review workflow improvements
---------------------------------------
- Shows PDF ID image previews directly in the Add to Master / Ignore decision popup for unresolved assets.
- Pipe and Cleaning review shows upstream and downstream ID crops side-by-side; Manhole review shows the manhole ID crop.
- Preserves the current Live Summary vertical position and selected/focused row when Edit Selected rebuilds the summary.
- Preserves all v89 printed-pair identity, new-asset, continuation, total-validation, and OCR safeguards.
'''
if 'Version 90 review workflow improvements' not in text:
    text += section
readme.write_text(text, encoding='utf-8')
PY

git diff --check
python -m py_compile working_source/app/reno_scan_updater.py working_source/app/xps_update.py
python - <<'PY'
from pathlib import Path
import re
app = Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
updater = Path('working_source/app/xps_update.py').read_text(encoding='utf-8')
assert re.search(r"^APP_VERSION\s*=\s*['\"]90['\"]", app, re.M)
assert re.search(r'^CURRENT_VERSION\s*=\s*["\']90["\']', updater, re.M)
assert "APP_TITLE = f'{APP_NAME} v{APP_VERSION}'" in app
print('Version checks passed: app/display/updater = 90')
PY

python - <<'PY'
from pathlib import Path
import subprocess, sys

tests = sorted(Path('working_source/tests').glob('regression_*.py'))
passed = []
skipped = []
for test in tests:
    print(f'===== {test} =====', flush=True)
    proc = subprocess.run([sys.executable, str(test)], text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout, end='')
    if proc.stderr:
        print(proc.stderr, end='')
    if proc.returncode == 0:
        passed.append(test.name)
        continue
    combined = (proc.stdout or '') + '\n' + (proc.stderr or '')
    missing_private_fixture = (
        'FileNotFoundError' in combined and
        any(marker in combined for marker in (
            '/upload/', "'upload/", '/output/package_v69/', "'output/package_v69/",
            '8-11-2026.pdf', '8-17-2026', 'fixture PDF unavailable',
        ))
    )
    if missing_private_fixture:
        skipped.append(test.name)
        print(f'SKIP {test.name}: private/stale fixture is not present in the public release repository.')
        continue
    raise SystemExit(f'{test.name} failed with exit code {proc.returncode}')
print(f'Regression summary: {len(passed)} passed, {len(skipped)} private/stale fixture skips.')
if skipped:
    print('Skipped:', ', '.join(skipped))
PY

python - <<'PY'
from pathlib import Path
source = Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
required = [
    'PDF ID verification',
    "('Upstream ID',record.get('up') or '', 'upstream')",
    "('Downstream ID',record.get('down') or '', 'downstream')",
    "[('Manhole ID',record.get('asset') or '', 'asset')]",
    'vertical_position=self.tree.yview()[0]',
    'self.tree.yview_moveto(vertical_position)',
    'self.tree.selection_set(surviving)',
    'self.tree.focus(focused)',
]
for item in required:
    assert item in source, item
for legacy in ('parse_reno', 'parse_year15', 'parse_year15_manholes', 'Phase 2 Year 1 Manholes'):
    assert legacy in source, legacy
print('v90 UI and unrelated-parser structural safeguards passed.')
PY

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git rm -f working_source/tools/publish_v90.sh
git add working_source/app/reno_scan_updater.py working_source/app/xps_update.py working_source/app/README_XPS_Tracker_Updater.txt
git commit -m "Prepare XPS Tracker Updater v90 release"
git push origin HEAD:v90-work
RELEASE_COMMIT=$(git rev-parse HEAD)

python - <<'PY'
from pathlib import Path
import hashlib, zipfile
app = Path('working_source/app')
zip_path = Path('XPS_Tracker_Updater_v90.zip')
top = 'XPS_Tracker_Updater'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted(app.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(app)
        if '__pycache__' in rel.parts or path.suffix == '.pyc':
            continue
        z.write(path, f'{top}/{rel.as_posix()}')
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    names = z.namelist()
    assert names and all(name.startswith(top + '/') for name in names)
    required = {
        f'{top}/reno_scan_updater.py', f'{top}/xps_update.py',
        f'{top}/run_xps_tracker.bat', f'{top}/setup_and_run.bat',
        f'{top}/README_XPS_Tracker_Updater.txt', f'{top}/update_config.json',
        f'{top}/xps_tracker_updater.ico',
    }
    assert not required.difference(names), required.difference(names)
    assert "APP_VERSION = '90'" in z.read(f'{top}/reno_scan_updater.py').decode('utf-8')
    assert 'CURRENT_VERSION = "90"' in z.read(f'{top}/xps_update.py').decode('utf-8')
digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
Path('v90.sha256').write_text(digest + '\n', encoding='ascii')
print('ZIP size:', zip_path.stat().st_size)
print('SHA256:', digest)
PY
unzip -t XPS_Tracker_Updater_v90.zip
ZIP_SHA256=$(cat v90.sha256)
ZIP_SIZE=$(stat -c%s XPS_Tracker_Updater_v90.zip)

GH_TOKEN="$GITHUB_TOKEN" gh release create v90 XPS_Tracker_Updater_v90.zip \
  --repo "$GITHUB_REPOSITORY" \
  --target "$RELEASE_COMMIT" \
  --title "XPS Tracker Updater v90" \
  --notes "v90 improves manual review speed and verification. Unresolved Pipe/Cleaning assets now show upstream and downstream PDF ID crops directly in the Add to Master / Ignore popup, while unresolved Manholes show the manhole ID crop. Editing a summary row now preserves the Live Summary scroll position and selected/focused row instead of jumping back to the top. Existing v89 printed-pair identity, Add/Ignore behavior, continuation-page handling, total validation, MSA safeguards, and OCR protections are preserved."

ZIP_SHA256="$ZIP_SHA256" ZIP_SIZE="$ZIP_SIZE" GH_TOKEN="$GITHUB_TOKEN" python - <<'PY'
import json, os, subprocess, time
expected_sha = os.environ['ZIP_SHA256'].strip().lower()
expected_size = int(os.environ['ZIP_SIZE'])
for _ in range(12):
    raw = subprocess.check_output(['gh','api',f'repos/{os.environ["GITHUB_REPOSITORY"]}/releases/tags/v90'], text=True, env={**os.environ, 'GH_TOKEN': os.environ['GITHUB_TOKEN']})
    release = json.loads(raw)
    assets = [a for a in release.get('assets',[]) if a.get('name') == 'XPS_Tracker_Updater_v90.zip']
    if assets:
        asset = assets[0]
        digest = str(asset.get('digest') or '').lower().removeprefix('sha256:')
        assert asset.get('state') == 'uploaded'
        assert int(asset.get('size') or 0) == expected_size
        assert digest == expected_sha, (digest, expected_sha)
        assert asset.get('browser_download_url') == 'https://github.com/painguin11/xps-tracker-updater-releases/releases/download/v90/XPS_Tracker_Updater_v90.zip'
        print('Public release asset verified:', asset['name'], asset['size'], asset['digest'])
        break
    time.sleep(2)
else:
    raise SystemExit('v90 release asset did not become visible')
PY

git fetch origin main
git checkout -B main origin/main
ZIP_SHA256="$ZIP_SHA256" python - <<'PY'
from pathlib import Path
import json, os
Path('update_manifest.json').write_text(json.dumps({
    'version': '90',
    'download_url': 'https://github.com/painguin11/xps-tracker-updater-releases/releases/download/v90/XPS_Tracker_Updater_v90.zip',
    'sha256': os.environ['ZIP_SHA256'].strip().lower(),
    'release_notes': [
        'Show upstream and downstream PDF ID image previews in the Add to Master / Ignore popup for unresolved Pipe and Cleaning assets',
        'Show the PDF manhole ID image preview in the Add to Master / Ignore popup for unresolved Manholes',
        'Preserve the Live Summary scroll position after editing a row',
        'Restore the selected and focused summary row after the edit refresh',
        'Preserve v89 printed-pair identity, new-asset, continuation, total-validation, MSA, and OCR safeguards'
    ]
}, indent=2) + '\n', encoding='utf-8')
PY
git add update_manifest.json
git commit -m "Publish v90 update manifest"
git push origin HEAD:main

ZIP_SHA256="$ZIP_SHA256" python - <<'PY'
import json, os, time, urllib.request
url = 'https://raw.githubusercontent.com/painguin11/xps-tracker-updater-releases/main/update_manifest.json'
expected = os.environ['ZIP_SHA256'].strip().lower()
for _ in range(12):
    with urllib.request.urlopen(url + f'?t={time.time()}', timeout=10) as r:
        data = json.loads(r.read().decode('utf-8'))
    if data.get('version') == '90':
        assert data.get('sha256') == expected
        assert data.get('download_url') == 'https://github.com/painguin11/xps-tracker-updater-releases/releases/download/v90/XPS_Tracker_Updater_v90.zip'
        print('Manifest verified:', data['version'], data['sha256'])
        break
    time.sleep(2)
else:
    raise SystemExit('Published manifest did not update to v90')
PY
