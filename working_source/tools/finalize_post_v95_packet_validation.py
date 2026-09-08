from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "working_source/app/reno_scan_updater.py"
TEST = ROOT / "working_source/tests/regression_post_v95_new_packet_ocr.py"
CONTEXT = ROOT / "PROJECT_CONTEXT.md"
CHECKLIST = ROOT / "RELEASE_CHECKLIST.md"


def replace_once(path, old, new):
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise RuntimeError(f"Expected patch anchor missing in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


# 1) A detected compact table with usable column geometry must reach the existing
# Layout Review even when only some roles were OCR-mapped. The parser itself
# already fails closed on incomplete roles; the old application-flow gate skipped
# the page before review could be offered.
old_gate = """                    roles=layout.get('role_indices',{})
                    if (not layout.get('column_boxes') or
                            not all(role in roles for role in ('up','down','value','date'))):
                        self.add_unprocessed_page(wo,pi+1,kind,'table layout could not be resolved safely')
                        item['skip_processing']=True
                        continue
"""
new_gate = """                    roles=layout.get('role_indices',{})
                    # A detected table with usable column geometry must be allowed
                    # into the existing Layout Review flow even when OCR mapped only
                    # some roles. Only missing table geometry is unsafe to review.
                    if not layout.get('column_boxes'):
                        self.add_unprocessed_page(wo,pi+1,kind,'table layout could not be resolved safely')
                        item['skip_processing']=True
                        continue
"""
replace_once(APP, old_gate, new_gate)


# 2) Strengthen the permanent new-packet regression with direct executable cases
# for the compact partial-layout path and the Pipe 250 -> 260 total-audit guard.
test = TEST.read_text(encoding="utf-8")
if '"if not layout.get(\'column_boxes\'):"' not in test:
    anchor = '    "preferred_deg=item.get(\'effective_deg\'))",\n):'
    repl = '    "preferred_deg=item.get(\'effective_deg\'))",\n    "if not layout.get(\'column_boxes\'):",\n):'
    if anchor not in test:
        raise RuntimeError("Regression source-check anchor missing")
    test = test.replace(anchor, repl, 1)

if "synthetic worse OCR" not in test:
    block = r'''

# Partial role mappings must remain safe and reviewable rather than raising a
# KeyError or being treated as a fully parsed row before review.
import numpy as np
partial_prepared={
    'img':np.zeros((120,240),dtype=np.uint8),
    'bands':[(20,40),(40,60)],
    'table':(10,230),
    'mapping':{'up':(0.0,0.25),'down':(0.25,0.50)},
    'header_band_index':0,
}
partial=xps.parse_year15_pair_list(None,{'asset_format':{}},'cleaning',prepared=partial_prepared)
assert len(partial)==1 and partial[0]['asset']=='COLUMN HEADERS NOT RESOLVED',partial
assert partial[0]['skip_update'] is True,partial
assert "not all(role in roles for role in ('up','down','value','date'))" not in s

# A whole-table Pipe audit must not replace an already-valid 250 with a worse
# independently observed 260 when doing so increases the printed-total mismatch.
d2=Dummy(); d2.records=[
    {'wo':'P','kind':'Pipe','video_length':250.0,'master_length':250.0,
     '_length_value_cell':'pipe-sentinel'},
    {'wo':'P','kind':'Pipe','video_length':100.0,'master_length':100.0,
     '_length_value_cell':'other-sentinel'},
]
d2._total_check_records=types.MethodType(xps.App._total_check_records,d2)
orig=xps._independent_row_length_read
try:
    def fake_pipe(cell,*_a,**_k):
        if cell=='pipe-sentinel':
            return {'value':260.0,'confident':True,'source':'synthetic worse OCR','candidates':[260.0]}
        return {'value':100.0,'confident':True,'source':'synthetic same OCR','candidates':[100.0]}
    xps._independent_row_length_read=fake_pipe
    check={'wo':'P','kind':'Pipe','pdf_total':355.0,'pdf_total_confident':True}
    changed=xps.App._retry_length_total_mismatch(d2,check,all_rows=True,force=True)
    assert not changed,d2.records
    assert d2.records[0]['video_length']==250.0,d2.records
    assert d2.records[0].get('_length_crosscheck_conflict')==260.0,d2.records
finally:
    xps._independent_row_length_read=orig
'''
    marker = "\nprint('Post-v95 new packet OCR/direction/total safeguards regression passed.')"
    if marker not in test:
        raise RuntimeError("Regression final print anchor missing")
    test = test.replace(marker, block + marker, 1)
TEST.write_text(test, encoding="utf-8")


# 3) Update canonical project context with the tested post-v95 safeguards and the
# exact private-fixture expectations. Customer files themselves remain local.
context = CONTEXT.read_text(encoding="utf-8")
if "Observed-value length reconciliation for new Phase 2 packets" not in context:
    anchor = """   - The existing suffix/new-asset and ambiguity review rules still decide whether
     an observed ID is matched, NEW PIPE, or unresolved.

Functional source commits for these changes:
"""
    insert = """   - The existing suffix/new-asset and ambiguity review rules still decide whether
     an observed ID is matched, NEW PIPE, or unresolved.
4. **Observed-value length reconciliation for new Phase 2 packets**
   - Cleaning mismatch recovery keeps batch and independent cell OCR as actual PDF
     observations; the master may break ties between observed values but never
     manufactures a measurement.
   - Targeted rereads remain limited to suspect/mismatch rows instead of rereading
     every Cleaning cell.
   - Pipe mismatch recovery includes the lower-scale alternate view that can
     recover values such as `323.72` when another view reads `393.72`.
   - A whole-table Pipe audit cannot replace an already-valid value with a different
     OCR observation unless the replacement reduces the printed-total mismatch and
     also improves master plausibility, unless it closes the printed total exactly.
5. **Digit-bearing R2 direction protection**
   - Explicit IDs such as `R2-491` retain the `R2` prefix instead of being parsed as
     prefix `R` plus numeric body `2491`.
   - Complete printed upstream/downstream direction is authoritative; a synthetic
     reverse-master alias cannot turn the opposite printed direction into an exact
     match.
6. **Compact partial-header review safety**
   - If table geometry/column boxes are detected but OCR maps only some required
     roles, the page enters the existing Layout Review instead of being skipped or
     raising a missing-role exception.
   - Only pages without usable table geometry are skipped as structurally unsafe.
7. **Faint compact row separators remain protected**
   - The v95 faint/interrupted separator recovery remains active and is covered by
     its permanent regression plus the new 8-25 real-PDF check.

Functional source commits for these changes:
"""
    if anchor not in context:
        raise RuntimeError("PROJECT_CONTEXT unreleased-change anchor missing")
    context = context.replace(anchor, insert, 1)

if "`regression_post_v95_new_packet_ocr.py`" not in context:
    anchor = """- `working_source/tests/regression_post_v95_msa_suffix_review.py`
- `working_source/tests/regression_post_v95_padded_endpoint_ids.py`
"""
    repl = anchor + "- `working_source/tests/regression_post_v95_new_packet_ocr.py`\n"
    if anchor not in context:
        raise RuntimeError("PROJECT_CONTEXT regression-list anchor missing")
    context = context.replace(anchor, repl, 1)

if "8-20 Manholes: 20/20" not in context:
    marker = "\nExact customer documents remain private even when these expected counts/totals\nare documented.\n"
    block = r'''

Additional post-v95 Phase 2 packet expectations verified against the supplied
Phase 2 Year 1 master, with Trouble Tickets intentionally out of scope:

- 8-20 Manholes: 20/20.
- 8-20 Cleaning: 27 normal printed rows / 5690 exact; difficult printed values
  finish as 56, 171, and 47 from PDF-observed rereads.
- 8-21 Pipe page 2: 22 rows / 6408.66 exact. The difficult values include
  431.36, 300.95, 315.58, 168.86, 375.89, 323.72, and 325.89. An already-correct
  250 must remain 250 during the final whole-table audit rather than being
  replaced by a worse 260 observation.
- 8-21 Cleaning page 4: 23 normal printed rows / 3926. One known non-table anomaly
  in this private fixture is excluded from the fixture expectation only; it must
  not create a generic parser/filtering rule.
- 8-21 Cleaning page 6: 14 rows / 3724.
- 8-21 Cleaning page 8: 12 rows / 3180. Compact-header role detection/layout
  review must not crash or skip a detected table with usable column geometry.
- 8-21 Manholes page 10: 27/27.
- 8-25 Pipe page 2: 12 physical rows / 2803.46 exact. Printed
  `R2-491 -> R2-489 = 53.22` remains NOT MATCHED when the master only contains the
  opposite direction.
- 8-25 Cleaning page 4: 5 rows / 1220.
- 8-25 Cleaning page 6: 20 rows / 4821; `EC-1507 -> EC-1477` remains 110 rather
  than accepting the worse alternate OCR observation 1101.
- 8-27 first Pipe table: 34 rows / 5164.64.
- 8-27 Manholes: 3/3.
- 8-27 later Pipe table: 9 rows / 2698.20.
- 8-27 Cleaning table: 12 rows / 3475; production classification selects its 90°
  orientation and the total reconciliation corrects the observed 6 to the
  independently observed 96.
'''
    if marker not in context:
        raise RuntimeError("PROJECT_CONTEXT real-fixture marker missing")
    context = context.replace(marker, block + marker, 1)

if "`regression_post_v95_new_packet_ocr.py`," not in context:
    anchor = """Before publishing, the full active suite should pass, including
`regression_post_v95_msa_suffix_review.py`,
`regression_post_v95_padded_endpoint_ids.py`, and the current
"""
    repl = """Before publishing, the full active suite should pass, including
`regression_post_v95_new_packet_ocr.py`,
`regression_post_v95_msa_suffix_review.py`,
`regression_post_v95_padded_endpoint_ids.py`, and the current
"""
    if anchor not in context:
        raise RuntimeError("PROJECT_CONTEXT active-suite anchor missing")
    context = context.replace(anchor, repl, 1)

CONTEXT.write_text(context, encoding="utf-8")


# 4) Update the release checklist so future work repeats the exact new guards and
# fixture targets rather than relying on this conversation.
checklist = CHECKLIST.read_text(encoding="utf-8")
if "post-v95 new-packet OCR/direction/total/layout regression" not in checklist:
    anchor = """The active baseline includes, at minimum:

- post-v95 padded complete endpoint-ID recovery regression;
"""
    repl = """The active baseline includes, at minimum:

- post-v95 new-packet OCR/direction/total/layout regression;
- post-v95 padded complete endpoint-ID recovery regression;
"""
    if anchor not in checklist:
        raise RuntimeError("RELEASE_CHECKLIST active-baseline anchor missing")
    checklist = checklist.replace(anchor, repl, 1)

if "`working_source/tests/regression_post_v95_new_packet_ocr.py`" not in checklist:
    anchor = """The current unreleased regressions are:

- `working_source/tests/regression_post_v95_msa_suffix_review.py`
- `working_source/tests/regression_post_v95_padded_endpoint_ids.py`
"""
    repl = """The current unreleased regressions are:

- `working_source/tests/regression_post_v95_new_packet_ocr.py`
- `working_source/tests/regression_post_v95_msa_suffix_review.py`
- `working_source/tests/regression_post_v95_padded_endpoint_ids.py`
"""
    if anchor not in checklist:
        raise RuntimeError("RELEASE_CHECKLIST unreleased-regression anchor missing")
    checklist = checklist.replace(anchor, repl, 1)

if "synthetic reverse-master lookup" not in checklist:
    anchor = """- Recovery must identify exactly one directional master pair.
- Exact numeric-body matches outrank tolerated leading-junk matches.
"""
    repl = """- Recovery must identify exactly one directional master pair.
- Complete printed upstream/downstream direction remains authoritative; a
  synthetic reverse-master lookup must not turn the opposite direction into an
  exact match.
- Exact numeric-body matches outrank tolerated leading-junk matches.
"""
    if anchor not in checklist:
        raise RuntimeError("RELEASE_CHECKLIST direction anchor missing")
    checklist = checklist.replace(anchor, repl, 1)

if "partial role mapping" not in checklist.lower():
    anchor = """- Faint/dashed compact B&C row rules remain recoverable without changing the
  normal solid-grid first pass.
"""
    repl = anchor + """- A compact table with usable column geometry but only a partial role mapping
  must enter the existing Layout Review instead of being skipped or crashing;
  only missing/unusable table geometry is an automatic skip.
"""
    if anchor not in checklist:
        raise RuntimeError("RELEASE_CHECKLIST compact-layout anchor missing")
    checklist = checklist.replace(anchor, repl, 1)

if "whole-table Pipe audit" not in checklist:
    anchor = """- OCR/total recovery must not manufacture or round a PDF value to match master
  data.
"""
    repl = anchor + """- Cleaning disagreement handling retains competing batch/independent OCR as
  actual PDF observations; the master may break ties only between observed values.
- A whole-table Pipe audit must not replace a currently valid measurement with a
  different OCR observation unless it improves printed-total mismatch and master
  plausibility, except when the new observation closes the printed total exactly.
"""
    if anchor not in checklist:
        raise RuntimeError("RELEASE_CHECKLIST length-integrity anchor missing")
    checklist = checklist.replace(anchor, repl, 1)

if "8-20 Manholes 20/20" not in checklist:
    marker = "\nPrivate fixtures must remain local and must never be committed or packaged.\n"
    block = r'''

The current additional Phase 2 matrix must also preserve:

- 8-20 Manholes 20/20 and Cleaning 27 / 5690, including PDF-observed 56, 171,
  and 47 corrections.
- 8-21 Pipe page 2 = 22 / 6408.66 with 323.72 recovered and correct 250 not
  replaced by worse 260; Cleaning page 4 = 23 normal printed rows / 3926;
  Cleaning page 6 = 14 / 3724; Cleaning page 8 = 12 / 3180; Manholes page 10 =
  27/27. The known non-table anomaly on page 4 is excluded from this private
  fixture expectation only and must not create generic parser/filtering logic.
- 8-25 Pipe page 2 = 12 / 2803.46 and `R2-491 -> R2-489 = 53.22` remains NOT
  MATCHED; Cleaning page 4 = 5 / 1220; Cleaning page 6 = 20 / 4821 and
  `EC-1507 -> EC-1477 = 110` remains 110.
- 8-27 first Pipe = 34 / 5164.64; Manholes = 3/3; later Pipe = 9 / 2698.20;
  Cleaning = 12 / 3475 with production classification selecting the 90° table
  orientation.

These 8-20, 8-21, 8-25, and 8-27 private fixtures passed the current post-v95
source locally against the supplied Phase 2 Year 1 master. Trouble Tickets were
intentionally excluded from this matrix.
'''
    if marker not in checklist:
        raise RuntimeError("RELEASE_CHECKLIST private-fixture marker missing")
    checklist = checklist.replace(marker, block + marker, 1)

CHECKLIST.write_text(checklist, encoding="utf-8")

print("Post-v95 finalizer patches applied.")
