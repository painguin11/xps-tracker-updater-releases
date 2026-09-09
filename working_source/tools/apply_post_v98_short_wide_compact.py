from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'app' / 'reno_scan_updater.py'
TEST = ROOT / 'tests' / 'regression_post_v98_short_wide_compact_table.py'
CONTEXT = ROOT.parent / 'PROJECT_CONTEXT.md'

source = SOURCE.read_text(encoding='utf-8')
old = """    candidates=[]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if ww>=w*.35 and hh>=h*.12 and ww*hh<=w*h*.85:
            candidates.append((ww*hh,x,y,ww,hh))
"""
new = """    candidates=[]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        # Normal compact tables still use the established minimum height. A very
        # short report (header + only a couple of rows + total) can be physically
        # valid while occupying less than 12% of the page after rotation. Admit
        # that shorter shape only when it spans most of the page width; the strict
        # vertical-rule, horizontal-rule, column-count, and header-role checks
        # below still have to validate the region before it can become a table.
        normal_region=ww>=w*.35 and hh>=h*.12
        short_wide_region=ww>=w*.70 and hh>=h*.055
        if (normal_region or short_wide_region) and ww*hh<=w*h*.85:
            candidates.append((ww*hh,x,y,ww,hh))
"""
if new not in source:
    if source.count(old) != 1:
        raise SystemExit(f'Expected exactly one compact-table candidate block, found {source.count(old)}')
    SOURCE.write_text(source.replace(old, new, 1), encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast
import cv2
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(s)

assert 'short_wide_region=ww>=w*.70 and hh>=h*.055' in s

ns={'cv2':cv2,'np':np}
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_year15_compact_grid_bands')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

# Reproduce the geometry class without customer data: after rotation the table is
# almost full-page width but only about 8% of page height because it contains a
# header, two data rows, and a total row. The old 12%-height gate rejected this
# before any of the existing grid/header safeguards could inspect it.
h,w=1530,1980
img=np.full((h,w,3),255,dtype=np.uint8)
left,right=129,1854
y_rules=[128,158,185,211,242]
x_rules=[129,375,621,868,1114,1361,1608,1854]
for x in x_rules:
    cv2.line(img,(x,y_rules[0]),(x,y_rules[-1]),(30,30,30),2)
for y in y_rules:
    cv2.line(img,(left,y),(right,y),(30,30,30),2)

bands,table,seed=ns['_year15_compact_grid_bands'](img)
assert table==(left,right),table
assert len(bands)==4,bands
assert seed==x_rules,seed

# Keep the relaxation narrow: a similarly short region that is not at least 70%
# of page width must still fail the candidate gate instead of becoming a table.
narrow=np.full((h,w,3),255,dtype=np.uint8)
n_left,n_right=300,1450
n_x=[300,465,630,795,960,1125,1290,1450]
for x in n_x:
    cv2.line(narrow,(x,y_rules[0]),(x,y_rules[-1]),(30,30,30),2)
for y in y_rules:
    cv2.line(narrow,(n_left,y),(n_right,y),(30,30,30),2)

n_bands,n_table,n_seed=ns['_year15_compact_grid_bands'](narrow)
assert n_bands==[] and n_table is None and n_seed is None,(n_bands,n_table,n_seed)

print('post-v98 short-wide compact-table regression passed')
''', encoding='utf-8')

context = CONTEXT.read_text(encoding='utf-8')
marker = '## Unreleased post-v98 short-wide compact-table safeguard'
if marker not in context:
    context += """

## Unreleased post-v98 short-wide compact-table safeguard

- Very short Brown & Caldwell pair tables can contain only a header, a few data
  rows, and a total, leaving the real table under the previous 12% page-height
  threshold after rotation even though it spans almost the full page width.
- The compact-grid candidate stage now admits that short shape only when the
  connected region spans at least 70% of page width and at least 5.5% of page
  height. Existing vertical-rule, horizontal-rule, column-count, header-role,
  matching, and review safeguards remain unchanged.
- Permanent synthetic regression:
  `working_source/tests/regression_post_v98_short_wide_compact_table.py`.
"""
    CONTEXT.write_text(context, encoding='utf-8')

print('Applied post-v98 short-wide compact-table safeguard and regression.')
