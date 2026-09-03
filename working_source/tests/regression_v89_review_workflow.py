import ast
from pathlib import Path

SOURCE=Path("working_source/app/reno_scan_updater.py")
src=SOURCE.read_text(encoding="utf-8")
tree=ast.parse(src)

for required in (
    "DUPLICATE_PIPE_REVIEW = 'Duplicate pipe - check IDs'",
    "PIPE NOT FOUND IN MASTER — CHECK MH IDS",
    "MH NOT FOUND IN MASTER — CHECK MH ID",
    "class MsaConfirmDialog(tk.Toplevel):",
    "class UnmatchedAssetDecisionDialog(tk.Toplevel):",
    "def resolve_pipe_duplicate_groups(self,prompt=False,update_mode=False):",
    "if pipe_group_physical_count(records)>=3:",
    "difference=pipe_msa_difference(first,second)",
    "def resolve_unmatched_for_update(self):",
    "record['new_asset_append']=True",
    "def insert_blank_formatted_row_below(ws,base_row):",
    "Check each scan image beside its field, pre-filled text is only a suggestion.",
    "Description preview unavailable — check PDF",
    "'date':'Date'",
    "raise ValueError('Enter a valid length')",
    "ticket['_field_previews']={",
    "('Pipe/MH ID','pipe_id'",
    "self.resolve_pipe_duplicate_groups(prompt=True,update_mode=True)",
    "self.resolve_pipe_duplicate_groups(prompt=True,update_mode=False)",
):
    assert required in src, required

assert "messagebox.askyesno('Unmatched rows'" not in src
assert 'if kinds: status+=' not in src

# Exercise the pure MSA arithmetic helpers rather than testing only source text.
wanted={'pipe_group_physical_count','pipe_msa_difference'}
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted]
module=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(module)
ns={}
exec(compile(module,str(SOURCE),'exec'),ns)
a={'video_length':120.0,'master_length':301.0,'part_count':1}
b={'video_length':180.0,'master_length':301.0,'part_count':1}
assert ns['pipe_group_physical_count']([a,b])==2
assert ns['pipe_msa_difference'](a,b)==1.0
c={'video_length':10.0,'master_length':301.0,'part_count':1}
assert ns['pipe_group_physical_count']([a,b,c])==3

print('v89 reviewed wording, unmatched decisions, duplicate/MSA safeguards, and Trouble Ticket previews passed.')

# Post-review audit guards: decisions are identity-scoped, popup uses real IDs, and
# generic appends use the physical sheet end after any base-row insertions.
for required in (
    "clear_asset_decision_if_changed((asset_key(up),asset_key(down)))",
    "clear_asset_decision_if_changed(asset_key(asset))",
    "scanned=f\"{record.get('up','')} → {record.get('down','')}\"",
    "undecided_new=(status.startswith(('NEW PIPE','NEW MANHOLE'))",
    "base_info=new_asset_base_info(record,self.master_index)",
    "ps.Cells(ps.Rows.Count,ph['pipe_id']).End(-4162).Row",
    "ms.Cells(ms.Rows.Count,mh['st_id']).End(-4162).Row",
    "pipe_name.upper().startswith('UNMATCHED ROW')",
):
    assert required in src, required

print('v89 post-review identity and append-row audit guards passed.')
