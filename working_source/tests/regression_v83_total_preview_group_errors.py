from pathlib import Path

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')

# The total reader must retain the exact PDF value-cell pixels used as evidence.
assert "'preview':None" in src
assert "preview=cut(value_box,y1,y2)" in src
assert "'preview':preview.copy()" in src

# The verification UI is no longer a text-only simpledialog; it displays each
# available source-page total crop and returns the verified numeric value.
assert 'class TotalLengthVerifyDialog(tk.Toplevel):' in src
assert "PDF page {source.get('page','?')} printed total:" in src
assert 'ImageTk.PhotoImage(image,master=self)' in src
assert 'dlg=TotalLengthVerifyDialog(self,check,initial); self.wait_window(dlg)' in src

# Group-wide total failures get their own neutral/blank summary row instead of
# being appended to the first asset row.
assert 'def show_total_summary_error(self,check,follow=False):' in src
assert "values=('','','','',str(check.get('wo','')),'','',warning)" in src
assert "tags=('total_warning',)" in src
assert 'self.show_total_summary_error(check)' in src
assert '_total_warning_for_record_index' not in src
assert 'group_warning=' not in src
assert "if iid.startswith('group-error:'):" in src

# Pair parser is called with kind='pipes'; the suffix guard must use that same value.
assert "if kind=='pipes' and not match and match_status=='NEW PIPE':" in src
assert "if kind=='pipe' and not match and match_status=='NEW PIPE':" not in src

print('v83 total preview and group-error summary regression passed.')
