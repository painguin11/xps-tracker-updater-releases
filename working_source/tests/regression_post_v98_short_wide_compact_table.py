from pathlib import Path
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
