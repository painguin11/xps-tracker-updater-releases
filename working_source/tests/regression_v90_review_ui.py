from pathlib import Path
s=(Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py').read_text(encoding='utf-8')
d=s[s.index('class UnmatchedAssetDecisionDialog'):s.index('\n\nclass App',s.index('class UnmatchedAssetDecisionDialog'))]
for x in ('PDF ID verification',"'upstream'","'downstream'","'asset'",'ImageTk.PhotoImage(image,master=self)',"text='Add to Master'","text='Ignore'","text='Back to Summary'"): assert x in d,x
r=s[s.index('    def _refresh_record_rows_only(self):'):s.index('\n    def _pipe_duplicate_groups',s.index('    def _refresh_record_rows_only(self):'))]
for x in ('vertical_position=self.tree.yview()[0]','selected=list(self.tree.selection())','focused=self.tree.focus()','self.tree.selection_set(surviving)','self.tree.focus(focused)','self.tree.yview_moveto(vertical_position)'): assert x in r,x
assert r.index('vertical_position=self.tree.yview()[0]') < r.index('self.tree.delete(iid)')
assert r.index('self.tree.yview_moveto(vertical_position)') > r.index('self.show_total_summary_error(check)')
print('v90 review UI regression passed')
