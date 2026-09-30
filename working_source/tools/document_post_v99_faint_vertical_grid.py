from pathlib import Path

context = Path(__file__).resolve().parents[2] / 'PROJECT_CONTEXT.md'
text = context.read_text(encoding='utf-8')
heading = '### Unreleased post-v99 faint vertical-grid safeguard'
if heading not in text:
    marker = 'Public v99 release:\n'
    block = (
        '### Unreleased post-v99 faint vertical-grid safeguard\n\n'
        '- Some image-only Phase 2 pair tables preserve clear horizontal rules while their interior vertical rules scan lighter than the established compact-grid threshold.\n'
        '- The compact-grid parser now makes one guarded lighter vertical-rule retry only after both established dark-grid passes fail.\n'
        '- The retry is accepted only when 5-20 long rules span at least 75% of the isolated table height and 70% of its width; normal row-rule, header-role, matching, and review safeguards remain unchanged.\n'
        '- Permanent regression: `working_source/tests/regression_post_v99_faint_vertical_grid.py`.\n'
        '- The supplied private fixture was used only for local diagnosis and was not committed or packaged.\n\n'
    )
    if marker not in text:
        raise SystemExit('PROJECT_CONTEXT marker not found')
    text = text.replace(marker, block + marker, 1)
    context.write_text(text, encoding='utf-8')

checklist = Path(__file__).resolve().parents[2] / 'RELEASE_CHECKLIST.md'
text = checklist.read_text(encoding='utf-8')
regression = '- `working_source/tests/regression_post_v99_faint_vertical_grid.py`\n'
if regression not in text:
    marker = 'The current unreleased regressions are:\n\n'
    if marker not in text:
        raise SystemExit('RELEASE_CHECKLIST regression marker not found')
    text = text.replace(marker, marker + regression, 1)

guard = ('- Faint interior vertical rules in a compact pair table may use the guarded post-v99 '
         'lighter-grid retry only after the established dark-grid passes fail; accepted rules must '
         'still satisfy the long-span/count/width evidence gates before row/header parsing.\n')
if guard not in text:
    marker = ('- Faint/dashed compact B&C row rules remain recoverable without changing the\n'
              '  normal solid-grid first pass.\n')
    if marker not in text:
        raise SystemExit('RELEASE_CHECKLIST continuation marker not found')
    text = text.replace(marker, marker + guard, 1)
checklist.write_text(text, encoding='utf-8')

print('Documented post-v99 faint vertical-grid safeguard.')
