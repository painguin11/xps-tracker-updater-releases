from pathlib import Path
import ast
import cv2
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')
tree=ast.parse(s)

assert 'short_wide_region=ww>=w*.70 and hh>=h*.055' in s

# Pipe and Cleaning share the same pair-table grid detector. Reproduce the
# geometry class without customer data: after rotation the table is almost
# full-page width but only about 8% of page height because it contains a header,
# two data rows, and a total row. The old 12%-height gate rejected this before
# the existing grid/header safeguards could inspect it.
ns={'cv2':cv2,'np':np}
compact_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_year15_compact_grid_bands')
exec(compile(ast.Module(body=[compact_node],type_ignores=[]),str(SOURCE),'exec'),ns)

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

# Guard the fact that Pipe and Cleaning hit the same grid detector before any
# type-specific header-role logic. A future refactor must not quietly restore a
# different minimum-height rule for Cleaning.
pair_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='prepare_year15_pair_layout')
grid_calls=[n for n in ast.walk(pair_node)
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
            and n.func.id=='_year15_grid_bands']
assert grid_calls,'prepare_year15_pair_layout no longer uses the shared Year 15 grid detector'
grid_line=min(n.lineno for n in grid_calls)
kind_if_lines=[]
for n in ast.walk(pair_node):
    if not isinstance(n,ast.If):
        continue
    if any(isinstance(x,ast.Name) and x.id=='kind' for x in ast.walk(n.test)):
        kind_if_lines.append(n.lineno)
assert not kind_if_lines or grid_line<min(kind_if_lines),(grid_line,kind_if_lines)

# Manholes intentionally use a separate positioned-token parser instead of the
# pair-table compact-grid gate. Exercise a one-row synthetic Manhole report so
# row count/table height can never become an implicit requirement there either.
class _CV2Stub:
    COLOR_RGB2GRAY=1
    @staticmethod
    def cvtColor(image,code):
        return image

class _OutputStub:
    DICT='DICT'

class _TesseractStub:
    Output=_OutputStub
    @staticmethod
    def image_to_data(image,config='',output_type=None):
        return {
            'text':['MH-1001','9/1/2026'],
            'left':[40,650],
            'top':[200,200],
            'height':[20,20],
        }

mh_img=np.full((1000,800,3),255,dtype=np.uint8)

def _parse_date_text(value):
    return '09/01/2026' if str(value).strip()=='9/1/2026' else None

def _printed_asset_tokens(value,asset_format):
    value=str(value).strip().upper()
    return [value] if value=='MH-1001' else []

def _resolve_full_asset(values,known):
    if values and values[0]=='MH-1001':
        return ({'asset':'MH-1001','asset_key':'MH1001'},'Matched')
    return (None,'NOT MATCHED')

mh_ns={
    'cv2':_CV2Stub,
    'pytesseract':_TesseractStub,
    '_year15_oriented':lambda page,kind,preferred_deg=None: mh_img,
    'parse_date_text':_parse_date_text,
    '_printed_asset_tokens':_printed_asset_tokens,
    '_resolve_full_asset':_resolve_full_asset,
    '_best_observed_asset_id':lambda values,known: None,
    'canonical_asset_id':lambda value: str(value).strip().upper(),
    '_table_row_bands':lambda *args,**kwargs: ([],None),
}
mh_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_year15_manholes')
exec(compile(ast.Module(body=[mh_node],type_ignores=[]),str(SOURCE),'exec'),mh_ns)
rows=mh_ns['parse_year15_manholes'](
    object(),
    {'asset_format':{'mode':'prefixed_dash'},'manholes':{'MH1001':{'asset':'MH-1001'}}},
)
assert len(rows)==1,rows
assert rows[0]['asset']=='MH-1001',rows
assert rows[0]['status']=='Matched',rows
assert rows[0]['row_date']=='09/01/2026',rows

print('post-v98 short Pipe/Cleaning/Manhole table regression passed')
