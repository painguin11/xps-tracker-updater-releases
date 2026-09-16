from pathlib import Path

root=Path(__file__).resolve().parents[2]
context=root/'PROJECT_CONTEXT.md'
text=context.read_text(encoding='utf-8')
section='''
## Pending after v103 - reordered Manhole table columns

- A supplied private five-page B&C packet has a 37-row Manhole table on page 2 with `Date` first and `Manhole Number` second. The work-order page confirms 37 Manholes.
- v103 still assumed the older Manhole grid order (`Manhole Number` first, `Date` last) in its ruled-row and count-retry crops. Whole-page OCR saw only two IDs on this scan, so the fuller grid path could not recover the table.
- The Manhole parser now reads the printed header positions to locate the Manhole Number and Date cells, while retaining the v103 fixed-column fallback if header OCR is unusable. It also extends Manhole row-band detection from 72% to 90% of page height so long tables keep their final physical row.
- The count-mismatch retry uses the same detected Manhole/Date cells. Global asset-ID syntax and matching safeguards are unchanged.
- Permanent synthetic regression: `working_source/tests/regression_post_v103_manhole_reordered_columns.py`.
- The supplied customer PDF remains private and is not committed or packaged.
'''
if '## Pending after v103 - reordered Manhole table columns' not in text:
    insert=text.find('\n## Released in v103')
    if insert<0:
        insert=text.find('\n## Released in v102')
    if insert<0:
        insert=len(text)
    text=text[:insert]+section+text[insert:]
    context.write_text(text,encoding='utf-8')

checklist=root/'RELEASE_CHECKLIST.md'
text=checklist.read_text(encoding='utf-8')
bullet='- post-v103 reordered Manhole Date/Manhole-Number column regression;\n'
marker='The active baseline includes, at minimum:\n\n'
if bullet not in text:
    if marker not in text:
        raise SystemExit('active regression marker missing')
    text=text.replace(marker,marker+bullet,1)
named='- `working_source/tests/regression_post_v103_manhole_reordered_columns.py`\n'
marker2='The following post-version-named regressions are already released and remain required:\n\n'
if named not in text:
    if marker2 not in text:
        raise SystemExit('named regression marker missing')
    text=text.replace(marker2,marker2+named,1)
checklist.write_text(text,encoding='utf-8')

docs=root/'working_source'/'docs'
(docs/'PROJECT_CONTEXT.md').write_text(context.read_text(encoding='utf-8'),encoding='utf-8')
(docs/'RELEASE_CHECKLIST.md').write_text(checklist.read_text(encoding='utf-8'),encoding='utf-8')
print('Documented post-v103 reordered Manhole column fix')
