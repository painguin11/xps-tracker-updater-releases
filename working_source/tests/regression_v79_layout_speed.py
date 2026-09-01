from pathlib import Path
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
