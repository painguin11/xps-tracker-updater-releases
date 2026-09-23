from pathlib import Path

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

for required in (
    'def ocr_workorder_guesses(page, master_index=None, expect_manhole_count=False):',
    "description_preview=crop(.035,.425,.72,.700)",
    "'expect_manhole_count':bool(expect_manhole_count)",
    "ttk.Label(self,text='Expected Manholes:')",
    "'expected_manhole_count':expected_manhole_count",
    "item['expects_manhole_count']=any(",
    "item['guesses']=ocr_workorder_guesses(item['page'],idx,item.get('expects_manhole_count',False))",
    'manhole_rows_by_wo={}',
    "manhole_rows_by_wo[wo_key]=manhole_rows_by_wo.get(wo_key,0)+int(report.get('rows') or 0)",
    'def show_manhole_count_summary(self,check):',
    'MANHOLE COUNT MISMATCH — EXPECTED',
    "manhole_count_failures=[check for check in self.manhole_count_validations if not check.get('passed')]",
    'Continue with only the readable rows?',
    'source=sources[-1]',
    "mode='final page printed work-order total'",
    "'sources':([selected_source] if selected_source else [])",
    'def cut(box,right_bleed=False,vertical_bleed=0,horizontal_bleed=0):',
    'cell=cut(box,horizontal_bleed=2); obs=_ocr_asset_candidates(cell,fast_plain=fast,asset_format=asset_format)',
):
    assert required in src, required

assert "mode='sum of printed page totals'" not in src
assert "mode='partial printed page totals'" not in src
print('v89 Manhole count, final-page total, and tight endpoint-crop safeguards passed.')
