from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def replace_once(text,old,new,label):
    count=text.count(old)
    if count!=1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    return text.replace(old,new,1)

context_path=ROOT/'PROJECT_CONTEXT.md'
s=context_path.read_text(encoding='utf-8')
old="""2. **NEW PIPE suffix evidence outranks lossy endpoint fallbacks**
   - Once complete printed endpoint evidence resolves as `NEW PIPE`, the R2,
     numeric-body, and slow OCR fallbacks are not allowed to erase the suffix
     before the existing independent suffix-confirmation crop runs.
   - If the suffix does not survive that existing independent confirmation, the
     normal conservative fallback behavior may still resolve the unsuffixed
     existing master pair.
   - This is targeted at the 8-24 page-4 style where real one-letter suffixes such
     as `DN-2243S` must not be collapsed to the base asset merely because the
     numeric bodies match.

Functional source commit for these changes:
`4b11eb19824e6fc1d74840b8b75f6c27682ee21d`.

Regression added:
`working_source/tests/regression_post_v95_msa_suffix_review.py`.

The full active Linux regression suite passed with this source change. The private
8-24 PDF was not available in the current connected file store, so the page-4
suffix fix has structural/regression validation but must still be rechecked on the
real private PDF when it is available. The private R2 fixture was also unavailable
on Linux CI, so its structural safeguards passed while exact fixture OCR was
skipped.
"""
new="""2. **NEW PIPE suffix evidence outranks lossy endpoint fallbacks**
   - Once complete printed endpoint evidence resolves as `NEW PIPE`, the R2,
     numeric-body, and slow OCR fallbacks are not allowed to erase the suffix
     before the existing independent suffix-confirmation crop runs.
   - If the suffix does not survive that existing independent confirmation, the
     normal conservative fallback behavior may still resolve the unsuffixed
     existing master pair.
   - This protects real one-letter suffixes such as `DN-2243S` from being
     collapsed to a base asset merely because the numeric bodies match.
3. **Padded complete endpoint-ID recovery for damaged grid cells**
   - If the normal endpoint reads remain unresolved, each physical endpoint cell
     may be re-read with white padding before any lossy R2/numeric-body fallback.
   - A complete ID is accepted only when at least two independent OCR passes agree.
   - The selected master may filter impossible project prefixes, but it never
     supplies missing letters or digits.
   - Independently agreed complete IDs become authoritative evidence, so a real
     suffix such as `DN-2241A` / `DN-2242A` is not erased by numeric recovery.
   - The existing suffix/new-asset and ambiguity review rules still decide whether
     an observed ID is matched, NEW PIPE, or unresolved.

Functional source commits for these changes:

- `4b11eb19824e6fc1d74840b8b75f6c27682ee21d` — reversible MSA review and suffix priority.
- `493ac60e249f7541014f8d61781b9bfa5ca64bc4` — padded complete endpoint-ID recovery.

Permanent regressions:

- `working_source/tests/regression_post_v95_msa_suffix_review.py`
- `working_source/tests/regression_post_v95_padded_endpoint_ids.py`

The full active Linux regression suite passed after the padded-ID source commit.
The supplied private 8-24, 8-26, and 8-28 packets were also exercised locally
against the supplied Phase 2 Year 1 master with Trouble Tickets intentionally out
of scope. The key Pipe/Cleaning/Manhole counts, totals, MSA reconciliation,
continuation behavior, suffix IDs, and intentionally unresolved non-master pairs
matched the documented expectations below. The private R2 fixture remains
unavailable on Linux CI, so its structural safeguards passed while exact fixture
OCR was skipped.
"""
s=replace_once(s,old,new,'current unreleased changes')
s=replace_once(s,
"""Current unreleased regression added on `v95-work`:

- `regression_post_v95_msa_suffix_review.py`
""",
"""Current unreleased regressions added on `v95-work`:

- `regression_post_v95_msa_suffix_review.py`
- `regression_post_v95_padded_endpoint_ids.py`
""",
'unreleased regressions list')
s=replace_once(s,
"""- 8-26: Manholes 10/10; Pipe page 2 = 27 rows / 6720.58; Pipe page 4 =
  15 rows / 4198.37; Manholes page 6 = 10; Cleaning page 10 = 16 rows /
  4614; Pipe page 12 = 8 rows / 1700.
- 8-28 page 2 is the compact B&C faint/dashed-row failure specifically addressed
  by v95.
""",
"""- 8-26: Manholes 10/10; Pipe page 2 = 27 physical rows / 6720.58 after
  two-part MSA reconciliation; Pipe page 4 = 15 rows / 4198.37 after targeted
  total reconciliation; Manholes page 6 = 10; Cleaning page 10 = 16 rows / 4614;
  Cleaning page 12 = 8 rows / 1700.
- 8-28 page 2: 18 Pipe rows, total 5006.09; this is the compact B&C faint/dashed
  row-grid failure specifically addressed by v95.
- 8-28 page 4: 21 physical Pipe rows, total 3095.53. Preserve complete printed
  suffix IDs including `DN-2241A` and `DN-2242A`; valid printed non-master pairs
  remain explicit review rows rather than being fuzzy-corrected.
""",
'real fixture expectations')
s=replace_once(s,
"""Before publishing, the full active suite should pass, including
`regression_post_v95_msa_suffix_review.py`, the current
""",
"""Before publishing, the full active suite should pass, including
`regression_post_v95_msa_suffix_review.py`,
`regression_post_v95_padded_endpoint_ids.py`, and the current
""",
'active regression expectations')
context_path.write_text(s,encoding='utf-8')

check_path=ROOT/'RELEASE_CHECKLIST.md'
s=check_path.read_text(encoding='utf-8')
s=replace_once(s,
"""The active baseline includes, at minimum:

- post-v95 MSA preview/reversal and NEW PIPE suffix-priority regression;
""",
"""The active baseline includes, at minimum:

- post-v95 padded complete endpoint-ID recovery regression;
- post-v95 MSA preview/reversal and NEW PIPE suffix-priority regression;
""",
'checklist active baseline')
s=replace_once(s,
"""The current unreleased regression is:
`working_source/tests/regression_post_v95_msa_suffix_review.py`.
""",
"""The current unreleased regressions are:

- `working_source/tests/regression_post_v95_msa_suffix_review.py`
- `working_source/tests/regression_post_v95_padded_endpoint_ids.py`
""",
'checklist regression list')
s=replace_once(s,
"""- A suffix that fails independent confirmation may still fall back conservatively;
  independently corroborated real suffix evidence must remain a NEW PIPE.
""",
"""- A suffix that fails independent confirmation may still fall back conservatively;
  independently corroborated real suffix evidence must remain a NEW PIPE.
- Unresolved endpoint cells may use padded complete-ID recovery before lossy
  fallbacks, but a complete ID requires agreement from at least two independent
  OCR passes. The master may filter impossible prefixes only; it must never fill
  in a missing endpoint letter or digit.
""",
'checklist matching expectation')
s=replace_once(s,
"""- 8-24 page 4 is a key private real-fixture check for suffix handling; in
  particular `DN-2243S -> DN-2243 = 52` must remain a valid NEW PIPE.
""",
"""- 8-24 page 4 is a key private real-fixture check for suffix handling; in
  particular `DN-2243S -> DN-2243 = 52` must remain a valid NEW PIPE.
- 8-28 page 4 is a key padded-complete-ID target: 21 physical Pipe rows must total
  3095.53 and printed suffixes such as `DN-2241A` / `DN-2242A` must survive.
""",
'checklist new asset fixture')
s=replace_once(s,
"""The 8-28 page-2 compact B&C table is a key v95 real-PDF regression target.
The 8-24 packet is a key continuation/final-total/Manhole-count target, and page 4
is now also a key suffix-ID target.
""",
"""The 8-28 page-2 compact B&C table is a key v95 real-PDF regression target.
The 8-24 packet is a key continuation/final-total/Manhole-count target, and page 4
is a key suffix-ID target. The 8-26 packet is a key two-part MSA plus total-reread
target. The 8-28 page-4 table is a key complete-suffix-ID target.

The supplied 8-24, 8-26, and 8-28 private fixtures have passed the current
post-v95 source locally against the supplied Phase 2 Year 1 master, with Trouble
Tickets intentionally excluded from this test pass.
""",
'checklist private fixture status')
s=replace_once(s,
"""The public updater manifest points to that verified v95 asset. The current
`v95-work` MSA/suffix changes are unreleased until the user explicitly says
`PUBLISH`.
""",
"""The public updater manifest points to that verified v95 asset. The current
`v95-work` MSA/suffix/padded-endpoint changes are unreleased until the user
explicitly says `PUBLISH`.
""",
'checklist production footer')
check_path.write_text(s,encoding='utf-8')
print('Updated post-v95 real-fixture documentation.')
