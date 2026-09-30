from pathlib import Path
import importlib.util
import sys
import types


APP=Path('working_source/app/reno_scan_updater.py')
src=APP.read_text(encoding='utf-8')

for required in (
    "self.tree.tag_configure('total_verified', background='#16734a', foreground='white')",
    'Work order total length ({_format_pdf_number(expected)}) verified and matched, ready to update master',
    "warning=str(check.get('warning') or 'TOTAL LENGTH NEEDS VERIFICATION')",
    'This row is the work-order total-length status separator, not an individual asset row.',
):
    assert required in src, required

# Import production source while stubbing only Windows COM modules unavailable in CI.
win32com=types.ModuleType('win32com')
client=types.ModuleType('win32com.client')
win32com.client=client
sys.modules['win32com']=win32com
sys.modules['win32com.client']=client
sys.modules['pythoncom']=types.ModuleType('pythoncom')
sys.modules['pywintypes']=types.ModuleType('pywintypes')
spec=importlib.util.spec_from_file_location('xps_v87',APP)
xps=importlib.util.module_from_spec(spec)
spec.loader.exec_module(xps)


class FakeTree:
    columns=('type','asset','length','date','wo','truck','operator','status')

    def __init__(self):
        self.order=['record:0','record:1','record:2']
        self.rows={
            'record:0':{'values':('Pipe','A -> B','100','','12345','','','Matched'),'tags':()},
            'record:1':{'values':('Pipe','B -> C','200','','12345','','','Matched'),'tags':()},
            'record:2':{'values':('Pipe','X -> Y','300','','99999','','','Matched'),'tags':()},
        }

    def exists(self,iid):
        return iid in self.rows

    def delete(self,iid):
        self.rows.pop(iid,None)
        if iid in self.order: self.order.remove(iid)

    def item(self,iid,values=None,tags=None):
        if values is not None: self.rows[iid]['values']=values
        if tags is not None: self.rows[iid]['tags']=tags
        return self.rows[iid]

    def get_children(self):
        return tuple(self.order)

    def set(self,iid,column):
        return self.rows[iid]['values'][self.columns.index(column)]

    def index(self,iid):
        return self.order.index(iid)

    def insert(self,_parent,index,iid,values,tags):
        self.rows[iid]={'values':values,'tags':tags}
        if index=='end': self.order.append(iid)
        else: self.order.insert(int(index),iid)

    def see(self,_iid):
        pass


fake=types.SimpleNamespace(tree=FakeTree())
fake._total_error_iid=types.MethodType(xps.App._total_error_iid,fake)

# A passing total always creates a green separator directly after its work-order rows.
check={'wo':'12345','kind':'Pipe','passed':True,'pdf_total':300.0,
       'manual_verified':False,'warning':''}
xps.App.show_total_summary_error(fake,check)
iid=fake._total_error_iid(check)
assert fake.tree.order==['record:0','record:1',iid,'record:2'],fake.tree.order
assert fake.tree.rows[iid]['tags']==('total_verified',)
assert fake.tree.rows[iid]['values'][7]=='Work order total length (300) verified and matched, ready to update master'

# A later mismatch updates the same permanent row rather than adding/removing rows.
check.update(passed=False,warning='TOTAL LENGTH MISMATCH — PDF TOTAL 300, SUMMARY 290, DIFF 10 FT')
xps.App.show_total_summary_error(fake,check)
assert fake.tree.order.count(iid)==1
assert fake.tree.rows[iid]['tags']==('total_warning',)
assert fake.tree.rows[iid]['values'][7]==check['warning']

# Correcting the mismatch restores the verified separator and preserves its position.
check.update(passed=True,warning='')
xps.App.show_total_summary_error(fake,check)
assert fake.tree.order==['record:0','record:1',iid,'record:2']
assert fake.tree.rows[iid]['tags']==('total_verified',)
assert fake.tree.rows[iid]['values'][7]=='Work order total length (300) verified and matched, ready to update master'

print('v87 permanent work-order total separator regression passed.')
