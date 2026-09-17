from pathlib import Path

TESTS=Path('working_source/tests')
paths=[
    TESTS/'regression_post_v103_manhole_reordered_columns.py',
    TESTS/'regression_post_v102_manhole_expected_count_retry.py',
    TESTS/'regression_post_v102_manhole_partial_tokens.py',
]
for path in paths:
    text=path.read_text(encoding='utf-8')
    if "'_unique_manhole_digit_match':" in text:
        continue
    anchor="    '_confirmed_suffix_asset_candidates':"
    assert anchor in text, f'harness anchor missing in {path}'
    pos=text.index(anchor)
    line_end=text.index('\n',pos)+1
    text=text[:line_end]+"    '_unique_manhole_digit_match':lambda cell,master_index: None,\n"+text[line_end:]
    path.write_text(text,encoding='utf-8')
    print(f'Updated {path}')
