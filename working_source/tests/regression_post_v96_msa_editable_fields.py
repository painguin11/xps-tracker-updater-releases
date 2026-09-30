from pathlib import Path
import importlib.util
import sys
import types

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
s=SOURCE.read_text(encoding='utf-8')

# The MSA review must expose all OCR-derived row fields as editable values and
# must provide an explicit save-without-merge action if corrected IDs diverge.
start=s.index('class MsaConfirmDialog(tk.Toplevel):')
end=s.index('\n\nclass NewAssetApprovalDialog',start)
dialog=s[start:end]
for required in (
    "self.edits=None",
    "ttk.Entry(block,textvariable=var,width=26)",
    "('Upstream ID','up','upstream')",
    "('Downstream ID','down','downstream')",
    "('Length','video_length','activity_value')",
    "text='Save Changes & Cancel MSA'",
    "self.save_cancel_button.grid_remove()",
    "self.confirm_button.state(['disabled'])",
    "Use Save Changes & Cancel MSA instead.",
):
    assert required in dialog, required

# Import the real helper code with Windows-only modules stubbed out.
win32com=types.ModuleType('win32com')
client=types.ModuleType('win32com.client')
win32com.client=client
sys.modules['win32com']=win32com
sys.modules['win32com.client']=client
pythoncom=types.ModuleType('pythoncom'); pythoncom.CoInitialize=lambda:None; pythoncom.CoUninitialize=lambda:None
sys.modules['pythoncom']=pythoncom
pywintypes=types.ModuleType('pywintypes'); pywintypes.com_error=Exception
sys.modules['pywintypes']=pywintypes
spec=importlib.util.spec_from_file_location('xps_post_v96_msa',SOURCE)
xps=importlib.util.module_from_spec(spec); spec.loader.exec_module(xps)

# Synthetic master entries let us verify that saving popup edits uses the same
# normal matching path as Edit Selected rather than bypassing safeguards.
pipe_a={'row':1,'expected':167.296975,'pipe_id':'P-A','up':'R2-349','down':'R2-335',
        'up_key':'R2349','down_key':'R2335'}
pipe_b={'row':2,'expected':210.0,'pipe_id':'P-B','up':'R2-400','down':'R2-401',
        'up_key':'R2400','down_key':'R2401'}
master={
    'pipes':{
        ('R2349','R2335'):pipe_a,
        ('R2400','R2401'):pipe_b,
    },
    'pipe_items':[pipe_a,pipe_b],
    'pipe_by_id':{'PA':pipe_a,'PB':pipe_b},
    'manholes':{},
}
first={'kind':'Pipe','up':'R2-349','down':'R2-335','asset':'P-A','display_asset':'R2-349 -> R2-335',
       'video_length':84.48,'master_length':167.296975,'status':'LENGTH DIFF 82.8',
       'warnings':[xps.DUPLICATE_PIPE_REVIEW],'_msa_pending':True}
second={'kind':'Pipe','up':'R2-349','down':'R2-335','asset':'P-A','display_asset':'R2-349 -> R2-335',
        'video_length':2.87,'master_length':167.296975,'status':'LENGTH DIFF 164.4',
        'warnings':[xps.DUPLICATE_PIPE_REVIEW],'_msa_pending':True}

same=xps.apply_msa_review_edits(first,second,master,[
    {'up':'R2-349','down':'R2-335','video_length':'84.48'},
    {'up':'R2-349','down':'R2-335','video_length':'82.87'},
])
assert same is True
assert second['video_length']==82.87,second
assert second.get('_length_user_edited') is True,second
assert xps.pipe_msa_difference(first,second)<xps.LENGTH_DIFF_THRESHOLD,(first,second)

# If one printed ID was misread, Save Changes & Cancel MSA must preserve both
# corrected rows independently and clear stale duplicate/MSA state.
second['warnings']=[xps.DUPLICATE_PIPE_REVIEW]
second['_msa_pending']=True
same=xps.apply_msa_review_edits(first,second,master,[
    {'up':'R2-349','down':'R2-335','video_length':'84.48'},
    {'up':'R2-400','down':'R2-401','video_length':'82.87'},
])
assert same is False
assert second['up']=='R2-400' and second['down']=='R2-401',second
assert second['asset']=='P-B' and second['master_length']==210.0,second
assert xps.DUPLICATE_PIPE_REVIEW not in second.get('warnings',[]),second
assert not second.get('_msa_pending') and not second.get('_msa_rejected'),second

# Reproduce the 8-26 failure mode without the private PDF: direct OCR observes
# 82.87, a fallback also observes 2.87, and the master is the *combined* MSA
# length so neither individual part is within the normal 35% master window.
orig=xps._independent_row_length_read
try:
    xps._independent_row_length_read=lambda *_a,**_k:{
        'value':82.87,'confident':True,'candidates':[82.87,82.87,82.87],
        'source':'synthetic independent support'}
    cands=[82.87,2.87]
    chosen=xps._choose_pair_length_observation(cands,82.87,167.296975,'cell','expanded')
    assert chosen==82.87,(chosen,cands)
finally:
    xps._independent_row_length_read=orig

print('Post-v96 editable MSA fields, save/cancel, and 8-26 length safeguard regression passed.')
