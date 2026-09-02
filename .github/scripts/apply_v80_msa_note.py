from pathlib import Path

APP=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_split_pipes.py')

text=APP.read_text(encoding='utf-8')
old="""                    # Carry configured length warnings into NOTES when the project\n                    # provides that column, and highlight the measured value itself.\n                    diff=r.get('length_diff')\n"""
new="""                    # A split-pipe/MSA survey is stored as one combined master row.\n                    # Mark that row explicitly while preserving any existing notes.\n                    notes_col=ph.get('notes')\n                    if r['kind']=='Pipe' and int(r.get('part_count') or 0)>1 and notes_col:\n                        append_note(ps.Cells(rr,notes_col),'MSA')\n                    # Carry configured length warnings into NOTES when the project\n                    # provides that column, and highlight the measured value itself.\n                    diff=r.get('length_diff')\n"""
if new not in text:
    if old not in text:
        raise SystemExit('Expected master-write block not found; refusing broad edit')
    text=text.replace(old,new,1)
APP.write_text(text,encoding='utf-8')

test=TEST.read_text(encoding='utf-8')
anchor="""assert \"if key in seen and kind!='pipes': continue\" in pair_parser\nprint('Split-pipe summing, MSA feedback, and missing-part review checks passed.')\n"""
replacement="""assert \"if key in seen and kind!='pipes': continue\" in pair_parser\n# A detected MSA must leave a durable master note, without changing the\n# split-detection or summed-length behavior itself.\nassert \"if r['kind']=='Pipe' and int(r.get('part_count') or 0)>1 and notes_col:\" in source\nassert \"append_note(ps.Cells(rr,notes_col),'MSA')\" in source\nprint('Split-pipe summing, MSA master note, feedback, and missing-part review checks passed.')\n"""
if replacement not in test:
    if anchor not in test:
        raise SystemExit('Expected split-pipe regression anchor not found')
    test=test.replace(anchor,replacement,1)
TEST.write_text(test,encoding='utf-8')
print('Applied v80 MSA master-note change.')
