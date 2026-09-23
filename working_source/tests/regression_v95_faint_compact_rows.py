from pathlib import Path
import ast
import cv2
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(s)

assert 'def compact_horizontal_rule_ys(source):' in s
assert 'if len(rule_ys)<=4:' in s
assert 'join_width=max(3,int(round((right-left)*.003)))' in s

ns={'cv2':cv2,'np':np}
for name in ('_year15_compact_grid_bands','_year15_recover_vertical_rules'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)

# Reproduce the 8/28 compact-table geometry without any customer data. Most
# vertical rules are dark, two real column rules are faint, and the data-row
# separators are faint/dashed. The normal compact pass sees exactly four long
# horizontal rules, which is still too sparse to represent the physical rows;
# the retry must recover the real row grid before any OCR/master matching occurs.
h,w=1530,1980
img=np.full((h,w,3),255,dtype=np.uint8)
left,right=45,1930
y_rules=[120,150,180]+[210+30*i for i in range(19)]
x_rules=[45,315,585,855,1125,1395,1660,1930]

for x in x_rules:
    shade=230 if x in (315,1660) else 30
    cv2.line(img,(x,y_rules[0]),(x,y_rules[-1]),(shade,shade,shade),2)

for index,y in enumerate(y_rules):
    if index<3 or index==len(y_rules)-1:
        cv2.line(img,(left,y),(right,y),(30,30,30),2)
        continue
    x=left
    while x<right:
        x2=min(right,x+14)
        cv2.line(img,(x,y),(x2,y),(230,230,230),1)
        x=x2+5

bands,table,seed=ns['_year15_compact_grid_bands'](img)
assert table==(left,right),table
assert len(bands)==21,len(bands)  # title + header + 18 data rows + total band
assert seed==[45,585,855,1125,1395,1930],seed

recovered=ns['_year15_recover_vertical_rules'](img,bands,table,seed)
assert recovered==x_rules,recovered

# A normal solid compact grid must continue to use the unchanged first pass.
solid=img.copy()
for y in y_rules:
    cv2.line(solid,(left,y),(right,y),(30,30,30),2)
solid_bands,solid_table,solid_seed=ns['_year15_compact_grid_bands'](solid)
assert solid_table==(left,right),solid_table
assert len(solid_bands)==21,len(solid_bands)
solid_recovered=ns['_year15_recover_vertical_rules'](solid,solid_bands,solid_table,solid_seed)
assert solid_recovered==x_rules,solid_recovered

print('v95 faint compact-table row-grid regression passed')
