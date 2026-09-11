from pathlib import Path

SOURCE = Path('working_source/app/reno_scan_updater.py')
PROJECT = Path('PROJECT_CONTEXT.md')
CHECKLIST = Path('RELEASE_CHECKLIST.md')

source = SOURCE.read_text(encoding='utf-8')

old_below = """        below=[b for b in boxes if 0<=b[1]-y2<h*.018\n               and abs(b[0]-x1)<w*.018 and abs(b[2]-x2)<w*.018]\n        if below:\n            fields[key]=min(below,key=lambda b:b[1])\n"""
new_below = """        # Perspective/skew in scanned forms can make the next ruled cell's\n        # contour begin a few pixels above the label cell's lowest point. Allow\n        # only a tiny bounded overlap and still require both horizontal edges to\n        # align, then choose the boundary nearest the label. This keeps generic\n        # grids fail-closed while preserving real adjacent label/value pairs.\n        below=[b for b in boxes if -h*.006<=b[1]-y2<h*.018\n               and abs(b[0]-x1)<w*.018 and abs(b[2]-x2)<w*.018]\n        if below:\n            fields[key]=min(below,key=lambda b:abs(b[1]-y2))\n"""
if old_below in source:
    source = source.replace(old_below, new_below, 1)
elif new_below not in source:
    raise SystemExit('ticket label/value geometry block not found')

old_desc = """        if key=='description':\n            value=re.sub(r'\\s+',' ',value).strip()\n            return re.sub(r'\\bDescription\\s*[:;]?\\s*','',value,count=1,flags=re.I).strip()\n"""
new_desc = """        if key=='description':\n            value=re.sub(r'\\s+',' ',value).strip()\n            value=re.sub(r'\\bDescription\\s*[:;]?\\s*','',value,count=1,flags=re.I).strip()\n            # Rule-removal artifacts can leave punctuation ahead of the first\n            # real word. Remove only leading non-content debris so legitimate\n            # terminal punctuation remains intact.\n            return re.sub(r'^[^A-Za-z0-9]+','',value).strip()\n"""
if old_desc in source:
    source = source.replace(old_desc, new_desc, 1)
elif new_desc not in source:
    raise SystemExit('ticket description cleanup block not found')

SOURCE.write_text(source, encoding='utf-8')

project = PROJECT.read_text(encoding='utf-8')
project_marker = """- Production remains v100. This fix is unreleased; await explicit `PUBLISH`.\n"""
project_add = project_marker + """\nFollow-up validation for the 8-26 B&C Trouble Ticket scan variation:\n\n- Adjacent ruled label/value cells may overlap vertically by a few pixels after\n  perspective/skew in the scan. The detector now accepts only a tightly bounded\n  overlap (0.6% of page height), still requires both horizontal edges to align,\n  and selects the closest adjacent boundary. Generic/partial grids remain\n  fail-closed.\n- Leading non-alphanumeric OCR debris is removed from descriptions after the\n  printed `Description` label is stripped; legitimate ending punctuation is\n  preserved.\n- Permanent regression: `working_source/tests/regression_post_v100_826_trouble_geometry.py`.\n- Local private validation on the two Trouble Ticket pages in the supplied 8-26\n  packet produced the expected ticket fields with the detected-cell path. The\n  private PDF and expected customer values remain uncommitted.\n"""
if 'regression_post_v100_826_trouble_geometry.py' not in project:
    if project_marker not in project:
        raise SystemExit('PROJECT_CONTEXT trouble-ticket marker not found')
    project = project.replace(project_marker, project_add, 1)
    PROJECT.write_text(project, encoding='utf-8')

checklist = CHECKLIST.read_text(encoding='utf-8')
check_marker = """- `working_source/tests/regression_post_v100_trouble_cells.py`\n"""
check_add = check_marker + """- `working_source/tests/regression_post_v100_826_trouble_geometry.py`\n"""
if 'regression_post_v100_826_trouble_geometry.py' not in checklist:
    if check_marker not in checklist:
        raise SystemExit('RELEASE_CHECKLIST trouble regression marker not found')
    checklist = checklist.replace(check_marker, check_add, 1)
    CHECKLIST.write_text(checklist, encoding='utf-8')

print('Applied bounded Trouble Ticket scan-skew geometry and description cleanup fix.')
