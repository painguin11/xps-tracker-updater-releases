from pathlib import Path
import re

APP = Path('working_source/app/reno_scan_updater.py')
UPDATER = Path('working_source/app/xps_update.py')
README = Path('working_source/app/README_XPS_Tracker_Updater.txt')
TEST = Path('working_source/tests/regression_v79_layout_speed.py')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'{label}: expected source block not found; refusing broad edit')
    return text.replace(old, new, 1)


text = APP.read_text(encoding='utf-8')
old = '''    cgray=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)\n    cinv=cv2.threshold(cgray,225,255,cv2.THRESH_BINARY_INV)[1]\n    joined=cv2.morphologyEx(\n        cinv,cv2.MORPH_CLOSE,\n        cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(3,int(bh*.012)))))\n    vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(20,int(bh*.12))))\n    vertical=cv2.morphologyEx(joined,cv2.MORPH_OPEN,vk)\n    contours,_=cv2.findContours(vertical,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)\n\n    # Short fragments at one x-coordinate are merged before judging continuity.\n    # This repairs grid rules interrupted by printed text crossing the line.\n    rules=[]\n    for contour in contours:\n        x,y,ww,hh=cv2.boundingRect(contour)\n        if hh>=bh*.18 and ww<=max(24,bw*.025):\n            rules.append((x+ww//2,y,y+hh))\n    rules.sort(); merged=[]\n    for rule in rules:\n        if merged and abs(rule[0]-merged[-1][0])<=max(5,int(bw*.006)):\n            old=merged[-1]\n            merged[-1]=((old[0]+rule[0])//2,min(old[1],rule[1]),max(old[2],rule[2]))\n        else:\n            merged.append(rule)\n    if len(merged)<5:\n        return [],None,None\n\n    max_span=max(y2-y1 for _,y1,y2 in merged)\n    strong=[rule for rule in merged if rule[2]-rule[1]>=max_span*.85]\n    if len(strong)<5:\n        return [],None,None\n'''
new = '''    cgray=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)\n    cinv=cv2.threshold(cgray,225,255,cv2.THRESH_BINARY_INV)[1]\n\n    def collect_vertical_rules(binary,kernel_ratio,min_span_ratio):\n        # Prefer uninterrupted printed grid rules. Joining vertical gaps before\n        # this test can accidentally connect repeated letter/digit strokes in a\n        # long table and make dozens of fake columns.\n        vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(20,int(bh*kernel_ratio))))\n        vertical=cv2.morphologyEx(binary,cv2.MORPH_OPEN,vk)\n        found,_=cv2.findContours(vertical,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)\n        rules=[]\n        for contour in found:\n            x,y,ww,hh=cv2.boundingRect(contour)\n            if hh>=bh*.30 and ww<=max(24,bw*.025):\n                rules.append((x+ww//2,y,y+hh))\n        rules.sort(); merged=[]\n        for rule in rules:\n            if merged and abs(rule[0]-merged[-1][0])<=max(5,int(bw*.006)):\n                previous=merged[-1]\n                merged[-1]=((previous[0]+rule[0])//2,min(previous[1],rule[1]),max(previous[2],rule[2]))\n            else:\n                merged.append(rule)\n        if len(merged)<5:\n            return []\n        max_span=max(y2-y1 for _,y1,y2 in merged)\n        return [rule for rule in merged if rule[2]-rule[1]>=max_span*min_span_ratio]\n\n    # Clean scans should resolve from the raw binary image. This is both faster\n    # and much less likely to mistake repeated text strokes for vertical rules.\n    strong=collect_vertical_rules(cinv,.18,.80)\n    if not (5<=len(strong)<=20):\n        # Broken/faint grids still get the older gap-joining repair, but reject an\n        # implausibly large rule set rather than feeding dozens of fake columns\n        # into the expensive master-assisted OCR stage.\n        joined=cv2.morphologyEx(\n            cinv,cv2.MORPH_CLOSE,\n            cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(3,int(bh*.012)))))\n        strong=collect_vertical_rules(joined,.12,.85)\n    if not (5<=len(strong)<=20):\n        return [],None,None\n'''
text = replace_once(text, old, new, 'compact vertical-rule detector')
text = replace_once(
    text,
    "    if len(column_boxes)<2 or len(bands)<2: return None,0,0\n",
    "    if len(column_boxes)<2 or len(bands)<2: return None,0,0\n    # Bad geometry must never turn into hundreds of OCR calls. Normal B&C pair\n    # tables are far below this bound; an implausible set should be confirmed\n    # manually rather than spending minutes master-scoring fake columns.\n    if len(column_boxes)>20: return None,0,0\n",
    'master-assisted column-count guard')
text, n = re.subn(r"APP_VERSION = ['\"]\d+['\"]", "APP_VERSION = '79'", text, count=1)
if n != 1:
    raise SystemExit('APP_VERSION replacement failed')
APP.write_text(text, encoding='utf-8')

updater = UPDATER.read_text(encoding='utf-8')
updater, n = re.subn(r"CURRENT_VERSION = ['\"]\d+['\"]", 'CURRENT_VERSION = "79"', updater, count=1)
if n != 1:
    raise SystemExit('CURRENT_VERSION replacement failed')
UPDATER.write_text(updater, encoding='utf-8')

readme = README.read_text(encoding='utf-8')
heading = 'Version 79 compact-layout performance fix'
if heading not in readme:
    readme += '''\n\nVersion 79 compact-layout performance fix\n-----------------------------------------\n- Compact B&C tables first detect uninterrupted vertical grid rules before any gap-joining repair.\n- Repeated printed text strokes can no longer be promoted into dozens of fake table columns on clean scans.\n- The older gap-joining grid repair remains available only when the clean raw-grid pass cannot resolve a plausible rule set.\n- Master-assisted endpoint scoring refuses implausible layouts above 20 columns instead of launching hundreds of OCR calls.\n- No cleaning-length OCR, total validation, matching, or master-write behavior is changed.\n'''
    README.write_text(readme, encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast
import cv2
import numpy as np

src = Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert "APP_VERSION = '79'" in src
assert 'strong=collect_vertical_rules(cinv,.18,.80)' in src
assert 'if not (5<=len(strong)<=20):' in src
assert 'strong=collect_vertical_rules(joined,.12,.85)' in src
assert 'if len(column_boxes)>20: return None,0,0' in src

# Execute only the compact-grid helper so this geometry regression remains
# independent of Windows COM/Tk imports on the Linux CI runner.
tree = ast.parse(src)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_year15_compact_grid_bands')
namespace = {'cv2': cv2, 'np': np}
exec(compile(ast.Module(body=[node], type_ignores=[]), '<compact-grid>', 'exec'), namespace)
detect = namespace['_year15_compact_grid_bands']

# Synthetic 9-column compact table. Repeated short vertical strokes emulate the
# failure mode where row text aligned at the same x-coordinate across many rows.
img = np.full((1200, 1800, 3), 255, np.uint8)
x0, y0, x1, y1 = 180, 160, 1500, 850
xs = [x0, 300, 430, 570, 800, 870, 1110, 1240, 1370, x1]
ys = np.linspace(y0, y1, 26, dtype=int)
for x in xs:
    cv2.line(img, (x, y0), (x, y1), (0, 0, 0), 3)
for y in ys:
    cv2.line(img, (x0, y), (x1, y), (0, 0, 0), 2)
for fake_x in [220,250,350,390,480,520,620,680,740,920,960,1010,1060,1300,1330,1430]:
    for a, b in zip(ys[:-1], ys[1:]):
        cv2.line(img, (fake_x, int(a)+7), (fake_x, int(b)-7), (0, 0, 0), 2)

bands, table, bounds = detect(img)
assert len(bounds or []) == 10, bounds
assert len(bands) >= 20, len(bands)
assert table is not None and table[1] - table[0] > 1000, table
print('v79 compact-layout speed regression passed.')
''', encoding='utf-8')

print('Applied v79 compact-layout performance fix.')
