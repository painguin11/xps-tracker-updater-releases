import ast
from pathlib import Path


SOURCE=Path('working_source/app/reno_scan_updater.py')
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='APPROVED_NEW_ROW_GREEN' for target in node.targets):
        nodes.append(node)
    elif isinstance(node,ast.FunctionDef) and node.name in {'copy_master_row_below','clear_master_columns','highlight_approved_master_row'}:
        nodes.append(node)
module=ast.Module(body=nodes,type_ignores=[]); ast.fix_missing_locations(module)
namespace={}
exec(compile(module,str(SOURCE),'exec'),namespace)


class Interior:
    def __init__(self): self.Pattern=0; self.Color=None


class Cell:
    def __init__(self,row,col,value=None):
        self.Row=row; self.Column=col; self.Value=value; self.Interior=Interior()
    def ClearContents(self): self.Value=None


class Range:
    def __init__(self,sheet,start,end):
        self.sheet=sheet; self.start=start; self.end=end; self.Interior=RangeInterior(self)
    def Copy(self,destination):
        for col in range(self.start.Column,self.end.Column+1):
            source=self.sheet.Cells(self.start.Row,col)
            target=self.sheet.Cells(destination.start.Row,col)
            target.Value=source.Value


class RangeInterior:
    def __init__(self,target): self.target=target
    @property
    def Pattern(self): return None
    @Pattern.setter
    def Pattern(self,value):
        for col in range(self.target.start.Column,self.target.end.Column+1):
            self.target.sheet.Cells(self.target.start.Row,col).Interior.Pattern=value
    @property
    def Color(self): return None
    @Color.setter
    def Color(self,value):
        for col in range(self.target.start.Column,self.target.end.Column+1):
            self.target.sheet.Cells(self.target.start.Row,col).Interior.Color=value


class Row:
    def __init__(self,sheet,index): self.sheet=sheet; self.index=index; self.RowHeight=15
    def Insert(self):
        shifted={}
        for (row,col),cell in sorted(self.sheet.data.items(),reverse=True):
            if row>=self.index:
                cell.Row=row+1; shifted[(row+1,col)]=cell
            else: shifted[(row,col)]=cell
        self.sheet.data=shifted


class Rows:
    def __init__(self,sheet): self.sheet=sheet
    def __call__(self,index): return Row(self.sheet,index)


class Sheet:
    def __init__(self):
        self.data={}; self.Rows=Rows(self)
        self.UsedRange=type('Used',(),{'Columns':type('Cols',(),{'Count':5})()})()
    def Cells(self,row,col): return self.data.setdefault((row,col),Cell(row,col))
    def Range(self,start,end): return Range(self,start,end)


sheet=Sheet()
for col,value in enumerate(['MAP 1','DE-1234','MAIN ST',None,'old note'],1):
    sheet.Cells(10,col).Value=value
sheet.Cells(11,1).Value='NEXT ROW'

insert_row,last_col=namespace['copy_master_row_below'](sheet,10)
assert insert_row==11 and last_col==5
assert [sheet.Cells(11,col).Value for col in range(1,6)]==['MAP 1','DE-1234','MAIN ST',None,'old note']
assert sheet.Cells(12,1).Value=='NEXT ROW'

namespace['clear_master_columns'](sheet,11,[4,5,None,5])
assert sheet.Cells(11,4).Value is None and sheet.Cells(11,5).Value is None
namespace['highlight_approved_master_row'](sheet,11,last_col)
green=namespace['APPROVED_NEW_ROW_GREEN']
assert all(sheet.Cells(11,col).Interior.Color==green for col in range(1,6))
assert all(sheet.Cells(11,col).Interior.Pattern==1 for col in range(1,6))

print('Approved master-row insertion, clearing, and green highlight checks passed against current source.')
