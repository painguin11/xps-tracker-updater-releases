from pathlib import Path
import ast

SOURCE=Path('working_source/app/reno_scan_updater.py')
TEST=Path('working_source/tests/regression_v89_review_workflow.py')
src=SOURCE.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global src
    count=src.count(old)
    if count!=1:
        raise AssertionError(f'{label}: expected one target, found {count}')
    src=src.replace(old,new,1)

# If IDs are edited after an Add/Ignore/new-asset decision, invalidate only decisions
# tied to the old identity. Length-only edits keep the user's asset decision.
old="""def apply_manual_asset_edit(record,master_index,up=None,down=None,asset=None):
    \"\"\"Apply an Edit Selected asset/node correction and immediately re-match it.\"\"\"
    kind=record.get('kind')
    record.pop('_unmatched_ignored',None)
    record.pop('_msa_rejected',None)
    if kind in ('Pipe','Cleaning'):
        up=canonical_asset_id(up); down=canonical_asset_id(down)
        if not up or not down:
            raise ValueError('Upstream Node and Downstream Node are required.')
        match,status=_resolve_pipe_pair([up],[down],master_index)
"""
new="""def apply_manual_asset_edit(record,master_index,up=None,down=None,asset=None):
    \"\"\"Apply an Edit Selected asset/node correction and immediately re-match it.\"\"\"
    kind=record.get('kind')
    old_identity=((asset_key(record.get('up','')),asset_key(record.get('down','')))
                  if kind in ('Pipe','Cleaning') else asset_key(record.get('asset','')))
    record.pop('_unmatched_ignored',None)
    record.pop('_msa_rejected',None)
    def clear_asset_decision_if_changed(new_identity):
        if new_identity==old_identity:
            return
        for key in ('new_asset_approved','new_asset_append','new_asset_base_row','new_asset_base_asset'):
            record.pop(key,None)
        record['warnings']=[w for w in record.get('warnings',[]) if w!='BASE MASTER ROW NOT FOUND']
    if kind in ('Pipe','Cleaning'):
        up=canonical_asset_id(up); down=canonical_asset_id(down)
        if not up or not down:
            raise ValueError('Upstream Node and Downstream Node are required.')
        clear_asset_decision_if_changed((asset_key(up),asset_key(down)))
        match,status=_resolve_pipe_pair([up],[down],master_index)
"""
replace_once(old,new,'manual identity decision reset')

old="""    if kind=='Manhole':
        asset=canonical_asset_id(asset)
        if not asset: raise ValueError('Asset is required.')
        item,status=_resolve_full_asset([asset],master_index.get('manholes',{}))
"""
new="""    if kind=='Manhole':
        asset=canonical_asset_id(asset)
        if not asset: raise ValueError('Asset is required.')
        clear_asset_decision_if_changed(asset_key(asset))
        item,status=_resolve_full_asset([asset],master_index.get('manholes',{}))
"""
replace_once(old,new,'manhole identity decision reset')

# The unmatched popup should show the actual observed IDs, never the internal
# UNMATCHED ROW placeholder.
old="""        header='MH NOT FOUND IN MASTER — CHECK MH ID' if is_manhole else 'PIPE NOT FOUND IN MASTER — CHECK MH IDS'
        scanned=record.get('display_asset') or record.get('asset') or ''
        noun='manhole' if is_manhole else 'pipe'
"""
new="""        header='MH NOT FOUND IN MASTER — CHECK MH ID' if is_manhole else 'PIPE NOT FOUND IN MASTER — CHECK MH IDS'
        if is_manhole:
            scanned=record.get('asset') or record.get('display_asset') or ''
        else:
            scanned=f\"{record.get('up','')} → {record.get('down','')}\"
        noun='manhole' if is_manhole else 'pipe'
"""
replace_once(old,new,'unmatched popup scanned IDs')

# A NEW PIPE/MANHOLE whose base could not be located did not receive a real user
# decision during analysis. Resolve it at Update Master just like any other unmatched
# row. If Add is chosen and a base is now identifiable, preserve the established
# below-base insertion behavior; otherwise use the conservative formatted append path.
old="""            status=str(record.get('status') or '')
            if not (status=='NOT MATCHED' or status.startswith('AMBIGUOUS')):
                continue
            dlg=UnmatchedAssetDecisionDialog(self,record); self.wait_window(dlg)
            if dlg.result is None:
                return False
            if dlg.result=='add':
                record['new_asset_approved']=True
                record['new_asset_append']=True
                record['status']='NEW MANHOLE' if record.get('kind')=='Manhole' else 'NEW PIPE'
                record.pop('_unmatched_ignored',None)
            else:
                record['_unmatched_ignored']=True
"""
new="""            status=str(record.get('status') or '')
            unresolved=(status=='NOT MATCHED' or status.startswith('AMBIGUOUS'))
            undecided_new=(status.startswith(('NEW PIPE','NEW MANHOLE')) and
                           (('new_asset_approved' not in record) or
                            'BASE MASTER ROW NOT FOUND' in record.get('warnings',[])))
            if not (unresolved or undecided_new):
                continue
            dlg=UnmatchedAssetDecisionDialog(self,record); self.wait_window(dlg)
            if dlg.result is None:
                return False
            if dlg.result=='add':
                record['status']='NEW MANHOLE' if record.get('kind')=='Manhole' else 'NEW PIPE'
                base_info=new_asset_base_info(record,self.master_index)
                record['new_asset_approved']=True
                record['warnings']=[w for w in record.get('warnings',[]) if w!='BASE MASTER ROW NOT FOUND']
                if base_info:
                    record['new_asset_base_row']=base_info['row']
                    record['new_asset_base_asset']=base_info['base_asset']
                    record.pop('new_asset_append',None)
                else:
                    record['new_asset_append']=True
                    record.pop('new_asset_base_row',None); record.pop('new_asset_base_asset',None)
                record.pop('_unmatched_ignored',None)
            else:
                record['_unmatched_ignored']=True
"""
replace_once(old,new,'unmatched update decision logic')

# Approved below-base insertions can shift the physical last row. Query Excel after
# those insertions before appending a truly unbased new item.
old="""            append_pipe_rows=[r for r in self.records if r.get('new_asset_approved') and r.get('new_asset_append') and r.get('kind') in ('Pipe','Cleaning')]
            pipe_last=max([int(item.get('row') or 0) for item in cached.get('pipe_items',[])] or [pr])
"""
new="""            append_pipe_rows=[r for r in self.records if r.get('new_asset_approved') and r.get('new_asset_append') and r.get('kind') in ('Pipe','Cleaning')]
            pipe_last=max(int(pr),int(ps.Cells(ps.Rows.Count,ph['pipe_id']).End(-4162).Row))
"""
replace_once(old,new,'true last pipe row')

old="""                    pipe_name=r.get('asset') or f\"{master_text(r.get('up'))}-{master_text(r.get('down'))}\"
                    ps.Cells(rr,ph['pipe_id']).Value=master_text(pipe_name)
"""
new="""                    pipe_name=str(r.get('asset') or '').strip()
                    if not pipe_name or pipe_name.upper().startswith('UNMATCHED ROW'):
                        pipe_name=f\"{master_text(r.get('up'))}-{master_text(r.get('down'))}\"
                    ps.Cells(rr,ph['pipe_id']).Value=master_text(pipe_name)
"""
replace_once(old,new,'safe appended pipe ID')

old="""            append_manhole_rows=[r for r in self.records if r.get('new_asset_approved') and r.get('new_asset_append') and r.get('kind')=='Manhole']
            manhole_last=max([int(item.get('row') or 0) for item in cached.get('manholes',{}).values()] or [mr])
"""
new="""            append_manhole_rows=[r for r in self.records if r.get('new_asset_approved') and r.get('new_asset_append') and r.get('kind')=='Manhole']
            manhole_last=max(int(mr),int(ms.Cells(ms.Rows.Count,mh['st_id']).End(-4162).Row))
"""
replace_once(old,new,'true last manhole row')

ast.parse(src)
SOURCE.write_text(src,encoding='utf-8')

test=TEST.read_text(encoding='utf-8')
marker="print('v89 reviewed wording, unmatched decisions, duplicate/MSA safeguards, and Trouble Ticket previews passed.')\n"
extra="""\n# Post-review audit guards: decisions are identity-scoped, popup uses real IDs, and\n# generic appends use the physical sheet end after any base-row insertions.\nfor required in (\n    \"clear_asset_decision_if_changed((asset_key(up),asset_key(down)))\",\n    \"clear_asset_decision_if_changed(asset_key(asset))\",\n    \"scanned=f\\\"{record.get('up','')} → {record.get('down','')}\\\"\",\n    \"undecided_new=(status.startswith(('NEW PIPE','NEW MANHOLE'))\",\n    \"base_info=new_asset_base_info(record,self.master_index)\",\n    \"ps.Cells(ps.Rows.Count,ph['pipe_id']).End(-4162).Row\",\n    \"ms.Cells(ms.Rows.Count,mh['st_id']).End(-4162).Row\",\n    \"pipe_name.upper().startswith('UNMATCHED ROW')\",\n):\n    assert required in src, required\n\nprint('v89 post-review identity and append-row audit guards passed.')\n"""
if marker not in test:
    raise AssertionError('review regression print marker missing')
test=test.replace(marker,marker+extra,1)
TEST.write_text(test,encoding='utf-8')
print('Applied v89 post-review audit fixes.')
