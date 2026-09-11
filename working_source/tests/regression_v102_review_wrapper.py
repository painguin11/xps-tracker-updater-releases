from pathlib import Path

root=Path(__file__).resolve().parents[1]
wrapper=(root/'app'/'xps_review_controls.py').read_text(encoding='utf-8')
launcher=(root/'app'/'run_xps_tracker.bat').read_text(encoding='utf-8')
setup=(root/'app'/'setup_and_run.bat').read_text(encoding='utf-8')
core=(root/'app'/'reno_scan_updater.py').read_text(encoding='utf-8')

# The review extension is additive: OCR/parser implementation remains in the
# existing v101 core and both launch paths enter the extension.
assert "APP_VERSION = '101'" in core
assert 'xps_review_controls.py' in launcher
assert 'xps_review_controls.py' in setup
assert '"%VPY%" reno_scan_updater.py' not in launcher
assert '"%VPY%" reno_scan_updater.py' not in setup
assert 'class App(base.App):' in wrapper
assert 'base.ConfirmDialog=EnhancedConfirmDialog' in wrapper

# The Manhole-count confirmation image is substantially larger than the normal
# field thumbnails so small handwritten counts remain readable.
assert 'image.thumbnail((720,300),Image.Resampling.LANCZOS)' in wrapper

# Manual whole-W/O review uses its own multi-select dialog; row editing remains
# the original single-row Treeview behavior in the core.
assert 'selectmode=tk.EXTENDED' in wrapper
assert "text='Discard Work Order(s)'" in wrapper
assert "selectmode='browse'" in core

# Update Master exposes all three requested outcomes for non-green work orders.
for token in ('Ignore Problem Work Orders & Continue','Continue Current Review Flow','Back to Review'):
    assert token in wrapper, token
assert 'if not self.resolve_problem_work_orders_for_update(): return' in wrapper
assert 'return super().update_master()' in wrapper

# Discarding a work order removes every in-memory collection that could later
# write it or leave a validation blocker behind.
method=wrapper[wrapper.index('    def _discard_work_order_set(self,work_orders):'):
               wrapper.index('\n    def _rebuild_review_tree',wrapper.index('    def _discard_work_order_set(self,work_orders):'))]
for token in (
    'self.records=[item for item in self.records if not belongs(item)]',
    'self.trouble_tickets=[item for item in self.trouble_tickets if not belongs(item)]',
    'self.groups=[item for item in self.groups if not belongs(item)]',
    'self.total_validations=[item for item in self.total_validations if not belongs(item)]',
    'self.manhole_count_validations=[item for item in self.manhole_count_validations if not belongs(item)]',
    'self.unprocessed_pages=[item for item in self.unprocessed_pages if not belongs(item)]',
):
    assert token in method, token

# Problem-W/O detection covers all visible reasons that prevent a W/O from being
# fully green/ready before Update Master.
problem=wrapper[wrapper.index('    def _problem_work_orders(self):'):
                wrapper.index('\n    def _discard_work_order_set',wrapper.index('    def _problem_work_orders(self):'))]
for token in ('base.record_needs_review(record)','base.trouble_ticket_status(ticket)',
              'self.total_validations','self.manhole_count_validations','self.unprocessed_pages'):
    assert token in problem, token

print('v102 review wrapper regression passed')
