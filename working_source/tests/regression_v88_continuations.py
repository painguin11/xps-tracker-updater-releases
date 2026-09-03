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
):
    assert required in src, required

assert "Table layout could not be detected" not in src

tree=ast.parse(src)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_year15_recover_vertical_rules')
ns={'cv2':cv2,'np':np}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<v88-geometry>','exec'),ns)
recover=ns['_year15_recover_vertical_rules']

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
        cv2.line(img,(x,y1),(x,y2),(0,0,0),3)
for fake_x in (380,575,780,980,1180,1380):
    for y1,y2 in bands:
        mid=(y1+y2)//2
        cv2.line(img,(fake_x,mid-4),(fake_x,mid+4),(0,0,0),2)

bounds=recover(img,bands,(left,right),[xs[0],xs[2],xs[5],xs[-1]])
assert len(bounds)==8, bounds
for expected in xs:
    assert min(abs(actual-expected) for actual in bounds)<=5, (expected,bounds)

print('v88 continuation, partial-failure, and seven-column recovery regression passed.')
