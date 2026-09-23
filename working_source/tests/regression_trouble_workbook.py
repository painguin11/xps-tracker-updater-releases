import ast
import hashlib
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path


SOURCE=Path('working_source/app/reno_scan_updater.py')
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
names={'digits','asset_key','fmt_date','write_excel_date','legacy_trouble_ticket_key','trouble_ticket_key','trouble_ticket_asset_key','migrate_trouble_ticket_workbook_v60','prepare_trouble_ticket_workbook'}
nodes=[]
for node in tree.body:
    if isinstance(node,(ast.Assign,ast.AnnAssign)):
        targets=getattr(node,'targets',[getattr(node,'target',None)])
        if any(isinstance(target,ast.Name) and target.id in ('TROUBLE_TICKET_HEADERS','TROUBLE_TICKET_HEADERS_V60') for target in targets): nodes.append(node)
    elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names: nodes.append(node)
module=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(module)
namespace={'os':os,'re':re,'hashlib':hashlib,'datetime':datetime}
exec(compile(module,str(SOURCE),'exec'),namespace)


class Style:
    def __init__(self): self.Bold=False; self.Color=None; self.Hidden=False


class Cell:
    def __init__(self,sheet,row,col): self.sheet=sheet; self.Row=row; self.col=col; self.Value=None; self.NumberFormat=''; self.Font=Style(); self.Interior=Style()
    def End(self,direction):
        rows=[row for (row,col),cell in self.sheet.data.items() if col==self.col and cell.Value not in (None,'')]
        return type('End',(),{'Row':max(rows or [1])})()


class Collection:
    def __init__(self,sheet,kind): self.sheet=sheet; self.kind=kind; self.Count=1048576 if kind=='rows' else 16384
    def __call__(self,index): return RowProxy(self.sheet,index) if self.kind=='rows' else self.sheet.col_styles.setdefault(index,Style())


class RowProxy(Style):
    def __init__(self,sheet,index): super().__init__(); self.sheet=sheet; self.index=index
    def Insert(self):
        shifted={}
        for (row,col),cell in sorted(self.sheet.data.items(),reverse=True):
            if row>=self.index:
                cell.Row=row+1; shifted[(row+1,col)]=cell
            else: shifted[(row,col)]=cell
        self.sheet.data=shifted


class Cells:
    def __init__(self,sheet): self.sheet=sheet
    def __call__(self,row,col): return self.sheet.data.setdefault((row,col),Cell(self.sheet,row,col))
    def Clear(self): self.sheet.data={}


class Range(Style):
    def __init__(self,sheet): super().__init__(); self.sheet=sheet; self.Font=Style(); self.Interior=Style(); self.HorizontalAlignment=None; self.VerticalAlignment=None
    def AutoFilter(self): self.sheet.AutoFilterMode=True


class Sheet:
    def __init__(self):
        self.Name='Sheet1'; self.data={}; self.row_styles={}; self.col_styles={}; self.Rows=Collection(self,'rows'); self.Columns=Collection(self,'cols'); self.Cells=Cells(self); self.AutoFilterMode=False
    @property
    def UsedRange(self):
        filled=[(row,col) for (row,col),cell in self.data.items() if cell.Value not in (None,'')]
        rows=max([row for row,_ in filled] or [1]); cols=max([col for _,col in filled] or [1])
        return type('Used',(),{'Rows':type('Rows',(),{'Count':rows})(),'Columns':type('Cols',(),{'Count':cols})()})()
    def Range(self,*args): return Range(self)
    def Activate(self): pass


class Workbook:
    def __init__(self,books): self.sheet=Sheet(); self.Worksheets=lambda index:self.sheet; self.books=books
    def Save(self): pass
    def SaveAs(self,path,FileFormat=None): self.books[str(path)]=self; Path(path).touch()
    def Close(self,save): pass


class Workbooks:
    def __init__(self): self.books={}
    def Add(self): return Workbook(self.books)
    def Open(self,path): return self.books[str(path)]


class Excel:
    def __init__(self): self.Workbooks=Workbooks(); self.ActiveWindow=Style()


def ticket(pipe,page_hash,description='BURIED'):
    row={'date':datetime(2026,8,10),'reported_by':'ANTHONY M','pipe_id':pipe,'street_name':'EASEMENT','panel':'MAP 14','area':'2ND ST / INTERSTATE 580','service_type':'MH Survey','upstream':'','downstream':'','map_length':None,'pipe_size':'','description':description,'wo':'12069','truck':'ET01','operator':'ANTHONY M','tracker_status':'Open','resolution_notes':'','source_pdf':'sample.pdf','source_page':5,'source_page_hash':page_hash}
    row['ticket_key']=namespace['trouble_ticket_key'](row)
    return row


with tempfile.TemporaryDirectory() as folder:
    path=str(Path(folder)/'Trouble Tickets.xlsx'); excel=Excel()
    first=ticket('150335003','a'*64); second=ticket('150335025','b'*64)
    book,added,skipped,existed=namespace['prepare_trouble_ticket_workbook'](excel,path,[first,second])
    assert not existed and len(added)==2 and skipped==0
    book.SaveAs(path,FileFormat=51)
    book.sheet.Cells(2,3).Value='Resolved'
    book.sheet.Cells(2,4).Value='Repaired and verified'
    # Simulate a row written by v60 before page-based ticket identities existed.
    book.sheet.Cells(2,19).Value=namespace['legacy_trouble_ticket_key'](first)
    followup=ticket('150335003','c'*64,'NEW ISSUE')
    book2,added2,skipped2,existed2=namespace['prepare_trouble_ticket_workbook'](excel,path,[first,followup])
    assert existed2 and len(added2)==1 and skipped2==1
    sheet=book2.sheet
    assert sheet.Cells(2,1).Value=='150335003'
    assert sheet.Cells(2,19).Value==first['ticket_key']
    assert sheet.Cells(2,3).Value=='Resolved'
    assert sheet.Cells(2,4).Value=='Repaired and verified'
    assert sheet.Cells(3,1).Value=='150335003'
    assert sheet.Cells(3,2).Value=='NEW ISSUE'
    assert sheet.Cells(3,3).Value=='Open'
    assert sheet.Cells(4,1).Value=='150335025'
    assert sheet.Columns(19).Hidden is True

    # Verify an existing v60/v61 workbook migrates without losing its ticket row.
    old_path=str(Path(folder)/'Trouble Tickets old.xlsx'); old=Workbook(excel.Workbooks.books)
    excel.Workbooks.books[old_path]=old; Path(old_path).touch()
    for col,header in enumerate(namespace['TROUBLE_TICKET_HEADERS_V60'],1): old.sheet.Cells(1,col).Value=header
    old_values=[datetime(2026,8,10),'ANTHONY M','DE-3308','MAIN ST','MAP 2','MAIN / FIRST','MH Survey','','',None,'','COVERED','12069','ET01','Anthony M.','old.pdf',7,'legacy-key']
    for col,value in enumerate(old_values,1): old.sheet.Cells(2,col).Value=value
    migrated,added3,skipped3,existed3=namespace['prepare_trouble_ticket_workbook'](excel,old_path,[])
    assert existed3 and not added3 and not skipped3
    assert migrated.sheet.Cells(1,1).Value=='Pipe/MH ID'
    assert migrated.sheet.Cells(2,1).Value=='DE-3308'
    assert migrated.sheet.Cells(2,2).Value=='COVERED'
    assert migrated.sheet.Cells(2,3).Value=='Open'
    assert migrated.sheet.Cells(2,8).Value=='ANTHONY M'
    assert migrated.sheet.Cells(2,19).Value=='legacy-key'
print('Trouble-ticket page deduplication and same-asset adjacency checks passed against current source.')
