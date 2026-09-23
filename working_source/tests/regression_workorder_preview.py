from pathlib import Path
import importlib.util
import sys
import types

import fitz


ROOT = Path("/workspace/scratch/21e722c4daa5")
MODULE_PATH = ROOT / "output/package_v69/XPS_Tracker_Updater/reno_scan_updater.py"
PDF_PATH = ROOT / "upload/8-11-2026.pdf"

sys.path.insert(0, str(ROOT / "tmp/pydeps"))
win32com = types.ModuleType("win32com")
win32com_client = types.ModuleType("win32com.client")
win32com.client = win32com_client
sys.modules["win32com"] = win32com
sys.modules["win32com.client"] = win32com_client
sys.modules["pythoncom"] = types.ModuleType("pythoncom")
sys.modules["pywintypes"] = types.ModuleType("pywintypes")

spec = importlib.util.spec_from_file_location("reno_scan_updater_v69", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# This regression targets the preview geometry. Keep OCR deterministic so the
# test is independent of the Linux Tesseract build used by the test runner.
module.cached_ocr_string = lambda *_args, **_kwargs: "11976"

with fitz.open(PDF_PATH) as document:
    guesses = module.ocr_workorder_guesses(document[0], {"profile": "phase2_year1"})

preview = guesses["wo_preview"]
full_page = guesses["preview"]

expected_height = int(full_page.shape[0] * (0.090 - 0.043))
expected_width = int(full_page.shape[1] * (0.325 - 0.040))

assert guesses["wo"] == "11976", guesses["wo"]
assert abs(preview.shape[0] - expected_height) <= 1, preview.shape
assert abs(preview.shape[1] - expected_width) <= 1, preview.shape
assert preview.shape[1] > full_page.shape[1] * 0.28, preview.shape

print(
    f"Work-order preview passed: OCR={guesses['wo']} "
    f"preview={preview.shape[1]}x{preview.shape[0]}"
)
