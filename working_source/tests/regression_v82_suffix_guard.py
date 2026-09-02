from pathlib import Path
import ast,re

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'def _confirmed_suffix_asset_candidates' in src
assert 'def _guard_unconfirmed_suffix_observations' in src
assert "for ratio in (.025,.045):" in src
assert 'if count>=2' in src
assert "if kind=='pipe' and not match and match_status=='NEW PIPE':" in src
assert '_confirmed_suffix_asset_candidates(cut(up_box),endpoint_items,asset_format=asset_format)' in src
assert '_confirmed_suffix_asset_candidates(cut(dn_box),endpoint_items,asset_format=asset_format)' in src
assert '_ocr_asset_candidates(view,fast_plain=True,asset_format=asset_format)' in src

# Exercise only the pure suffix-normalization helpers. Legitimate confirmed
# suffixes must survive; a lone suffix OCR artifact must collapse to the base.
tree=ast.parse(src)
names={'canonical_asset_id','asset_key','_new_suffix_asset_candidates','_guard_unconfirmed_suffix_observations'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'re':re}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<suffix-guard>','exec'),ns)
guard=ns['_guard_unconfirmed_suffix_observations']
known={'EC1817':'EC-1817','EC1801':'EC-1801'}
assert guard(['EC-1817A'],[],known)==['EC-1817']
assert guard(['EC-1817A'],['EC-1817A'],known)==['EC-1817A']
assert guard(['EC-1817'],[],known)==['EC-1817']
assert guard(['1EC1801'],[],known)==['1EC1801']

print('v82 new-suffix OCR corroboration regression passed.')
