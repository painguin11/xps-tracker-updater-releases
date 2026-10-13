"""Private, local-only field/row accuracy benchmark for B&C scanned tables.

Use on a Windows XPS workstation with the application dependencies installed.
Do NOT commit expected JSON, customer PDFs, workbooks, or generated reports.
The tool prints aggregate metrics, never individual customer IDs.
"""
import argparse
from collections import Counter
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter

RETRY_HELPERS=(
    '_year15_compact_skew_retry','_conservative_cleaning_reread',
    '_independent_row_length_read','_ocr_gridless_number_candidates',
    '_batch_pair_endpoint_full_candidates','_ocr_known_r2_candidates',
    '_contextual_pipe_length_candidates',
)

def load_app(path,label):
    spec=importlib.util.spec_from_file_location('xps_private_benchmark_'+label,str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load source: {path}')
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def portable_master_matrices(path):
    """Read private workbook sheets without COM; leave the workbook unchanged.

    This opt-in test-only path uses the artifact_tool spreadsheet reader.
    It does not change any production workbook update or master parsing code.
    """
    from artifact_tool import Blob, SpreadsheetFile
    workbook=SpreadsheetFile.import_xlsx(Blob.load(str(path)))
    matrices={}
    for item in (json.loads(line) for line in
                 workbook.inspect({'kind':'sheet','include':'id,name'}).ndjson.splitlines()):
        if item.get('kind')!='sheet':
            continue
        name=item['name']
        # Read from A1 so the existing 1-based COM master index receives the
        # exact same column positions, even if the used range is offset.
        extent=item.get('range','A1')
        bottom_right=extent.split(':')[-1]
        matrices[name]=workbook.worksheets.get_item(name).get_range('A1:'+bottom_right).values
    if not matrices:
        raise RuntimeError('No readable worksheets in the private master workbook')
    return matrices


def install_portable_com_stub(matrices):
    """A narrow read-only fake Excel connection for the existing index builder."""
    import types
    win32com=types.ModuleType('win32com')
    client=types.ModuleType('win32com.client')
    win32com.client=client
    sys.modules['win32com']=win32com
    sys.modules['win32com.client']=client
    sys.modules.setdefault('pythoncom',types.ModuleType('pythoncom'))
    sys.modules.setdefault('pywintypes',types.ModuleType('pywintypes'))
    class Sheet:
        def __init__(self,name): self.Name=name
    class Sheets:
        def __iter__(self): return (Sheet(name) for name in matrices)
        def __call__(self,name): return Sheet(name)
    class Book:
        Worksheets=Sheets()
        def Close(self,*args): pass
    class Books:
        def Open(self,*args,**kwargs): return Book()
    class Excel:
        Workbooks=Books()
        def Quit(self): pass
    client.DispatchEx=lambda *args:Excel()


def norm_id(value):
    return ''.join(ch for ch in str(value or '').upper() if ch.isalnum())

def norm_date(value):
    if value is None:
        return None
    if isinstance(value,datetime):
        return value.date().isoformat()
    raw=str(value).strip()
    for fmt in ('%Y-%m-%d','%m/%d/%Y'):
        try:
            return datetime.strptime(raw,fmt).date().isoformat()
        except ValueError:
            continue
    return raw

def field_equal(field,actual,expected):
    if field in ('up','down','asset'):
        return norm_id(actual)==norm_id(expected)
    if field=='length':
        return (actual is None and expected is None) or (
            actual is not None and expected is not None and
            abs(float(actual)-float(expected))<0.005)
    if field=='date':
        return norm_date(actual)==norm_date(expected)
    return actual==expected

def parse_one(app,master,case):
    # Import inside the actual executable path so --help works on non-Windows
    # machines without win32com, the production OCR dependencies or a GUI.
    import pymupdf
    kind=case['kind'].lower()
    if kind not in ('pipes','cleaning','manholes'):
        raise ValueError('Expected kind pipes, cleaning or manholes')
    with pymupdf.open(case['pdf']) as pdf:
        page_num=int(case['page'])
        if not 1<=page_num<=len(pdf):
            raise ValueError('Page is outside PDF')
        page=pdf[page_num-1]
        if kind=='manholes':
            return app.parse_year15_manholes(page,master),None
        layout=app.prepare_year15_pair_layout(page,master,kind)
        if any(role not in layout.get('mapping',{}) for role in ('up','down','value','date')):
            raise RuntimeError('Column roles unresolved; confirm layout in application')
        expected_date=case.get('workorder_date')
        work_date=datetime.strptime(expected_date,'%Y-%m-%d') if expected_date else None
        rows=app.parse_year15_pair_list(page,master,kind,prepared=layout,expected_date=work_date)
        return rows,layout

def install_counts(app):
    counts=Counter()
    for name in RETRY_HELPERS:
        original=getattr(app,name,None)
        if original is None:
            continue
        def instrument(*args,_name=name,_original=original,**kwargs):
            counts[_name]+=1
            return _original(*args,**kwargs)
        setattr(app,name,instrument)
    return counts

def run(app,cases,master,portable_matrices=None):
    import os
    if not Path(master).is_file():
        raise FileNotFoundError('Master workbook missing')
    if portable_matrices is None:
        index=app.load_master_index(master)
    else:
        app._sheet_matrix=lambda ws:portable_matrices[ws.Name]
        index=app._load_master_index_once(master)
    if not index:
        raise RuntimeError('Unable to load master workbook')
    counts=install_counts(app)
    totals=Counter()
    fields=Counter()
    seconds=0.0
    outcomes=[]
    for case in cases:
        if not Path(case['pdf']).is_file():
            raise FileNotFoundError(f'Missing local PDF: {Path(case["pdf"]).name}')
        before=counts.copy()
        ocr_before=int(getattr(app,'_OCR_CACHE_MISSES',0))
        start=perf_counter()
        observed,layout=parse_one(app,index,case)
        seconds+=perf_counter()-start
        expected=case['rows']
        totals['pages']+=1
        totals['expected_physical_rows']+=len(expected)
        totals['detected_physical_rows']+=len(observed)
        totals['missing_rows']+=max(0,len(expected)-len(observed))
        totals['extra_rows']+=max(0,len(observed)-len(expected))
        printed=case.get('printed_total')
        if printed is not None:
            totals['pages_with_verified_printed_total']+=1
            info=(layout or {}).get('printed_total_info') or {}
            # Never substitute the printed total for any individual field.
            value=info.get('value')
            if value is not None and abs(float(value)-float(printed))<0.005:
                totals['exact_printed_totals']+=1
        for i in range(min(len(observed),len(expected))):
            row=observed[i]
            truth=expected[i]
            bad=False
            for field in ('up','down','asset','length','date'):
                if field not in truth:
                    continue
                actual=(row.get('video_length') if field=='length'
                        else row.get('row_date') if field=='date'
                        else row.get(field))
                fields['checked_'+field]+=1
                if field_equal(field,actual,truth[field]):
                    fields['exact_'+field]+=1
                else:
                    bad=True
            blocked=bool(row.get('skip_update') or row.get('_field_review_reasons'))
            review=bool(blocked or row.get('validation_warnings') or
                        str(row.get('status') or '').startswith('LENGTH DIFF'))
            if bad and not blocked:
                # A warning color alone is not a write block; totals may
                # independently block a whole work order, tracked separately.
                totals['incorrect_rows_still_update_eligible']+=1
            if bad and not review:
                totals['unflagged_wrong_rows']+=1
            if not bad and review:
                totals['correct_rows_sent_to_review']+=1
            if review:
                totals['review_rows']+=1
            if bad:
                totals['rows_with_any_wrong_field']+=1
        outcomes.append({
            'pdf':Path(case['pdf']).name,'page':case['page'],'kind':case['kind'],
            'expected_rows':len(expected),'detected_rows':len(observed),
            'duration_seconds':round(perf_counter()-start,3),
            'ocr_cache_misses':int(getattr(app,'_OCR_CACHE_MISSES',0))-ocr_before,
            'retry_calls':dict(counts-before),
            'layout_source':(layout or {}).get('source'),
        })
    return {'totals':dict(totals),'fields':dict(fields),
            'duration_seconds':round(seconds,3),
            'helper_calls':dict(counts),'pages':outcomes}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--expected',required=True,help='PRIVATE visually checked JSON with cases[]')
    ap.add_argument('--master',required=True,help='PRIVATE master Excel workbook')
    ap.add_argument('--updated-app',default=str(Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'))
    ap.add_argument('--baseline-app',help='Path to separately checked-out baseline app source')
    ap.add_argument('--report',help='Optional local-only aggregate metrics JSON')
    ap.add_argument('--portable',action='store_true',
                    help='Read private master with artifact_tool instead of Windows Excel COM')
    args=ap.parse_args()
    fixture=json.loads(Path(args.expected).read_text(encoding='utf-8'))
    cases=fixture.get('cases')
    if not isinstance(cases,list) or not cases:
        ap.error('Expected JSON must contain a nonempty cases array')
    if not all(isinstance(c,dict) and c.get('rows') is not None for c in cases):
        ap.error('Every case requires visually checked rows')
    paths=[('updated',args.updated_app)]
    if args.baseline_app:
        paths.insert(0,('baseline',args.baseline_app))
    matrices=portable_master_matrices(args.master) if args.portable else None
    if args.portable:
        install_portable_com_stub(matrices)
    results={}
    for label,path in paths:
        results[label]=run(load_app(Path(path),label),cases,args.master,matrices)
    print(json.dumps(results,indent=2))
    if args.report:
        Path(args.report).write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
        print('PRIVATE aggregate report written locally; do not add it to Git.')

if __name__=='__main__':
    main()
