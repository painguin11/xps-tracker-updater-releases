import importlib.util
import json
import os
import sys
import types

sys.path.insert(0, os.path.abspath('tmp/pydeps'))

win32com = types.ModuleType('win32com')
win32com.client = types.ModuleType('win32com.client')
sys.modules['win32com'] = win32com
sys.modules['win32com.client'] = win32com.client
sys.modules['pythoncom'] = types.ModuleType('pythoncom')
sys.modules['pywintypes'] = types.ModuleType('pywintypes')

path = os.path.abspath('output/package_v69/XPS_Tracker_Updater/reno_scan_updater.py')
spec = importlib.util.spec_from_file_location('updater', path)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
updater.pytesseract.pytesseract.tesseract_cmd = updater.find_tesseract()
doc = updater.pymupdf.open('upload/08_10_2026 Reno Work Orders.pdf')
work_order = {'wo': '12069', 'truck': 'ET01', 'operator': 'Anthony', 'date': None}
rows = [updater.parse_trouble_ticket(doc[i], i + 1, work_order,
        'upload/08_10_2026 Reno Work Orders.pdf') for i in range(4, 7)]
doc.close()
for row in rows:
    row['date'] = updater.fmt_date(row['date'])
print(json.dumps(rows, indent=2))
