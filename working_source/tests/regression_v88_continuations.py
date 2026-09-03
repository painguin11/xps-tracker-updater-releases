from pathlib import Path
import ast
import cv2
import numpy as np

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

for required in (
    'def _year15_recover_vertical_rules(',
    'def prepare_year15_pair_layout(page,master_index,kind,inherited_layout=None,preferred_deg=None):',
    "'source':'inherited continuation / '+geometry_source",
    "item['is_continuation']=True",
    "last_pair_layout[template_key]=layout",
    "preferred_deg=item.get('effective_deg') if item.get('is_continuation') else None",
    'def parse_year15_manholes(page, master_index, on_row=None, on_progress=None, orientation_deg=None):',
    "img=_year15_oriented(page,'manholes',preferred_deg=orientation_deg)",
    'def add_unprocessed_page(self,wo,page_number,kind,reason):',
    "self.tree.insert('',0,iid=iid",
    "PAGES {pages} COULD NOT BE PROCESSED",
    'safe_total_sources={key:value for key,value in total_sources.items() if key not in incomplete_total_keys}',
    '    if can_inherit:\n',
    'horizontal_inv=cv2.threshold(gray,240,255,cv2.THRESH_BINARY_INV)[1]',
    '    if bands and inherited_layout:\n',
    'cell=cut(value_box,y1,y2,right_bleed=True)',
    'value_cell=cut(val_box,right_bleed=True)',
    'expanded_cell=cut(val_box,right_bleed=True,vertical_bleed=2)',
    'still_implausible=(tentative is None)',
):
    assert required in src, required

# Once a page has been identified as a continuation, its preceding confirmed
# template must win even if OCR hallucinates a complete-looking header on that
# headerless page. Its outer table bounds must inherit too, because a headerless
# page may expose an extra left-side Field Crew column that the headed page omitted.
assert 'if can_inherit and not complete_header:' not in src
assert "complete_header=all(k in role_indices for k in ('up','down','value','date'))" not in src
assert 'if bands and not table and inherited_layout:' not in src
assert "Table layout could not be detected" not in src

tree=ast.parse(src)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_year15_recover_vertical_rules')
ns={'cv2':cv2,'np':np}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<v88-geometry>','exec'),ns)
recover=ns['_year15_recover_vertical_rules']

# Simulate the 8-24 page-4 failure mode: only some strong vertical rules survive
# the first detector, while the missing real rules are faint and interrupted at
# every horizontal row line. Repeated text strokes must not become columns.
img=np.full((900,1600,3),255,np.uint8)
left,right=120,1480
xs=[left,300,480,690,890,1080,1290,right]
bands=[]
y=150
for _ in range(15):
    y1,y2=y+4,y+30
    bands.append((y1,y2))
    y+=36
for x in (xs[0],xs[2],xs[5],xs[-1]):
    cv2.line(img,(x,140),(x,700),(0,0,0),3)
for x in (xs[1],xs[3],xs[4],xs[6]):
    for y1,y2 in bands:
        cv2.line(img,(x,y1),(x,y2),(225,225,225),3)
for fake_x in (380,575,780,980,1180,1380):
    for y1,y2 in bands:
        mid=(y1+y2)//2
        cv2.line(img,(fake_x,mid-4),(fake_x,mid+4),(0,0,0),2)

bounds=recover(img,bands,(left,right),[xs[0],xs[1],xs[2],xs[4],xs[-1]])
assert len(bounds)==8, bounds
for expected in xs:
    assert min(abs(actual-expected) for actual in bounds)<=5, (expected,bounds)

# A page whose first-pass detector already has every real boundary must stay
# unchanged even if repeated dark text strokes line up vertically across rows.
img2=np.full((900,1600,3),255,np.uint8)
for x in xs:
    cv2.line(img2,(x,140),(x,700),(0,0,0),3)
for fake_x in (340,390,530,735,1010,1240):
    for y1,y2 in bands:
        cv2.line(img2,(fake_x,y1),(fake_x,y2),(0,0,0),2)
full_bounds=recover(img2,bands,(left,right),xs)
assert full_bounds==xs, full_bounds

print('v88 exact-fixture continuation, partial-failure, faint-grid, and value-crop regression passed.')
