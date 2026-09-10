from pathlib import Path
import ast
import cv2
import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'app' / 'reno_scan_updater.py'
s = SOURCE.read_text(encoding='utf-8')
tree = ast.parse(s)

assert 'faint_inv=cv2.threshold(cgray,240,255,cv2.THRESH_BINARY_INV)[1]' in s
assert 'max_span>=bh*.75 and x_span>=bw*.70' in s

# Reproduce the geometry class from the 9/9/2026 image-only Phase 2 packet
# without retaining any customer data.  After the correct 90-degree orientation,
# the table spans almost the entire page width.  Its horizontal rules and outer
# border are dark, but the interior vertical rules are lighter than the normal
# 225 compact-grid threshold.  The established dark passes therefore see only
# the two outer borders and used to reject the table before header OCR.
ns = {'cv2': cv2, 'np': np}
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name == '_year15_compact_grid_bands')
exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), ns)

def make_faint_grid():
    h, w = 1530, 1980
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    left, right = 40, 1925
    top, bottom = 150, 535
    xs = [40, 309, 578, 847, 1116, 1385, 1654, 1925]
    ys = [150, 185, 215, 245, 275, 304, 333, 362, 392, 420, 449, 479, 506, 535]

    # Dark outer box and horizontal rules keep the connected table region clear.
    cv2.line(img, (left, top), (left, bottom), (205, 205, 205), 2)
    cv2.line(img, (right, top), (right, bottom), (205, 205, 205), 2)
    for y in ys:
        cv2.line(img, (left, y), (right, y), (205, 205, 205), 2)

    # Interior rules are intentionally just beyond the established 225 cutoff.
    for x in xs[1:-1]:
        cv2.line(img, (x, top), (x, bottom), (238, 238, 238), 2)
    return img, xs

img, expected_xs = make_faint_grid()
bands, table, xs = ns['_year15_compact_grid_bands'](img)
assert table is not None, (bands, table, xs)
assert xs is not None and len(xs) == 8, xs
assert len(bands) == 13, bands
assert abs(table[0] - expected_xs[0]) <= 5, table
assert abs(table[1] - expected_xs[-1]) <= 5, table
for actual, expected in zip(xs, expected_xs):
    assert abs(actual - expected) <= 5, (xs, expected_xs)

# Keep the lighter retry fail-closed.  Repeated faint short strokes can resemble
# columns, but they do not span most of the isolated region and must not turn a
# non-table area into valid compact geometry.
noise = np.full((1530, 1980, 3), 255, dtype=np.uint8)
cv2.rectangle(noise, (40, 150), (1925, 535), (205, 205, 205), 2)
for x in expected_xs[1:-1]:
    for y in range(180, 500, 70):
        cv2.line(noise, (x, y), (x, y + 18), (238, 238, 238), 2)
noise_bands, noise_table, noise_xs = ns['_year15_compact_grid_bands'](noise)
assert noise_bands == [] and noise_table is None and noise_xs is None, (
    noise_bands, noise_table, noise_xs)

print('post-v99 faint vertical-grid regression passed')
