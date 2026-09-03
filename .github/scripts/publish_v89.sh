#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3-tk
python -m pip install --quiet numpy opencv-python-headless openpyxl pymupdf pillow pytesseract

python .github/scripts/release_v89.py
python -m py_compile working_source/app/reno_scan_updater.py working_source/app/xps_update.py

for test in working_source/tests/regression_*.py; do
  name=$(basename "$test")
  case "$name" in
    regression_tall_cleaning_header.py|regression_workorder_preview.py|regression_v76_layout_skip.py|regression_v77_simple_first.py)
      echo "SKIP known stale/private fixture test: $name"
      ;;
    *)
      echo "RUN $name"
      python "$test"
      ;;
  esac
done

python - <<'PY'
from pathlib import Path
import re
app=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
updater=Path('working_source/app/xps_update.py').read_text(encoding='utf-8')
assert re.search(r"^APP_VERSION\s*=\s*['\"]89['\"]",app,re.M)
assert re.search(r'^CURRENT_VERSION\s*=\s*[\"\']89[\"\']',updater,re.M)
for required in (
    "if up_full and dn_full:\n        return None,'NOT MATCHED'",
    "prefix[0] in ('I','L') and prefix[1:] in prefixes",
    "'survev' in compact",
    'def resolve_unmatched_for_update(',
    'def resolve_pipe_duplicate_groups(',
    'Expected Manholes:',
    'def _resolve_printed_total_sources(',
    'def _batch_pair_endpoint_candidates(',
    'def apply_manual_asset_edit(',
    'MAX_ROW_LENGTH = 1700.0',
    'MAX_ROW_LENGTH_DECIMALS = 2'):
    assert required in app, required
print('v89 release parser-preservation and final safeguard checks passed.')
PY

git diff --check

rm -rf dist
mkdir -p dist/XPS_Tracker_Updater
cp -a working_source/app/. dist/XPS_Tracker_Updater/
find dist -type d -name '__pycache__' -prune -exec rm -rf {} +
find dist -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
test -f dist/XPS_Tracker_Updater/reno_scan_updater.py
test -f dist/XPS_Tracker_Updater/xps_update.py
test -f dist/XPS_Tracker_Updater/run_xps_tracker.bat
(
  cd dist
  zip -qr XPS_Tracker_Updater_v89.zip XPS_Tracker_Updater
  unzip -t XPS_Tracker_Updater_v89.zip
  python - <<'PY'
import zipfile
from pathlib import Path
archive=Path('XPS_Tracker_Updater_v89.zip')
with zipfile.ZipFile(archive) as z:
    names=z.namelist()
    assert names and all(n.startswith('XPS_Tracker_Updater/') for n in names)
    for required in ('XPS_Tracker_Updater/reno_scan_updater.py','XPS_Tracker_Updater/xps_update.py','XPS_Tracker_Updater/run_xps_tracker.bat'):
        assert required in names, required
    forbidden=('.xlsx','.pdf','ocr_cache','8-24-2026','8-26-2026','8-19-2026','8-17-2026','8-11-2026')
    assert not any(any(token.lower() in n.lower() for token in forbidden) for n in names), 'customer/test data leaked into ZIP'
print('v89 ZIP structure and privacy check passed.')
PY
)

RELEASE_SHA=$(sha256sum dist/XPS_Tracker_Updater_v89.zip | awk '{print $1}')
RELEASE_SIZE=$(stat -c%s dist/XPS_Tracker_Updater_v89.zip)
export RELEASE_SHA RELEASE_SIZE

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git rm -f .github/workflows/publish-v89.yml .github/scripts/release_v89.py .github/scripts/publish_v89.sh .release-v89-trigger
git add working_source/app/reno_scan_updater.py working_source/app/xps_update.py working_source/tests/regression_v89_printed_pair_identity.py README.md
git commit -m 'Release v89 [skip ci]'
git push origin HEAD:v89-work

if gh release view v89 --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  echo 'v89 release already exists; refusing to overwrite it.' >&2
  exit 1
fi
RELEASE_COMMIT=$(git rev-parse HEAD)
gh release create v89 dist/XPS_Tracker_Updater_v89.zip --repo "$GITHUB_REPOSITORY" --target "$RELEASE_COMMIT" --title 'XPS Tracker Updater v89' --notes 'v89 adds Manhole work-order count verification from the Description of work performed crop, uses only the final continuation-page total for multi-page Pipe/Cleaning verification, adds Add to Master / Ignore / Back to Summary decisions for unresolved assets, hardens duplicate-pipe MSA review, and adds PDF previews to Trouble Ticket editing. Final real-packet safeguards preserve complete printed endpoint pairs that are absent from the master instead of fuzzy-mapping them to nearby assets, recover a narrow left-grid OCR artifact such as IDN-1912, and recognize common OCR variants of Length Surveyed headers. Existing v88 continuation, partial-page, exact-number, and grid-recovery behavior is preserved.'

python - <<'PY'
import json,os,subprocess
repo=os.environ['GITHUB_REPOSITORY']
data=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/v89'],text=True))
asset=next((a for a in data.get('assets',[]) if a.get('name')=='XPS_Tracker_Updater_v89.zip'),None)
assert asset, 'release ZIP missing'
digest=str(asset.get('digest') or '')
if digest:
    assert digest==f"sha256:{os.environ['RELEASE_SHA']}"
assert int(asset.get('size') or 0)==int(os.environ['RELEASE_SIZE'])
print('public v89 release asset verified')
PY

git fetch origin main
rm -rf /tmp/xps-main
git worktree add --detach /tmp/xps-main origin/main
python - <<'PY'
from pathlib import Path
import json,os
path=Path('/tmp/xps-main/update_manifest.json')
data={
  'version':'89',
  'download_url':'https://github.com/painguin11/xps-tracker-updater-releases/releases/download/v89/XPS_Tracker_Updater_v89.zip',
  'sha256':os.environ['RELEASE_SHA'],
  'release_notes':[
    'Verify Manhole work-order row counts against the user-confirmed count from the Description of work performed crop',
    'Use only the final continuation page printed total for multi-page Pipe/Cleaning verification',
    'Offer Add to Master, Ignore, or Back to Summary for unresolved Pipe and Manhole rows before any master write',
    'Limit automatic MSA combination to exactly two duplicate Pipe rows and block larger duplicate groups for ID review',
    'Show PDF field previews while editing Trouble Tickets',
    'Preserve complete printed endpoint pairs that are absent from the master instead of fuzzy-mapping them to nearby assets',
    'Recover narrow left-grid endpoint OCR artifacts and common Length Surveyed header OCR variants',
    'Preserve v88 continuation, partial-page, faint-grid, and exact PDF-number safeguards'
  ]
}
path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
PY

(
  cd /tmp/xps-main
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git add update_manifest.json
  git commit -m 'Publish v89 update manifest'
  git push origin HEAD:main
  git fetch origin main
  git show origin/main:update_manifest.json > /tmp/public_manifest.json
)
python - <<'PY'
import json,os
data=json.load(open('/tmp/public_manifest.json',encoding='utf-8'))
assert data['version']=='89'
assert data['download_url']=='https://github.com/painguin11/xps-tracker-updater-releases/releases/download/v89/XPS_Tracker_Updater_v89.zip'
assert data['sha256']==os.environ['RELEASE_SHA']
print('committed public v89 manifest verified')
PY
