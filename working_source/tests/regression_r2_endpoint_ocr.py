import importlib.util
import sys
import types
from pathlib import Path


source = Path("working_source/app/reno_scan_updater.py").resolve()
source_text=source.read_text(encoding='utf-8')
assert 'def _ocr_known_r2_candidates' in source_text
assert 'def parse_year15_pair_list' in source_text

pdf_path = Path(sys.argv[1] if len(sys.argv) > 1 else "../upload/8-17-2026(1).pdf")
if not pdf_path.exists():
    # Customer fixture PDFs are deliberately absent from the public repository.
    # Static current-source guards still run here; the OCR fixture remains runnable
    # locally by passing the PDF path explicitly.
    print('R2 fixture PDF unavailable; current-source R2 structural guards passed, fixture OCR skipped.')
    raise SystemExit(0)

sys.path.insert(0, str(Path("tmp/pydeps").resolve()))

# The production program uses Excel COM on Windows. This regression exercises
# only PDF/OCR code, so provide inert modules on Linux.
win32com = types.ModuleType("win32com")
win32com_client = types.ModuleType("win32com.client")
win32com.client = win32com_client
sys.modules["win32com"] = win32com
sys.modules["win32com.client"] = win32com_client
sys.modules["pythoncom"] = types.ModuleType("pythoncom")
sys.modules["pywintypes"] = types.ModuleType("pywintypes")

spec = importlib.util.spec_from_file_location("tracker_current", source)
tracker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tracker)

pairs = [
    ("R2-414", "R2-410", 71),
    ("R2-440S", "R2-440", 3),
    ("R2-440", "R2-414", 214),
    ("R2-427", "R2-414", 185),
    ("R2-439", "R2-427", 188),
    ("R2-417", "R2-427", 188),
    ("R2-419", "R2-417", 398),
    ("R2-420", "R2-419", 206),
    ("R2-382", "R2-410", 292),
    ("R2-381", "R2-382", 392),
]
pipe_items = []
pipes = {}
for row_number, (up, down, expected) in enumerate(pairs, 2):
    item = {
        "row": row_number,
        "pipe_id": f"R2-TEST-{row_number}",
        "up": up,
        "down": down,
        "up_key": tracker.asset_key(up),
        "down_key": tracker.asset_key(down),
        "expected": float(expected),
    }
    pipe_items.append(item)
    pipes[(item["up_key"], item["down_key"])] = item

# Number-only OCR for 417/427 is ambiguous when another prefix shares the same
# numeric portion. The focused recovery must still choose the printed R2 pair.
decoy = {
    "row": 50,
    "pipe_id": "DECOY",
    "up": "EC-417",
    "down": "EC-427",
    "up_key": tracker.asset_key("EC-417"),
    "down_key": tracker.asset_key("EC-427"),
    "expected": 999.0,
}
pipe_items.append(decoy)
pipes[(decoy["up_key"], decoy["down_key"])] = decoy

master = {"pipes": pipes, "pipe_items": pipe_items, "manholes": {}}
with tracker.pymupdf.open(pdf_path) as document:
    page = document[1]
    layout = tracker.prepare_year15_pair_layout(page, master, "cleaning")
    rows = tracker.parse_year15_pair_list(page, master, "cleaning", layout)

actual = [(row["up"], row["down"], row["video_length"]) for row in rows]
actual_pairs = {(up, down) for up, down, _ in actual}
for up, down, _ in pairs:
    assert (up, down) in actual_pairs, ((up, down), actual)

target_rows = {(row["up"], row["down"]): row for row in rows}
assert target_rows[("R2-427", "R2-414")]["video_length"] == 185.0
assert target_rows[("R2-417", "R2-427")]["video_length"] == 188.0
assert not target_rows[("R2-427", "R2-414")].get("skip_update")
assert not target_rows[("R2-417", "R2-427")].get("skip_update")

# A joined trailing letter remains a possible real new-asset suffix. Only the
# separated lowercase grid-rule artifact may recover the existing base ID.
dummy_cell = tracker.np.full((20, 80, 3), 255, dtype=tracker.np.uint8)
original_ocr = tracker.cached_ocr_string
try:
    for suffixed in ("R2-414A", "R2-414S"):
        tracker.cached_ocr_string = lambda *_args, value=suffixed, **_kwargs: value
        assert tracker._ocr_known_r2_candidates(dummy_cell, {"R2414": "R2-414"}) == []
    tracker.cached_ocr_string = lambda *_args, **_kwargs: "R2-414 r"
    assert tracker._ocr_known_r2_candidates(dummy_cell, {"R2414": "R2-414"}) == ["R2-414"]
finally:
    tracker.cached_ocr_string = original_ocr

assert all(not row.get("skip_update") for row in rows if row["up"].startswith("R2-")), rows
print("R2 endpoint OCR recovery passed against current source:", actual)
