"""Live Summary stays plain until the analysis completes; no OCR fixtures needed."""
from pathlib import Path
import ast

source=(Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py').read_text(encoding='utf-8')
tree=ast.parse(source)
app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App')
methods={n.name:n for n in app.body if isinstance(n,ast.FunctionDef)}
def excerpt(name):
    return ast.get_source_segment(source,methods[name])

class Tree:
    def __init__(self): self.items={}; self.seen=[]
    def exists(self,iid): return iid in self.items
    def item(self,iid,values=(),tags=()): self.items[iid]=(values,tags)
    def insert(self,parent,where,iid,values,tags=()): self.items[iid]=(values,tags)
    def see(self,iid): self.seen.append(iid)

def preview(running):
    ns={'review_status':lambda r:'LENGTH DIFF; CHECK ID',
        'record_needs_review':lambda r:True,
        '_format_pdf_number':str,'fmt_date':str}
    exec(compile(ast.Module(body=[methods['show_summary_record']],type_ignores=[]),
                 'reno_scan_updater.py','exec'),ns)
    class Fake:
        show_summary_record=ns['show_summary_record']
        def _schedule_total_outlines(self): pass
        def pump_analysis_ui(self): pass
        def update_idletasks(self): pass
    app=Fake();app.tree=Tree();app._analysis_running=running
    app.records=[dict(kind='Pipe',display_asset='DN-1 -> DN-2',video_length=120.5,
                      date='10/12/2026',wo='12345',truck='CT01',operator='A B',
                      status='LENGTH DIFF 9.0',warnings=['CHECK ID'])]
    app.show_summary_record(0)
    return app.tree.items['record:0']

running,tags=preview(True)
assert running[-1]=='' and tags==(),(running,tags)
completed,tags=preview(False)
assert completed[-1] and tags==('length_warning',),(completed,tags)
for name in ('show_summary_ticket','refresh_unprocessed_summary',
             'show_manhole_count_summary','show_total_summary_error',
             '_draw_total_outlines'):
    assert '_analysis_running' in excerpt(name),name
assert "visible_status='' if getattr(self,'_analysis_running',False) else status" in excerpt('show_summary_ticket')
analysis=excerpt('analyze')
assert analysis.index('self.stop_analysis_animation()')<analysis.index('self.refresh_unprocessed_summary()')
assert analysis.index('self.refresh_unprocessed_summary()')<analysis.index('self.show_summary_record(i)')
assert 'for check in self.manhole_count_validations:' in analysis
assert 'for check in self.total_validations:' in analysis
print('Live Summary progressive plain rows / final review restoration regression passed')
