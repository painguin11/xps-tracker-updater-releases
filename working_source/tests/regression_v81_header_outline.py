from pathlib import Path

src = Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

# This regression protects the v81 behavior on later releases; the application
# version itself is intentionally checked by each release's own validation.

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
