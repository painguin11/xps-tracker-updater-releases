from pathlib import Path

path=Path('working_source/app/reno_scan_updater.py')
text=path.read_text(encoding='utf-8')

old="""        if kind=='cleaning' and value_candidates:\n            value=_choose_cleaning_length(value_candidates,expected)\n            distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}\n            needs_consensus=(value is None or len(distinct)>1 or\n"""
new="""        if kind=='cleaning':\n            value=_choose_cleaning_length(value_candidates,expected)\n            distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}\n            needs_consensus=(not value_candidates or value is None or len(distinct)>1 or\n"""
if old not in text:
    raise SystemExit('Expected cleaning OCR branch not found')
text=text.replace(old,new,1)

# Keep the edit-dialog status concise when a work-order total is still unresolved.
old="""            length_warnings=sum(1 for rec in self.records if str(rec.get('status','')).startswith('LENGTH DIFF'))\n            other_warnings=sum(1 for rec in self.records if record_needs_review(rec) and not str(rec.get('status','')).startswith('LENGTH DIFF'))\n            if length_warnings or other_warnings:\n                bits=[]\n                if length_warnings: bits.append(f'{length_warnings} length difference warning(s) > {LENGTH_DIFF_THRESHOLD:.1f}')\n                if other_warnings: bits.append(f'{other_warnings} other row(s) need review')\n"""
new="""            length_warnings=sum(1 for rec in self.records if str(rec.get('status','')).startswith('LENGTH DIFF'))\n            total_failures=sum(1 for check in self.total_validations if not check.get('passed'))\n            other_warnings=sum(1 for rec in self.records if record_needs_review(rec) and not str(rec.get('status','')).startswith('LENGTH DIFF') and not any(str(w).startswith('TOTAL LENGTH') for w in rec.get('warnings',[])))\n            if length_warnings or total_failures or other_warnings:\n                bits=[]\n                if total_failures: bits.append(f'{total_failures} TOTAL LENGTH VALIDATION FAILURE(S) — UPDATE MASTER BLOCKED')\n                if length_warnings: bits.append(f'{length_warnings} length difference warning(s) > {LENGTH_DIFF_THRESHOLD:.1f}')\n                if other_warnings: bits.append(f'{other_warnings} other row(s) need review')\n"""
if old not in text:
    raise SystemExit('Expected edit status block not found')
text=text.replace(old,new,1)

path.write_text(text,encoding='utf-8')

regression=Path('working_source/tests/regression_length_totals.py')
rtext=regression.read_text(encoding='utf-8')
rtext=rtext.replace("assert 'needs_consensus=(value is None or len(distinct)>1' in source",
                    "assert 'needs_consensus=(not value_candidates or value is None or len(distinct)>1' in source")
regression.write_text(rtext,encoding='utf-8')
