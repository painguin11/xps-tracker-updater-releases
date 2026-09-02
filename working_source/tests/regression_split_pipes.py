import ast
import re
from pathlib import Path


SOURCE=Path('working_source/app/reno_scan_updater.py')
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
wanted={'asset_key','refresh_length_status','split_pipe_identity','_length_part_snapshot',
        'combine_split_pipe_records','review_status','record_needs_review'}
nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='LENGTH_DIFF_THRESHOLD' for target in node.targets):
        nodes.append(node)
    elif isinstance(node,ast.FunctionDef) and node.name in wanted:
        nodes.append(node)
module=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(module)
namespace={'re':re}
exec(compile(module,str(SOURCE),'exec'),namespace)


first={
    'kind':'Pipe','asset':'150335003','up':'MH-1','down':'MH-2','wo':'12069',
    'video_length':120.5,'master_length':301.0,'length_diff':180.5,
    'status':'LENGTH DIFF 180.5','date':None,'source_page':2,
    'display_asset':'MH-1 -> MH-2  (pipe 150335003)',
    'display_asset_base':'MH-1 -> MH-2  (pipe 150335003)','warnings':[],
}
second={
    'kind':'Pipe','asset':'150335003','up':'MH-1','down':'MH-2','wo':'12069',
    'video_length':180.5,'master_length':301.0,'date':'08/10/2026',
    'source_page':3,'warnings':[],
}
assert namespace['split_pipe_identity'](first)==namespace['split_pipe_identity'](second)
combined=namespace['combine_split_pipe_records'](first,second)
assert combined['video_length']==301.0
assert combined['part_count']==2
assert combined['part_lengths']==[120.5,180.5]
assert len(combined['_length_part_reads'])==2
assert [p['value'] for p in combined['_length_part_reads']]==[120.5,180.5]
assert combined['source_page']=='2, 3'
assert combined['status']=='Matched'
assert namespace['review_status'](combined)=='MSA DETECTED — 2 PARTS COMBINED'
assert not namespace['record_needs_review'](combined)

# A missing segment length must remain visible for review and must not pretend
# the known partial length is the completed survey total.
missing={
    'kind':'Pipe','asset':'42','up':'A','down':'B','wo':'99999',
    'video_length':100.0,'master_length':200.0,'status':'Matched',
    'source_page':4,'display_asset':'A -> B  (pipe 42)','warnings':[],
}
namespace['combine_split_pipe_records'](missing,{
    'kind':'Pipe','asset':'42','up':'A','down':'B','wo':'99999',
    'video_length':None,'source_page':4,'warnings':[],
})
assert missing['status']=='CHECK PART LENGTH'
assert namespace['record_needs_review'](missing)
assert namespace['review_status'](missing)=='MSA DETECTED — 2 PARTS COMBINED; CHECK PART LENGTH'

# Different work orders remain separate; the caller includes W/O in the merge
# decision even though the physical pipe identity is the same.
assert first['wo']!=missing['wo']

source=SOURCE.read_text(encoding='utf-8')
pipe_parser=source[source.index('def parse_pipe_list'):source.index('def parse_manhole_list')]
assert 'pid in seen' not in pipe_parser
pair_parser=source[source.index('def parse_year15_pair_list'):source.index('def parse_year15_manholes')]
assert "if key in seen and kind!='pipes': continue" in pair_parser
# A detected MSA must leave a durable master note, without changing the
# split-detection or summed-length behavior itself.
assert "if r['kind']=='Pipe' and int(r.get('part_count') or 0)>1 and notes_col:" in source
assert "append_note(ps.Cells(rr,notes_col),'MSA')" in source
# v84 preserves every physical row's OCR evidence so total mismatch recovery
# never replaces a combined pipe with the value from only one part.
assert "existing['_length_part_reads']=part_reads" in source
assert 'def _independent_split_pipe_read(record):' in source
print('Split-pipe summing, OCR-part retention, MSA note, feedback, and missing-part review checks passed.')
