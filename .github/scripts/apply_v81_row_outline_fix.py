from pathlib import Path

APP = Path('working_source/app/reno_scan_updater.py')
UPDATER = Path('working_source/app/xps_update.py')
README = Path('working_source/app/README_XPS_Tracker_Updater.txt')
TEST = Path('working_source/tests/regression_v81_header_outline.py')

src = APP.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global src
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count}')
    src = src.replace(old, new, 1)

replace_once("APP_VERSION = '80'", "APP_VERSION = '81'", 'app version')

replace_once(
    "    best={}; best_cells=[]\n",
    "    best={}; best_cells=[]; best_band_index=None\n",
    'track best header band',
)
replace_once(
    "        if len(found)>len(best): best,best_cells=dict(found),list(cells)\n"
    "        if all(x in found for x in ('up','down','value','date')):\n"
    "            if return_details: return found,cells,'header'\n",
    "        if len(found)>len(best):\n"
    "            best,best_cells,best_band_index=dict(found),list(cells),band_index\n"
    "        if all(x in found for x in ('up','down','value','date')):\n"
    "            if return_details: return found,cells,'header',band_index\n",
    'return detected header band',
)
replace_once(
    "    if return_details:\n"
    "        return (best or None),best_cells,'header' if all(x in best for x in ('up','down','value','date')) else 'incomplete header'\n",
    "    if return_details:\n"
    "        return (best or None),best_cells,'header' if all(x in best for x in ('up','down','value','date')) else 'incomplete header',best_band_index\n",
    'return partial header band',
)
replace_once(
    "    mapping,cells,source=_table_header_columns(img,bands,table,kind,column_bounds,return_details=True)\n",
    "    mapping,cells,source,header_band_index=_table_header_columns(img,bands,table,kind,column_bounds,return_details=True)\n",
    'receive header band',
)
replace_once(
    "            'source':source+' / '+geometry_source,'warnings':warnings,'fingerprint':fingerprint,\n"
    "            'master_pair_score':assisted_score,'master_pair_second':assisted_second}\n",
    "            'source':source+' / '+geometry_source,'warnings':warnings,'fingerprint':fingerprint,\n"
    "            'header_band_index':header_band_index,\n"
    "            'master_pair_score':assisted_score,'master_pair_second':assisted_second}\n",
    'store header band',
)
replace_once(
    "    for band_index,(y1,y2) in enumerate(bands):\n"
    "        if total_band_index is not None and band_index==total_band_index:\n",
    "    for band_index,(y1,y2) in enumerate(bands):\n"
    "        header_band_index=prepared.get('header_band_index')\n"
    "        if header_band_index is not None and band_index==header_band_index:\n"
    "            # Layout detection already proved this band contains the printed\n"
    "            # column headers. Never let OCR/master coincidence turn it into\n"
    "            # an asset row (for example a header accidentally resolving to\n"
    "            # a real master pair).\n"
    "            continue\n"
    "        if total_band_index is not None and band_index==total_band_index:\n",
    'skip structural header band',
)

replace_once(
    "    def _total_check_records(self,check):\n"
    "        return [(i,r) for i,r in enumerate(self.records)\n"
    "                if str(r.get('wo',''))==str(check.get('wo','')) and r.get('kind')==check.get('kind')]\n",
    "    def _total_check_records(self,check):\n"
    "        return [(i,r) for i,r in enumerate(self.records)\n"
    "                if str(r.get('wo',''))==str(check.get('wo','')) and r.get('kind')==check.get('kind')]\n"
    "    def _total_outline_records(self,check):\n"
    "        # The arithmetic check remains activity-specific, but the visual\n"
    "        # warning belongs to the entire work-order group.\n"
    "        return [(i,r) for i,r in enumerate(self.records)\n"
    "                if str(r.get('wo',''))==str(check.get('wo',''))]\n",
    'add whole-WO outline records',
)
replace_once(
    "            indexed=self._total_check_records(check)\n"
    "            if not indexed:\n"
    "                continue\n"
    "            visible=[]\n",
    "            indexed=self._total_outline_records(check)\n"
    "            if not indexed:\n"
    "                continue\n"
    "            visible=[]\n",
    'outline whole work order',
)
replace_once(
    "        thickness=max(2,self.spx(2)); color='#d00000'\n"
    "        tree_x=self.tree.winfo_x(); tree_y=self.tree.winfo_y(); tree_w=max(1,self.tree.winfo_width())\n",
    "        thickness=max(2,self.spx(2)); color='#d00000'\n"
    "        tree_w=max(1,self.tree.winfo_width())\n",
    'tree-local outline coordinates',
)
replace_once(
    "            y_top=tree_y+min(box[1] for _,box in visible)\n"
    "            y_bottom=tree_y+max(box[1]+box[3] for _,box in visible)\n"
    "            height=max(thickness,y_bottom-y_top)\n"
    "            specs=[(tree_x,y_top,thickness,height),(tree_x+tree_w-thickness,y_top,thickness,height)]\n",
    "            y_top=min(box[1] for _,box in visible)\n"
    "            y_bottom=max(box[1]+box[3] for _,box in visible)\n"
    "            height=max(thickness,y_bottom-y_top)\n"
    "            specs=[(0,y_top,thickness,height),(tree_w-thickness,y_top,thickness,height)]\n",
    'remove parent-coordinate offset',
)
replace_once(
    "                specs.append((tree_x,y_top,tree_w,thickness))\n"
    "            if any(i==last_index for i,_ in visible):\n"
    "                specs.append((tree_x,y_bottom-thickness,tree_w,thickness))\n"
    "            for x,y,width,line_height in specs:\n"
    "                frame=tk.Frame(self.table_frame,background=color,borderwidth=0,highlightthickness=0,takefocus=0)\n",
    "                specs.append((0,y_top,tree_w,thickness))\n"
    "            if any(i==last_index for i,_ in visible):\n"
    "                specs.append((0,y_bottom-thickness,tree_w,thickness))\n"
    "            for x,y,width,line_height in specs:\n"
    "                # Parent the border to the Treeview itself so bbox() and\n"
    "                # place() use the same coordinate system. This avoids the\n"
    "                # previous one-row vertical offset inside a LabelFrame.\n"
    "                frame=tk.Frame(self.tree,background=color,borderwidth=0,highlightthickness=0,takefocus=0)\n",
    'tree-owned outline frames',
)

APP.write_text(src, encoding='utf-8')

up = UPDATER.read_text(encoding='utf-8')
if 'CURRENT_VERSION = "80"' not in up:
    raise SystemExit('updater version marker not found')
UPDATER.write_text(up.replace('CURRENT_VERSION = "80"', 'CURRENT_VERSION = "81"', 1), encoding='utf-8')

readme = README.read_text(encoding='utf-8')
section = """

Version 81 structural header-row filtering and work-order outline
-----------------------------------------------------------------
- Carries the actual detected table-header band into pair-row parsing and excludes it before asset OCR/matching, preventing a header from becoming a false row even if OCR accidentally resolves it to a real master pair.
- Keeps printed total-row exclusion unchanged.
- Draws failed-total validation borders in Treeview-local coordinates so the top row is included correctly.
- Extends the visual total-validation border across the entire work-order group while leaving the arithmetic validation activity-specific.
"""
if 'Version 81 structural header-row filtering and work-order outline' not in readme:
    README.write_text(readme.rstrip() + section + '\n', encoding='utf-8')

TEST.write_text(r'''from pathlib import Path

src = Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
updater = Path('working_source/app/xps_update.py').read_text(encoding='utf-8')

assert "APP_VERSION = '81'" in src
assert 'CURRENT_VERSION = "81"' in updater

# The layout detector must identify the exact header band and preserve it in the
# prepared layout. The row parser then rejects that band before endpoint OCR.
assert 'best_band_index=None' in src
assert "return found,cells,'header',band_index" in src
assert "'header_band_index':header_band_index" in src
needle = "header_band_index=prepared.get('header_band_index')"
skip = "if header_band_index is not None and band_index==header_band_index:"
ocr = "up_obs=read_id(up_box,True); dn_obs=read_id(dn_box,True)"
assert needle in src and skip in src and ocr in src
assert src.index(needle) < src.index(ocr)
assert src.index(skip) < src.index(ocr)

# Total arithmetic remains activity-specific; only the visual border expands to
# the complete work-order group.
assert 'def _total_check_records(self,check):' in src
assert 'def _total_outline_records(self,check):' in src
assert "indexed=self._total_outline_records(check)" in src

# Treeview bbox coordinates and the border overlay now share one coordinate
# system. This prevents the old top-row/one-row vertical shift.
assert 'tree_x=self.tree.winfo_x()' not in src
assert 'tree_y=self.tree.winfo_y()' not in src
assert 'frame=tk.Frame(self.tree,background=color' in src
assert 'specs=[(0,y_top,thickness,height),(tree_w-thickness,y_top,thickness,height)]' in src

print('v81 structural header filtering and work-order outline regression passed.')
''', encoding='utf-8')

print('Applied v81 structural header-row and work-order outline fix.')
