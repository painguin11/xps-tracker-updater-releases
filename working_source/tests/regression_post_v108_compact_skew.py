"""Synthetic coverage for the guarded small-skew B&C compact grid retry."""
from pathlib import Path
import ast

import cv2
import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "app" / "reno_scan_updater.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
ns = {"cv2": cv2, "np": np}

for name in ("_year15_compact_grid_bands", "_year15_compact_skew_retry"):
    node = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), ns)

# The source must apply the guarded recovery before extracting OCR cells.
prepare = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
               and n.name == "prepare_year15_pair_layout")
assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
           and n.func.id == "_year15_compact_skew_retry"
           for n in ast.walk(prepare))

h, w = 1530, 1980
clean = np.full((h, w, 3), 255, dtype=np.uint8)
xs = np.linspace(130, 1845, 8).astype(int)
ys = np.linspace(125, 660, 17).astype(int)
for x in xs:
    cv2.line(clean, (int(x), int(ys[0])), (int(x), int(ys[-1])),
             (40, 40, 40), 2)
for i, y in enumerate(ys):
    # Mimic alternating thin/slightly stronger scanned row separators.
    thickness = 2 if i in (0, 1, 7, 8, 11, 13, 16) else 1
    cv2.line(clean, (int(xs[0]), int(y)), (int(xs[-1]), int(y)),
             (40, 40, 40), thickness)

# The normal horizontal/vertical printed grid must remain unchanged.
straight_bands, straight_table, straight_cols = ns["_year15_compact_grid_bands"](clean)
assert len(straight_bands) == 16, len(straight_bands)
unchanged = ns["_year15_compact_skew_retry"](
    clean, straight_bands, straight_table, straight_cols)
assert unchanged[4] is False
assert unchanged[0] is clean
assert unchanged[1] == straight_bands

# About 0.6 degrees of physical scanner skew destroys most long horizontal
# morphology detections even though the 8 long vertical rules remain readable.
matrix = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), -0.6, 1.0)
skewed = cv2.warpAffine(clean, matrix, (w, h),
                        borderMode=cv2.BORDER_CONSTANT,
                        borderValue=(255, 255, 255))
broken_bands, broken_table, broken_cols = ns["_year15_compact_grid_bands"](skewed)
assert broken_table is not None and len(broken_cols) == 8
assert len(broken_bands) < len(straight_bands) - 2, len(broken_bands)

corrected, bands, table, columns, changed = ns["_year15_compact_skew_retry"](
    skewed, broken_bands, broken_table, broken_cols)
assert changed is True, (len(broken_bands), len(bands))
assert len(bands) == len(straight_bands), (len(bands), len(straight_bands))
assert len(columns) == 8
assert abs((table[1] - table[0]) - (straight_table[1] - straight_table[0])) < 25

# Do not manufacture a table or retry a blank/non-grid page.
blank = np.full((h, w, 3), 255, dtype=np.uint8)
assert ns["_year15_compact_grid_bands"](blank) == ([], None, None)
assert ns["_year15_compact_skew_retry"](
    blank, [], None, None)[4] is False

print("post-v108 compact small-skew row recovery regression passed")
