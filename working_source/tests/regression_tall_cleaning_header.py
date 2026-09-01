import importlib.util
import os
import sys
import types
from pathlib import Path


sys.path.insert(0, str(Path('tmp/pydeps').resolve()))

# The production program uses Excel COM on Windows.  This layout regression
# exercises only PDF/OCR code, so provide inert modules on Linux.
win32com = types.ModuleType('win32com')
win32com_client = types.ModuleType('win32com.client')
win32com.client = win32com_client
sys.modules['win32com'] = win32com
sys.modules['win32com.client'] = win32com_client
sys.modules['pythoncom'] = types.ModuleType('pythoncom')
sys.modules['pywintypes'] = types.ModuleType('pywintypes')

source = Path('output/package_v69/XPS_Tracker_Updater/reno_scan_updater.py').resolve()
spec = importlib.util.spec_from_file_location('tracker_v69', source)
tracker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tracker)

doc = tracker.pymupdf.open('upload/8-11-2026.pdf')
page = doc[1]
_, rotation, text, kind = tracker.classify_for_profile(page, 'phase2_year1')
assert kind == 'cleaning', (kind, rotation, text[:500])
assert rotation == 270, rotation

pairs = [
    ('R2-280', 'R2-215', 369), ('R2-327', 'R2-280', 369),
    ('R2-281', 'R2-280', 314), ('R2-281S', 'R2-281', 2),
    ('R2-329', 'R2-327', 313), ('R2-338', 'R2-327', 72),
    ('R2-387', 'R2-407', 268), ('R2-386', 'R2-387', 400),
    ('R2-373', 'R2-387', 78), ('R2-375', 'R2-404', 345),
    ('R2-388', 'R2-404', 320), ('R2-330', 'R2-328', 291),
    ('R2-385', 'R2-383', 366), ('R2-384', 'R2-385', 350),
    ('R2-408', 'R2-384', 275), ('R2-421', 'R2-420', 224),
    ('R2-433', 'R2-421', 120),
]
pipe_items = []
pipes = {}
for row, (up, down, expected) in enumerate(pairs, 2):
    item = {
        'row': row, 'pipe_id': f'TEST-{row}', 'up': up, 'down': down,
        'up_key': tracker.asset_key(up), 'down_key': tracker.asset_key(down),
        'expected': float(expected),
    }
    pipe_items.append(item)
    pipes[(item['up_key'], item['down_key'])] = item
master = {'pipes': pipes, 'pipe_items': pipe_items, 'manholes': {}}
layout = tracker.prepare_year15_pair_layout(page, master, 'cleaning')
assert layout['table'], layout
assert len(layout['bands']) >= 18, len(layout['bands'])
assert len(layout['column_boxes']) == 10, len(layout['column_boxes'])
assert all(role in layout['role_indices'] for role in ('up', 'down', 'value', 'date')), layout
assert 'Field Crew' in layout['headers'][0], layout['headers']
assert 'UP_MH' in layout['headers'][1], layout['headers']
assert 'DN_MH' in layout['headers'][2], layout['headers']
assert 'Wheel Walk' in layout['headers'][8], layout['headers']
assert 'Cleaning' in layout['headers'][9] and 'Date' in layout['headers'][9], layout['headers']
assert layout['role_indices'] == {'up': 1, 'down': 2, 'value': 8, 'date': 9}, layout['role_indices']
assert layout['source'].startswith('header / '), layout['source']

rows = tracker.parse_year15_pair_list(page, master, 'cleaning', layout)
assert len(rows) == 17, [(r.get('up'), r.get('down'), r.get('status')) for r in rows]
assert all(not row.get('skip_update') for row in rows), rows
assert [(row['up'], row['down']) for row in rows] == [(up, down) for up, down, _ in pairs], rows
assert [row['video_length'] for row in rows] == [float(value) for _, _, value in pairs], rows
assert tracker.canonical_asset_id('R2-280') == 'R2-280'
assert tracker.canonical_asset_id('R2 280') == 'R2-280'
assert tracker.canonical_asset_id('DE-1234A') == 'DE-1234A'

print(
    'Tall cleaning header passed:',
    f"rotation={rotation}",
    f"bands={len(layout['bands'])}",
    f"columns={len(layout['column_boxes'])}",
    f"roles={layout['role_indices']}",
    f"rows={len(rows)}",
    f"lengths={[row['video_length'] for row in rows]}",
)
