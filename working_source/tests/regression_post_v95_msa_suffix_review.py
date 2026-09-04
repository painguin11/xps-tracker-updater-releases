from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')

# MSA confirmation must show the actual two physical PDF rows, including the
# endpoint IDs and each row's length crop.
start=s.index('class MsaConfirmDialog(tk.Toplevel):')
end=s.index('\n\nclass NewAssetApprovalDialog',start)
dialog=s[start:end]
for required in (
    "self.crop_photos=[]",
    "PDF MSA verification",
    "add_part(0,'Part 1',first)",
    "add_part(1,'Part 2',second)",
    "'upstream'",
    "'downstream'",
    "'activity_value'",
    "ImageTk.PhotoImage(image,master=self)",
    "text='Confirm MSA'",
    "text='Not MSA'",
):
    assert required in dialog, required

# Saying Not MSA is a durable decision, but the Live Summary/Edit Selected path
# must make it obvious and possible to reverse without re-analyzing the PDF.
assert "NOT MSA — EDIT ROW TO CHANGE DECISION" in s
assert 'def _msa_pair_indices_for_record(self,index):' in s
assert 'def review_msa_for_record(self,index,parent=None):' in s
assert "self.status.set('MSA decision changed: the two Pipe rows are now combined.')" in s
assert "text='Review / Change MSA Decision'" in s

edit_helper_start=s.index('def apply_manual_asset_edit')
edit_helper_end=s.index('\ndef ',edit_helper_start+5)
edit_helper=s[edit_helper_start:edit_helper_end]
# A no-op Edit/Save must not silently erase the user's Not-MSA choice. Identity
# or length changes are allowed to clear it so the pair can be reconsidered.
assert "record.pop('_msa_rejected',None)\n    def clear_asset_decision_if_changed" not in edit_helper
identity_clear=edit_helper.index("record.pop('_msa_rejected',None)")
identity_guard=edit_helper.index('if new_identity==old_identity:')
assert identity_clear>identity_guard

# A complete printed NEW PIPE suffix is higher-quality evidence than lossy R2,
# numeric-body, or slow fallback OCR. Those fallbacks must not erase the suffix
# before the existing independent suffix confirmation has had a chance to verify it.
pair_start=s.index('def parse_year15_pair_list')
pair_end=s.index('\ndef parse_year15_manholes',pair_start)
pair=s[pair_start:pair_end]
for comment in (
    '# Some clean R2 prefixes are consistently read as 2/22/32/52.',
    '# If grid/prefix damage erased EC/DN/R2 but both endpoint numbers are',
    '# Escalate only uncertain endpoint cells to the slower OCR ensemble.',
):
    pos=pair.index(comment)
    condition=pair.rfind("if not match and match_status!='NEW PIPE':",0,pos)
    assert condition>=0, comment
    # Make sure it is the immediately preceding fallback guard, not a distant one.
    assert pos-condition<500, comment

suffix_guard=pair.index("if kind=='pipes' and not match and match_status=='NEW PIPE':")
assert suffix_guard>pair.index('# Escalate only uncertain endpoint cells to the slower OCR ensemble.')
assert '_confirmed_suffix_asset_candidates' in pair[suffix_guard:suffix_guard+1800]
assert '_guard_unconfirmed_suffix_observations' in pair[suffix_guard:suffix_guard+1800]

# Existing conservative behavior remains in place.
assert '_resolve_pipe_pair_from_endpoint_digits' in pair
assert "match_status='Matched'" in pair
assert "DUPLICATE_PIPE_REVIEW = 'Duplicate pipe - check IDs'" in s
assert "if pipe_group_physical_count(records)>=3:" in s

print('Post-v95 MSA preview/reversal and NEW PIPE suffix-priority regression passed.')
