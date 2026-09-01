import os, re, sys, shutil, statistics, csv, json, hashlib, time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    import pymupdf
    import cv2
    import numpy as np
    import pytesseract
    from PIL import Image, ImageTk
    import win32com.client
    import pythoncom, pywintypes
except Exception as exc:
    root = tk.Tk(); root.withdraw()
    messagebox.showerror('Missing dependency', f'A required component is missing:\n\n{exc}\n\nRun setup_and_run.bat first.')
    raise

APP_NAME = 'XPS Tracker Updater'
APP_VERSION = '78'
APP_TITLE = f'{APP_NAME} v{APP_VERSION}'
LENGTH_DIFF_THRESHOLD = 4.5
OCR_CACHE_VERSION = 'v5'
_OCR_CACHE = {}
_OCR_CACHE_PATH = ''
_OCR_CACHE_DIRTY = 0
_OCR_CACHE_HITS = 0
_OCR_CACHE_MISSES = 0
_PAGE_CACHE_FOLDER = ''

TROUBLE_TICKET_HEADERS_V60 = [
    'Date', 'Reported By', 'Pipe ID', 'Street Name', 'Panel',
    'Area / Major Intersection', 'Service Type', 'Upstream Manhole',
    'Downstream Manhole', 'Map Length', 'Pipe Size', 'Description',
    'Work Order', 'Truck', 'Operator', 'Source PDF', 'PDF Page', 'Ticket Key'
]
TROUBLE_TICKET_HEADERS = [
    'Pipe/MH ID', 'Description', 'Status', 'Resolution / Follow-up Notes',
    'Date', 'Work Order', 'Truck', 'Operator', 'Panel', 'Street',
    'Area / Major Intersection', 'Service Type', 'Upstream Manhole',
    'Downstream Manhole', 'Map Length', 'Pipe Size', 'Source PDF',
    'PDF Page', 'Ticket Key'
]


class AnalysisCancelled(Exception):
    pass


def app_resource_path(filename):
    """Resolve packaged resources both from source and a PyInstaller EXE."""
    base=getattr(sys,'_MEIPASS',os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base,filename)


def apply_app_icon(window):
    """Give Tk each native icon size so Windows never has to stretch one."""
    try:
        icon=app_resource_path('xps_tracker_updater.ico')
        if not os.path.exists(icon) and getattr(sys,'frozen',False): icon=sys.executable
        if not os.path.exists(icon): return
        source=Image.open(icon)
        sizes=sorted(source.ico.sizes()) if hasattr(source,'ico') else [source.size]
        photos=[]
        for size in sizes:
            frame=source.ico.getimage(size) if hasattr(source,'ico') else source.copy()
            photos.append(ImageTk.PhotoImage(frame.convert('RGBA'),master=window))
        if photos:
            window.iconphoto(True,*photos)
            # Tk does not retain Python references to icon images.
            window._xps_icon_photos=photos
    except Exception:
        pass


def configure_windows_identity():
    """Set identity and DPI mode before Tk creates any windows."""
    if sys.platform!='win32': return
    try:
        import ctypes
        # Prevent Windows from bitmap-scaling Tk's title-bar and taskbar icons.
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception: ctypes.windll.user32.SetProcessDPIAware()
        # Versioned identity prevents Windows from reusing a stale cached taskbar icon.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f'XPS.TrackerUpdater.v{APP_VERSION}')
    except Exception:
        pass


def ui_scale_for(window):
    """Return the current monitor scale relative to standard 96-DPI Windows."""
    try:
        dpi=float(window.winfo_fpixels('1i'))
        return max(.85,min(2.5,dpi/96.0))
    except Exception:
        try:
            return max(.85,min(2.5,float(window.tk.call('tk','scaling'))/(96.0/72.0)))
        except Exception:
            return 1.0


def _cache_root():
    base=os.environ.get('LOCALAPPDATA') or os.path.join(os.path.expanduser('~'),'.xps_tracker_updater')
    return os.path.join(base,'XPS Tracker Updater','Cache')


def _layout_profile_path():
    folder=os.path.dirname(_cache_root()); os.makedirs(folder,exist_ok=True)
    return os.path.join(folder,'layout_profiles_v1.json')


def _entry_history_path():
    folder=os.path.dirname(_cache_root()); os.makedirs(folder,exist_ok=True)
    return os.path.join(folder,'confirmed_entries_v1.json')


def load_entry_history():
    try:
        with open(_entry_history_path(),encoding='utf-8') as f: data=json.load(f)
        if not isinstance(data,dict): return {'trucks':{},'operators':{}}
        return {k:{str(v):int(n) for v,n in (data.get(k,{}) or {}).items() if int(n)>0}
                for k in ('trucks','operators')}
    except Exception:
        return {'trucks':{},'operators':{}}


def remember_confirmed_entries(groups):
    """Remember user-confirmed values only after Excel has saved successfully."""
    try:
        data=load_entry_history()
        for g in groups or []:
            truck=str(g.get('truck') or '').strip().upper()
            if re.fullmatch(r'[A-Z]{2}\d{2}',truck):
                data['trucks'][truck]=data['trucks'].get(truck,0)+1
            operator=_clean_operator_guess(g.get('operator_full') or g.get('operator') or '')
            if operator:
                operator=' '.join(w.capitalize() if len(w)>1 else w.upper()
                                  for w in re.findall(r"[A-Za-z][A-Za-z.'-]*",operator))
                if operator:
                    data['operators'][operator]=data['operators'].get(operator,0)+1
        path=_entry_history_path(); temp=path+'.tmp'
        with open(temp,'w',encoding='utf-8') as f: json.dump(data,f,indent=2,sort_keys=True)
        os.replace(temp,path)
    except Exception:
        pass


def _add_count(counts,value,kind):
    raw=str(value or '').strip()
    if kind=='truck':
        raw=raw.upper()
        if not re.fullmatch(r'[A-Z]{2}\d{2}',raw): return
    else:
        raw=_clean_operator_guess(raw)
        words=re.findall(r"[A-Za-z][A-Za-z.'-]*",raw)
        if not words: return
        raw=' '.join(w.capitalize() if len(w)>1 else w.upper() for w in words)
    counts[raw]=counts.get(raw,0)+1


def _merge_entry_history(truck_counts,operator_counts):
    history=load_entry_history()
    for value,n in history['trucks'].items(): truck_counts[value]=truck_counts.get(value,0)+n
    for value,n in history['operators'].items(): operator_counts[value]=operator_counts.get(value,0)+n


def load_layout_profiles():
    try:
        with open(_layout_profile_path(),encoding='utf-8') as f: data=json.load(f)
        return data if isinstance(data,dict) else {}
    except Exception: return {}


def save_layout_profile(fingerprint,layout,role_indices):
    try:
        profiles=load_layout_profiles()
        profiles[fingerprint]={'kind':layout.get('kind'),'headers':layout.get('headers',[]),
                               'role_indices':{k:int(v) for k,v in role_indices.items()},
                               'saved':datetime.now().isoformat(timespec='seconds')}
        path=_layout_profile_path(); temp=path+'.tmp'
        with open(temp,'w',encoding='utf-8') as f: json.dump(profiles,f,indent=2)
        os.replace(temp,path)
    except Exception: pass


def init_ocr_cache(pdf_hash):
    """Load persistent OCR results for this exact PDF without caching master data."""
    global _OCR_CACHE,_OCR_CACHE_PATH,_OCR_CACHE_DIRTY,_OCR_CACHE_HITS,_OCR_CACHE_MISSES,_PAGE_CACHE_FOLDER
    _OCR_CACHE={}; _OCR_CACHE_DIRTY=0; _OCR_CACHE_PATH=''; _OCR_CACHE_HITS=0; _OCR_CACHE_MISSES=0
    _PAGE_CACHE_FOLDER=''
    if not pdf_hash: return
    folder=_cache_root(); os.makedirs(folder,exist_ok=True)
    _OCR_CACHE_PATH=os.path.join(folder,f'{pdf_hash}_{OCR_CACHE_VERSION}.json')
    _PAGE_CACHE_FOLDER=os.path.join(folder,f'{pdf_hash}_{OCR_CACHE_VERSION}_pages'); os.makedirs(_PAGE_CACHE_FOLDER,exist_ok=True)
    try:
        with open(_OCR_CACHE_PATH,encoding='utf-8') as f:
            raw=json.load(f)
        if isinstance(raw,dict): _OCR_CACHE=raw
    except Exception: _OCR_CACHE={}


def save_ocr_cache():
    global _OCR_CACHE_DIRTY,_OCR_CACHE_HITS,_OCR_CACHE_MISSES
    if not _OCR_CACHE_PATH or not _OCR_CACHE_DIRTY: return
    try:
        temp=_OCR_CACHE_PATH+'.tmp'
        with open(temp,'w',encoding='utf-8') as f: json.dump(_OCR_CACHE,f,separators=(',',':'))
        os.replace(temp,_OCR_CACHE_PATH); _OCR_CACHE_DIRTY=0
    except Exception: pass


def cached_ocr_string(img,config=''):
    """Cache Tesseract output by exact pixels and configuration."""
    global _OCR_CACHE_DIRTY,_OCR_CACHE_HITS,_OCR_CACHE_MISSES
    if img is None or getattr(img,'size',0)==0: return ''
    try:
        key=hashlib.sha1(str((img.shape,str(img.dtype),config)).encode()+img.tobytes()).hexdigest()
        if key in _OCR_CACHE:
            _OCR_CACHE_HITS+=1; return _OCR_CACHE[key]
    except Exception:
        return pytesseract.image_to_string(img,config=config)
    text=pytesseract.image_to_string(img,config=config)
    _OCR_CACHE_MISSES+=1
    _OCR_CACHE[key]=text; _OCR_CACHE_DIRTY+=1
    if _OCR_CACHE_DIRTY>=50: save_ocr_cache()
    return text


def find_tesseract():
    p = shutil.which('tesseract')
    if p:
        return p
    candidates = [
        r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
        r'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\\Programs\\Tesseract-OCR\\tesseract.exe'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def digits(v):
    if v is None: return ''
    s = str(v).strip()
    if s.endswith('.0'): s = s[:-2]
    return re.sub(r'\D', '', s)


def canonical_asset_id(v):
    """Preserve a full asset identifier while normalizing its display punctuation."""
    raw=str(v or '').strip().upper()
    # Preserve prefixes that legitimately contain digits.  Compacting first made
    # R2-280 become R2280, which the generic formatter rebuilt as R-2280.
    punctuated=re.sub(r'[^A-Z0-9]+','-',raw).strip('-')
    m=re.fullmatch(r'([A-Z]+\d*)-+(\d+[A-Z]*)',punctuated)
    if m: return f'{m.group(1)}-{m.group(2)}'
    compact=re.sub(r'[^A-Z0-9]','',raw)
    m=re.fullmatch(r'([A-Z]+)(\d+)([A-Z]*)',compact)
    if m: return f'{m.group(1)}-{m.group(2)}{m.group(3)}'
    return compact


def asset_key(v):
    return re.sub(r'[^A-Z0-9]','',str(v or '').upper())


def asset_number(v):
    return ''.join(re.findall(r'\d',asset_key(v)))


def _ocr_id_text_variants(text):
    key=asset_key(text)
    if not key: return []
    out=[key]
    # Handwritten/highlighted IDs commonly turn 5 into S, 0 into O, and 1 into I/L.
    out.append(key.translate(str.maketrans({'S':'5','O':'0','Q':'0','I':'1','L':'1','B':'8'})))
    return list(dict.fromkeys(x for x in out if x))


def parse_float(s):
    if s is None: return None
    s = str(s).strip().replace(',', '')
    m = re.search(r'\d+(?:\.\d+)?', s)
    return float(m.group()) if m else None


def parse_date_text(text):
    # Month-name report dates are the most reliable on the printed survey-list page.
    m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})', text, re.I)
    if m:
        try: return datetime.strptime(f'{m.group(1)} {m.group(2)} {m.group(3)}', '%B %d %Y')
        except: pass
    # Handwritten/typed numeric dates.
    for pat in [r'\b(\d{1,2})[-/]\s*(\d{1,2})[-/]\s*((?:20)?\d{2})\b']:
        m = re.search(pat, text)
        if m:
            try:
                year=int(m.group(3)); year=2000+year if year<100 else year
                return datetime(year, int(m.group(1)), int(m.group(2)))
            except: pass
    return None


def fmt_date(d):
    return d.strftime('%m/%d/%Y') if isinstance(d, datetime) else str(d or '')


def operator_master_name(name):
    """Convert confirmed operator to first name + last initial when available.

    Tyler Martinez -> Tyler M.  If the work order only contains a first name
    (for example, Anthony), preserve that rather than inventing a last initial.
    """
    raw = str(name or '').strip()
    cleaned = re.sub(r"[^A-Za-z\s.'-]", ' ', raw)
    parts = [p.strip(" .' -") for p in re.split(r'\s+', cleaned) if p.strip(" .' -")]
    if len(parts) >= 2:
        first = parts[0].title()
        last_initial = re.sub(r'[^A-Za-z]', '', parts[-1])[:1].upper()
        return f'{first} {last_initial}'.strip() if last_initial else first
    if len(parts) == 1:
        return parts[0].title()
    return ''


def locate_headers(ws, required):
    used = ws.UsedRange
    max_col = used.Columns.Count
    for r in range(1, min(10, used.Rows.Count) + 1):
        vals = {}
        for c in range(1, max_col + 1):
            v = ws.Cells(r, c).Value
            if v is not None:
                vals[str(v).strip().lower()] = c
        if all(x.lower() in vals for x in required):
            return r, vals
    raise RuntimeError(f'Could not find required columns on sheet {ws.Name}: {required}')


def _header_map(ws, row=2):
    """Return normalized header -> columns, preserving repeated section headers."""
    out = {}
    for c in range(1, ws.UsedRange.Columns.Count + 1):
        v = ws.Cells(row, c).Value
        if v not in (None, ''):
            out.setdefault(re.sub(r'[^a-z0-9]+', ' ', str(v).strip().lower()).strip(), []).append(c)
    return out


def _sheet_matrix(ws):
    """Read a worksheet through one COM transfer instead of cell-by-cell calls."""
    used=ws.UsedRange
    row0=int(used.Row); col0=int(used.Column)
    rows=int(used.Rows.Count); cols=int(used.Columns.Count)
    raw=used.Value2
    if rows==1 and cols==1: raw=((raw,),)
    elif rows==1: raw=(tuple(raw),)
    elif cols==1: raw=tuple((x,) if not isinstance(x,(tuple,list)) else tuple(x) for x in raw)
    else: raw=tuple(tuple(x) for x in raw)
    # Pad to A1 coordinates so existing 1-based Excel column numbers remain valid.
    matrix=[[None]*(col0-1+cols) for _ in range(row0-1)]
    prefix=[None]*(col0-1)
    matrix.extend(prefix+list(row) for row in raw)
    return matrix


def _mv(matrix,row,col):
    try: return matrix[row-1][col-1]
    except (IndexError,TypeError): return None


def _header_map_matrix(matrix,row):
    out={}
    if not (1<=row<=len(matrix)): return out
    for c,v in enumerate(matrix[row-1],1):
        if v not in (None,''):
            key=re.sub(r'[^a-z0-9]+',' ',str(v).strip().lower()).strip()
            out.setdefault(key,[]).append(c)
    return out


def _locate_headers_matrix(matrix,required,sheet_name):
    needed=[x.lower() for x in required]
    for r in range(1,min(10,len(matrix))+1):
        vals={}
        for c,v in enumerate(matrix[r-1],1):
            if v is not None: vals[str(v).strip().lower()]=c
        if all(x in vals for x in needed): return r,vals
    raise RuntimeError(f'Could not find required columns on sheet {sheet_name}: {required}')


def _sheet_by_headers(wb, required, max_rows=5):
    required = {re.sub(r'[^a-z0-9]+', ' ', x.lower()).strip() for x in required}
    for ws in wb.Worksheets:
        for row in range(1, min(max_rows, ws.UsedRange.Rows.Count) + 1):
            hm = _header_map(ws, row)
            if required.issubset(hm):
                return ws, row, hm
    raise RuntimeError('Could not find a worksheet containing: ' + ', '.join(sorted(required)))


def _com_call_rejected(exc):
    """True for Excel's transient RPC_E_CALL_REJECTED / retry-later errors."""
    code=getattr(exc,'hresult',None)
    if code in (-2147418111,-2147417846): return True
    text=str(exc).lower()
    return 'call was rejected by callee' in text or 'application is busy' in text


def load_master_index(path, attempts=5):
    """Read the master, retrying when desktop Excel is briefly busy."""
    last=None
    for attempt in range(attempts):
        try:
            pythoncom.CoInitialize()
            return _load_master_index_once(path)
        except Exception as exc:
            last=exc
            if not _com_call_rejected(exc): raise
            if attempt==attempts-1:
                raise RuntimeError('Excel stayed busy and would not allow the master to be read. Close any Excel dialogs and close the selected master workbook, then try again.') from exc
            # Let Excel finish startup, calculation, add-ins, or a previous COM call.
            try: pythoncom.PumpWaitingMessages()
            except Exception: pass
            time.sleep(.6*(attempt+1))
        finally:
            try: pythoncom.CoUninitialize()
            except Exception: pass
    raise last


def _load_master_index_once(path):
    excel = win32com.client.DispatchEx('Excel.Application')
    excel.Visible = False; excel.DisplayAlerts = False
    wb = None
    try:
        wb = excel.Workbooks.Open(os.path.abspath(path), ReadOnly=True)
        sheet_names = {str(ws.Name).lower() for ws in wb.Worksheets}
        year15 = 'year15pipes' in sheet_names and 'year15manholes' in sheet_names
        phase2 = 'pipes' in sheet_names and 'phase 2 year 1 manholes' in sheet_names
        if year15 or phase2:
            profile = 'year15' if year15 else 'phase2_year1'
            pipe_sheet_name = 'Year15Pipes' if year15 else 'Pipes'
            manhole_sheet_name = 'Year15Manholes' if year15 else 'Phase 2 Year 1 Manholes'
            ps = wb.Worksheets(pipe_sheet_name); ps_name=str(ps.Name); pr = 2
            pvals=_sheet_matrix(ps); hm = _header_map_matrix(pvals,pr)
            # The duplicated Date/W/O/Truck/Operator columns are disambiguated by
            # position: CLEAN is I:M and VIDEO is N:R in this project master.
            wheel_key = 'wheel walk' if 'wheel walk' in hm else 'w walk'
            video_key = 'video length' if 'video length' in hm else 'pano lgth'
            ph = {'panelno': hm['panelno'][0], 'upstream': hm['up mh'][0], 'downstream': hm['dn mh'][0],
                  'pipe_id': hm['sewer id'][0], 'length': hm['length'][0],
                  'clean wheel walk': hm[wheel_key][0], 'clean date': hm['date'][0],
                  'clean w/o': hm['w o'][0], 'clean truck': hm['truck'][0], 'clean operator': hm['operator'][0],
                  'video length': hm[video_key][0], 'video date': hm['date'][1],
                  'video w/o': hm['w o'][1], 'video truck': hm['truck'][1], 'video operator': hm['operator'][1]}
            ph['notes']=hm.get('notes',[None])[0]
            pipes={}; pipe_by_id={}
            for r in range(pr+1,len(pvals)+1):
                up=canonical_asset_id(_mv(pvals,r,ph['upstream'])); dn=canonical_asset_id(_mv(pvals,r,ph['downstream']))
                if not up or not dn: continue
                item={'row':r,'expected':parse_float(_mv(pvals,r,ph['length'])),
                      'pipe_id':canonical_asset_id(_mv(pvals,r,ph['pipe_id'])),'up':up,'down':dn,
                      'up_key':asset_key(up),'down_key':asset_key(dn),
                      'existing':any(_mv(pvals,r,ph[x]) not in (None,'') for x in ('video length','video date','video w/o','video truck','video operator')),
                      'existing_wo':digits(_mv(pvals,r,ph['video w/o'])),
                      'clean_existing':any(_mv(pvals,r,ph[x]) not in (None,'') for x in ('clean wheel walk','clean date','clean w/o','clean truck','clean operator')),
                      'clean_existing_wo':digits(_mv(pvals,r,ph['clean w/o']))}
                if item['pipe_id']: pipe_by_id[asset_key(item['pipe_id'])]=item
                pipes[(item['up_key'],item['down_key'])]=item
                pipes.setdefault((item['down_key'],item['up_key']),{**item,'reverse':True})
            ms=wb.Worksheets(manhole_sheet_name); ms_name=str(ms.Name); mr=2
            mvals=_sheet_matrix(ms); mh0=_header_map_matrix(mvals,mr)
            mh={'st_id':mh0['mh id'][0],'date':mh0['date'][0],'w/o':mh0['w o'][0],
                'truck':mh0['truck'][0],'operator':mh0['operator'][0],
                'notes':mh0.get('notes',[None])[0]}
            manholes={}
            manholes_by_number={}
            for r in range(mr+1,len(mvals)+1):
                sid=canonical_asset_id(_mv(mvals,r,mh['st_id']))
                if sid:
                    item={'row':r,'asset':sid,'asset_key':asset_key(sid),'existing':any(_mv(mvals,r,mh[x]) not in (None,'') for x in ('date','w/o','truck','operator')),'existing_wo':digits(_mv(mvals,r,mh['w/o']))}
                    manholes[item['asset_key']]=item
                    manholes_by_number.setdefault(asset_number(sid),[]).append(item)
            truck_counts={}; operator_counts={}
            for vals,row,col in ((pvals,pr,ph['clean truck']),(pvals,pr,ph['video truck']),(mvals,mr,mh['truck'])):
                for rr in range(row+1,len(vals)+1):
                    _add_count(truck_counts,_mv(vals,rr,col),'truck')
            for vals,row,col in ((pvals,pr,ph['clean operator']),(pvals,pr,ph['video operator']),(mvals,mr,mh['operator'])):
                for rr in range(row+1,len(vals)+1): _add_count(operator_counts,_mv(vals,rr,col),'operator')
            _merge_entry_history(truck_counts,operator_counts)
            return {'profile':profile,'pipes':pipes,'pipe_by_id':pipe_by_id,'manholes':manholes,'trucks':set(truck_counts),
                    'truck_counts':truck_counts,'operator_counts':operator_counts,
                    'manholes_by_number':manholes_by_number,
                    'pipe_items':list({item['row']:item for item in pipes.values() if not item.get('reverse')}.values()),
                    'pipe_sheet':ps_name,'manhole_sheet':ms_name,'pipe_headers':ph,'manhole_headers':mh}
        # Reno pipes: retain the established v14-compatible reader and layout.
        ps = wb.Worksheets('Pipes')
        ps_name=str(ps.Name); pvals=_sheet_matrix(ps)
        pr, ph = _locate_headers_matrix(pvals, ['pipe_id','upstream','downstream','length','video length','date','w/o','truck','operator'],ps_name)
        pipes = {}
        pipe_by_id = {}
        for r in range(pr + 1,len(pvals)+1):
            up,dn=digits(_mv(pvals,r,ph['upstream'])),digits(_mv(pvals,r,ph['downstream']))
            if not up or not dn: continue
            expected=parse_float(_mv(pvals,r,ph['length']))
            item={'row':r,'expected':expected,'pipe_id':digits(_mv(pvals,r,ph['pipe_id'])),'up':up,'down':dn,
                  'existing':any(_mv(pvals,r,ph[x]) not in (None,'') for x in ('video length','date','w/o','truck','operator')),
                  'existing_wo':digits(_mv(pvals,r,ph['w/o']))}
            if item['pipe_id']:
                pipe_by_id[item['pipe_id']] = item
            pipes[(up, dn)] = item
            pipes.setdefault((dn, up), {**item, 'reverse': True})
        # Manholes
        ms = wb.Worksheets('Manholes')
        ms_name=str(ms.Name); mvals=_sheet_matrix(ms)
        mr,mh=_locate_headers_matrix(mvals,['st_id','date','w/o','truck','operator'],ms_name)
        manholes = {}
        for r in range(mr+1,len(mvals)+1):
            sid=digits(_mv(mvals,r,mh['st_id']))
            if sid: manholes[sid] = {'row': r,
                                     'existing':any(_mv(mvals,r,mh[x]) not in (None,'') for x in ('date','w/o','truck','operator')),
                                     'existing_wo':digits(_mv(mvals,r,mh['w/o']))}
        # Existing fleet codes are useful as a gentle OCR prior. They are not a hard whitelist.
        truck_counts={}; operator_counts={}
        for vals,header_row,hr in ((pvals,pr,ph),(mvals,mr,mh)):
            tc = hr.get('truck')
            if not tc: continue
            for rr in range(header_row+1,len(vals)+1):
                _add_count(truck_counts,_mv(vals,rr,tc),'truck')
            oc=hr.get('operator')
            if oc:
                for rr in range(header_row+1,len(vals)+1): _add_count(operator_counts,_mv(vals,rr,oc),'operator')
        _merge_entry_history(truck_counts,operator_counts)
        return {'profile':'reno','pipes': pipes, 'pipe_by_id': pipe_by_id, 'manholes': manholes,
                'trucks':set(truck_counts),'truck_counts':truck_counts,'operator_counts':operator_counts}
    finally:
        # Cleanup must never replace a successful read or hide the original error.
        if wb:
            try: wb.Close(False)
            except Exception: pass
        try: excel.Quit()
        except Exception: pass


def render_page(page, scale=2.0):
    page_no=getattr(page,'number',None)
    cache_path=''
    if _PAGE_CACHE_FOLDER and page_no is not None:
        cache_path=os.path.join(_PAGE_CACHE_FOLDER,f'page_{int(page_no)+1}_scale_{str(scale).replace(".","_")}.png')
        if os.path.exists(cache_path):
            try: return np.array(Image.open(cache_path).convert('RGB'))
            except Exception: pass
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
    arr=np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    if cache_path:
        try: Image.fromarray(arr).save(cache_path,format='PNG')
        except Exception: pass
    return arr


def ocr_text(img, psm=6):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return cached_ocr_string(gray, config=f'--psm {psm}')


def orient_and_classify(page):
    """Classify pages with work-order detection biased toward the fixed form layout.

    A work-order page starts a new group. We do not rely only on OCR reading the
    words 'Work Order Number': a 5-digit value in the known upper-left W/O box is
    enough to treat the page as a work order. This makes new groups much harder to miss.
    """
    base = render_page(page, 1.25)
    h, w = base.shape[:2]

    # Trouble tickets have a very distinctive printed title near the top.
    top = base[:int(h*.38), :]
    top_txt = ocr_text(top, 11)
    low_top = top_txt.lower()
    if 'trouble ticket' in low_top:
        return base, 0, top_txt, 'trouble'

    # Work-order form: check the fixed 5-digit number box independently of label OCR.
    wo_crop = base[int(h*.045):int(h*.135), int(w*.055):int(w*.36)]
    g = cv2.cvtColor(wo_crop, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=1.7, fy=1.7, interpolation=cv2.INTER_CUBIC)
    wo_hits = []
    for psm in (6,7,11,13):
        t = cached_ocr_string(g, config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
        wo_hits.extend(re.findall(r'\d{5}', t))
    if wo_hits or 'work order number' in low_top or ('operator' in low_top and ('vehicle' in low_top or 'support' in low_top)):
        return base, 0, top_txt, 'workorder'

    # Survey lists are landscape in the source packet. Rotate portrait render into readable landscape.
    arr = np.array(Image.fromarray(base).rotate(270, expand=True))
    txt = ocr_text(arr, 11)
    l = txt.lower()
    if 'trouble ticket' in l:
        return arr, 270, txt, 'trouble'
    if ('mainline survey' in l or 'psr' in l or
        ('up node' in l and 'down node' in l) or 'surveyed length' in l):
        return arr, 270, txt, 'pipes'
    if ('node survey' in l or 'node number' in l or 'report survey count' in l):
        return arr, 270, txt, 'manholes'
    return arr, 270, txt, 'other'


def classify_for_profile(page, profile):
    """Use the project profile to recognize both portrait and rotated list pages."""
    if profile not in ('year15', 'phase2_year1'):
        return orient_and_classify(page)
    base=render_page(page,1.25); h,w=base.shape[:2]
    top_txt=ocr_text(base[:int(h*.40),:],11); low=top_txt.lower()
    if 'trouble ticket' in low:
        return base,0,top_txt,'trouble'
    wo_crop=base[int(h*.035):int(h*.135),int(w*.04):int(w*.36)]
    wo_digits=''.join(_ocr_digits(wo_crop,False)) if False else ''
    if 'work order number' in low or ('operator' in low and ('vehicle' in low or 'support' in low)):
        return base,0,top_txt,'workorder'
    candidates=[]
    for deg in (0,270,90):
        arr=base if deg==0 else np.array(Image.fromarray(base).rotate(deg,expand=True))
        txt=ocr_text(arr,11); l=txt.lower()
        norm=re.sub(r'[^a-z0-9]+',' ',l)
        score=max(norm.count('upstream'),norm.count('up mh'))+max(norm.count('downstream'),norm.count('dn mh'))
        # OCR often drops the final k in Walk or prefixes DN_MH with a stray I.
        # Tall, wrapped headers can make Tesseract return the words Wheel, Walk,
        # Cleaning, and Date far apart in its reading order.  Treat the paired
        # words as the same header signal even when they are not adjacent.
        cleaning_header=(
            'wheel wal' in norm or 'wheelwalk' in norm or 'cleaning date' in norm or
            ('wheel' in norm and 'walk' in norm) or
            ('cleaning' in norm and 'date' in norm)
        )
        if cleaning_header and ('project yea' in norm or 'field crew' in norm or score): kind='cleaning'; s=25+score
        elif 'manhole number' in norm or ('drainage area' in norm and 'street' in norm and 'date' in norm): kind='manholes'; s=20
        elif ('length surveyed' in norm or 'surveyed length' in norm) and score: kind='pipes'; s=20+score
        else: kind='other'; s=sum(x in l for x in ('up mh','dn mh','wheel walk','manhole number','length surveyed'))
        candidates.append((s,arr,deg,txt,kind))
    _,arr,deg,txt,kind=max(candidates,key=lambda x:x[0])
    return arr,deg,txt,kind

def _best_ocr_text(img, psms=(6,7,11,13), whitelist=None):
    """Return the most useful non-empty OCR result from a small crop."""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, None, fx=1.35, fy=1.35, interpolation=cv2.INTER_CUBIC)
    variants = [gray]
    try:
        variants.append(cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
    except Exception:
        pass
    candidates = []
    for im in variants:
        for psm in psms:
            cfg = f'--psm {psm}'
            if whitelist:
                cfg += f' -c tessedit_char_whitelist={whitelist}'
            txt = cached_ocr_string(im, config=cfg).strip().replace('\n', ' ')
            txt = re.sub(r'\s+', ' ', txt).strip()
            if txt:
                candidates.append(txt)
    if not candidates:
        return ''
    # Prefer text with letters/digits and fewer OCR punctuation artifacts.
    return max(candidates, key=lambda x: (sum(ch.isalnum() for ch in x), -len(x)))


def _ticket_crop(img, x1, y1, x2, y2):
    """Crop a trouble-ticket field using form-relative coordinates."""
    h,w=img.shape[:2]
    return img[max(0,int(h*y1)):min(h,int(h*y2)),max(0,int(w*x1)):min(w,int(w*x2))]


def _clean_ticket_text(value):
    text=str(value or '').replace('|',' ').replace('_',' ')
    text=re.sub(r'\s+',' ',text).strip(' .:-')
    text=re.sub(r'^[^A-Za-z0-9]+|[^A-Za-z0-9]+$','',text).strip()
    return text


def _ticket_field_text(img, psms=(11,), whitelist=None, preferred_digits=None):
    """OCR clean printed ticket cells without enlarging their ruled borders."""
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    variants=[gray]
    try: variants.append(cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1])
    except Exception: pass
    candidates=[]
    for variant in variants:
        for psm in psms:
            cfg=f'--psm {psm}'
            if whitelist: cfg+=f' -c tessedit_char_whitelist={whitelist}'
            value=re.sub(r'\s+',' ',cached_ocr_string(variant,config=cfg)).strip()
            if value: candidates.append((psm,value))
    if not candidates: return ''
    if preferred_digits:
        exact=[(psm,value) for psm,value in candidates if len(digits(value))==preferred_digits]
        if exact:
            rank={11:0,7:1,6:2,13:3}
            return min(exact,key=lambda item:rank.get(item[0],9))[1]
    # The unthresholded PSM-11 result is normally cleanest on this printed form;
    # thresholded variants exist as fallbacks for faint scans.
    return candidates[0][1]


def _ticket_service_types(img):
    """Read the three X boxes without treating the printed grid as a mark."""
    choices=[('Vac Truck',.592,.412,.690,.442),
             ('Pipe Survey',.692,.412,.802,.442),
             ('MH Survey',.805,.412,.915,.442)]
    found=[]
    for label,x1,y1,x2,y2 in choices:
        crop=_ticket_crop(img,x1,y1,x2,y2)
        h,w=crop.shape[:2]
        # Remove the cell borders before OCR/density scoring.
        crop=crop[int(h*.08):int(h*.70),int(w*.12):int(w*.88)]
        gray=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
        mark=cached_ocr_string(gray,config='--psm 10 -c tessedit_char_whitelist=Xx').strip()
        dark=float(np.mean(gray<105)) if gray.size else 0.0
        if 'x' in mark.lower() or dark>.018:
            found.append(label)
    return ', '.join(found)


def legacy_trouble_ticket_key(ticket):
    """Version 60 content key, retained only to migrate existing workbooks."""
    core=[fmt_date(ticket.get('date')),ticket.get('reported_by'),ticket.get('pipe_id'),
          ticket.get('street_name'),ticket.get('panel'),ticket.get('area'),
          ticket.get('service_type'),ticket.get('upstream'),ticket.get('downstream'),
          ticket.get('map_length'),ticket.get('pipe_size'),ticket.get('description')]
    normalized='|'.join(re.sub(r'[^A-Z0-9.]','',str(v or '').upper()) for v in core)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def trouble_ticket_key(ticket):
    """Identify the actual scanned page, not the asset or issue wording."""
    page_hash=str(ticket.get('source_page_hash') or '').strip().lower()
    if page_hash: return 'PAGE:'+page_hash
    # Manually reconstructed tickets without a page hash remain deterministic,
    # but are namespaced so they never collide with legacy v60 content keys.
    return 'CONTENT:'+legacy_trouble_ticket_key(ticket)


def trouble_ticket_asset_key(ticket):
    """Group follow-ups beneath the previous ticket for the same pipe/manhole."""
    pipe=asset_key(ticket.get('pipe_id'))
    if pipe: return 'PIPE:'+pipe
    up=asset_key(ticket.get('upstream')); down=asset_key(ticket.get('downstream'))
    if up or down: return 'NODES:'+('|'.join(x for x in (up,down) if x))
    return ''


def trouble_ticket_status(ticket):
    missing=[]
    if not ticket.get('date'): missing.append('date')
    if not ticket.get('pipe_id'): missing.append('Pipe/MH ID')
    if not ticket.get('operator'): missing.append('operator')
    if not ticket.get('description'): missing.append('description')
    return 'Review missing ' + ', '.join(missing) if missing else 'Ready for Trouble Tickets.xlsx'


def parse_trouble_ticket(page, page_number, current_wo=None, source_pdf=''):
    """Extract every labeled field from the fixed Consor trouble-ticket form."""
    # The form uses small condensed print; 2.5x keeps IDs and location text crisp.
    img=render_page(page,2.5)
    text=lambda coords,psms=(11,),whitelist=None,preferred_digits=None: _clean_ticket_text(
        _ticket_field_text(_ticket_crop(img,*coords),psms,whitelist,preferred_digits))
    reported=text((.085,.242,.360,.268),(11,))
    pipe_id=digits(text((.360,.242,.690,.268),(6,7,11,13),'0123456789',9))
    date_text=text((.690,.242,.915,.268),(6,7,11),'0123456789/-')
    ticket_date=parse_date_text(date_text)
    expected_date=(current_wo or {}).get('date')
    if isinstance(ticket_date,datetime) and isinstance(expected_date,datetime):
        if abs((ticket_date-expected_date).days)>45: ticket_date=expected_date
    ticket={
        'date':ticket_date,
        'reported_by':reported,
        'operator':reported or str((current_wo or {}).get('operator') or '').strip(),
        'pipe_id':pipe_id,
        'street_name':text((.085,.307,.690,.337),(11,)),
        'panel':text((.690,.307,.915,.337),(11,)),
        'area':text((.085,.412,.590,.442),(11,)),
        'service_type':_ticket_service_types(img),
        'upstream':canonical_asset_id(text((.085,.500,.360,.560),(11,))),
        'downstream':canonical_asset_id(text((.360,.500,.622,.560),(11,))),
        'map_length':parse_float(text((.622,.500,.718,.560),(11,),'0123456789.')),
        'pipe_size':text((.718,.500,.915,.560),(11,)),
        'description':text((.245,.582,.915,.800),(11,)),
        'wo':str((current_wo or {}).get('wo') or '').strip(),
        'truck':str((current_wo or {}).get('truck') or '').strip(),
        'tracker_status':'Open',
        'resolution_notes':'',
        'source_pdf':os.path.basename(source_pdf),
        'source_page':page_number,
        'source_page_hash':hashlib.sha256(img.tobytes()).hexdigest(),
    }
    # A readable ticket date should win; the confirmed work-order date is a safe
    # fallback only when OCR fails completely.
    if not ticket['date'] and isinstance((current_wo or {}).get('date'),datetime):
        ticket['date']=(current_wo or {}).get('date')
    ticket['ticket_key']=trouble_ticket_key(ticket)
    ticket['review_status']=trouble_ticket_status(ticket)
    return ticket


def _clean_operator_guess(raw):
    """Clean OCR from the handwritten Operator value box.

    The crop is intentionally tight, but handwriting OCR can still hallucinate pieces
    of the printed 'Operator:' label or nearby ruled lines.  Keep the most name-like
    words and apply only very conservative cleanup.  Confirmed names are still shown
    in an editable popup before anything is written to Excel.
    """
    raw = str(raw or '')
    # Remove both the full printed label and partial OCR fragments. These labels
    # are never valid parts of a person's name.
    raw = re.sub(r'(?i)\b(?:operator|perator|erator|rator|v?perat(?:or|0r)|vperg?i?or)\b\s*[:|.]?\s*', ' ', raw)
    raw = re.split(r'(?i)\b(?:helper|vehicle|support)\b', raw)[0]
    raw = re.sub(r"[^A-Za-z .'-]", ' ', raw)
    raw = re.sub(r'\s+', ' ', raw).strip(' .-|')

    parts = [p.strip(".'-") for p in raw.split()]
    label_fragments={'operator','perator','erator','rator','operato','oper'}
    parts = [p for p in parts if len(re.sub(r'[^A-Za-z]', '', p)) >= 2 and p.lower() not in label_fragments]
    if not parts:
        return ''

    # The operator value is a person's name.  When OCR picks up junk before it,
    # the last two substantial words are normally the handwritten first/last name.
    if len(parts) >= 2:
        parts = parts[-2:]
    return ' '.join(parts).strip()


def _normalize_truck(raw):
    """Normalize OCR from the *tight Vehicle/Support value box* to AA00.

    Truck codes are exactly two letters + two digits.  Handwriting OCR often returns
    CT01 as strings such as ``CTO}``, ``CTO|`` or ``CTOl``.  Preserve those glyphs
    long enough to normalize them instead of deleting them and accidentally accepting
    a valid-looking code from unrelated nearby text.
    """
    raw = str(raw or '').upper().strip()
    raw = re.sub(r'(?i)VEHICLE\s*/?\s*SUPPORT\s*[:|]?', ' ', raw)

    # Common punctuation/glyph confusions seen in handwritten two-digit suffixes.
    raw = raw.translate(str.maketrans({
        '@':'0', 'O':'O',  # O is converted contextually below when a digit is expected
        '}':'1', ']':'1', '|':'1', '!':'1', 'L':'L',
    }))

    # Build short candidate runs without joining distant words together.
    tokens = re.findall(r'[A-Z0-9@}\]|!]{3,6}', raw)
    if not tokens:
        compact = re.sub(r'[^A-Z0-9@}\]|!]', '', raw)
        if compact:
            tokens = [compact]

    letter_map = {'0':'O', '1':'I', '5':'S', '8':'B'}
    digit_map = {'O':'0', 'Q':'0', 'D':'0', 'I':'1', 'L':'1', 'Z':'2', 'S':'5', 'B':'8',
                 '@':'0', '}':'1', ']':'1', '|':'1', '!':'1'}

    for tok in tokens:
        # Sliding windows allow CTO} -> CT01 while ignoring trailing ruled-line junk.
        for i in range(max(1, len(tok)-3)):
            w = tok[i:i+4]
            if len(w) != 4:
                continue
            c=list(w)
            for j in (0,1):
                if c[j].isdigit():
                    c[j]=letter_map.get(c[j], c[j])
            for j in (2,3):
                c[j]=digit_map.get(c[j], c[j])
            candidate=''.join(c)
            if re.fullmatch(r'[A-Z]{2}\d{2}', candidate):
                return candidate
    return ''

def ocr_workorder_guesses(page, master_index=None):
    """Read the Work Order form and PRE-FILL the confirmation dialog.

    These forms contain handwriting, so OCR is only a best guess. The popup remains
    editable, but it should never force the user to retype values that OCR did find.
    """
    img = render_page(page, 3.0)
    h, w = img.shape[:2]
    def crop(x1,y1,x2,y2):
        return img[max(0,int(y1*h)):min(h,int(y2*h)), max(0,int(x1*w)):min(w,int(x2*w))]

    profile=(master_index or {}).get('profile','reno')
    # All projects use the same work-order form, but scans can be vertically
    # shifted. Try value-only crops at every observed position and select the
    # crop with the strongest internal OCR agreement.
    universal_wo_crops=[
        crop(.11,.052,.31,.082),  # Phase 2 / current form position
        crop(.10,.060,.315,.110), # Reno value box including lower shift
        crop(.11,.070,.31,.105),  # Reno tight handwritten value
        crop(.11,.012,.31,.052),  # handwriting above the printed box
    ]
    if profile in ('year15', 'phase2_year1'):
        normal_wo=crop(.055,.040,.325,.082)
        upper_wo=crop(.055,.000,.325,.045)
        candidate_wo_crops=universal_wo_crops+[normal_wo,upper_wo]
        op_crop=crop(.075,.323,.505,.370)
        veh_crop=crop(.130,.364,.370,.398)
    else:
        candidate_wo_crops=universal_wo_crops+[crop(.10,.060,.315,.110)]
        op_crop=crop(.075,.350,.405,.386)
        veh_crop=crop(.190,.382,.300,.410)
    # Work order number: isolate the handwritten number, then use an ensemble.
    wo_crop=candidate_wo_crops[0]
    crop_results=[]
    for candidate_crop in candidate_wo_crops:
        gray=cv2.cvtColor(candidate_crop,cv2.COLOR_RGB2GRAY)
        gray=cv2.resize(gray,None,fx=2.4,fy=2.4,interpolation=cv2.INTER_CUBIC)
        hits=[]
        for psm in (6,7,8,11,13):
            t=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
            hits+=re.findall(r'\d{4,5}',t)
        valid=[x for x in hits if len(x) in (4,5)]
        if valid:
            winner=max(set(valid),key=lambda x:(valid.count(x),len(x)))
            crop_results.append((valid.count(winner),len(valid),len(winner),winner,candidate_crop))
    if crop_results:
        agreement,total,digits_count,wo,wo_crop=max(crop_results,key=lambda x:(x[0],x[1],x[2]))
    else:
        wo=''
    # A broader crop sometimes reads one or two digits that the tight crop misses.
    if not wo:
        broad = _best_ocr_text(crop(.05,.045,.36,.135), psms=(6,11,12,13),whitelist='0123456789')
        exact=re.findall(r'\d{4,5}',broad)
        wo=exact[0] if exact else ''

    date_txt = _best_ocr_text(crop(.055,.115,.35,.190), psms=(6,11))
    date = parse_date_text(date_txt)

    # Read ONLY the handwritten value portion of the Operator box.  Tesseract is weak
    # on handwriting, so use several preprocessing variants and prefer candidates that
    # look like a human name instead of accepting the first OCR string.
    og = cv2.cvtColor(op_crop, cv2.COLOR_RGB2GRAY)
    og = cv2.resize(og, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    op_variants = [og]
    op_variants.append(cv2.threshold(og, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
    op_variants.append(cv2.adaptiveThreshold(og,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,9))
    op_candidates=[]
    for ov in op_variants:
        for psm in (7, 13, 6, 11):
            raw = cached_ocr_string(ov, config=f'--psm {psm}').strip().replace('\n',' ')
            c = _clean_operator_guess(raw)
            if c:
                op_candidates.append(c)

    def name_score(c):
        words=[w for w in re.findall(r"[A-Za-z][A-Za-z.'-]*", c) if len(re.sub(r'[^A-Za-z]','',w))>=2]
        if not words: return -999
        # Real names on these forms are short. Penalize OCR garbage and odd capitalization.
        score = 0
        score += 5 if 1 <= len(words) <= 3 else -4*abs(len(words)-2)
        score += sum(2 for w in words if w[:1].isupper())
        score -= sum(2 for w in words if len(w) > 14)
        score -= max(0, len(c)-28) * .25
        # Consensus matters more than a single noisy OCR pass.
        norm=' '.join(w.lower() for w in words)
        score += 3 * sum(1 for x in op_candidates if ' '.join(re.findall(r'[A-Za-z]+',x.lower())) == norm)
        return score

    operator = max(op_candidates, key=name_score) if op_candidates else ''
    # Known close OCR error from the first work order: Ales -> Alex.  This remains editable.
    operator = re.sub(r'(?i)^Ales(?=\s+Martinez\b)', 'Alex', operator)
    # Tesseract commonly reads the handwritten Anthony as Avthony / Autho Ay.
    # Compare compact letter-only OCR candidates to this confirmed operator name.
    def _lev(a,b):
        prev=list(range(len(b)+1))
        for i,ca in enumerate(a,1):
            cur=[i]
            for j,cb in enumerate(b,1):
                cur.append(min(cur[-1]+1, prev[j]+1, prev[j-1]+(ca!=cb)))
            prev=cur
        return prev[-1]
    for c in op_candidates:
        compact=''.join(re.findall(r'[A-Za-z]+', c)).lower()
        # Also test each word-sized segment so printed-label leftovers do not matter.
        segments=[compact] + [x.lower() for x in re.findall(r'[A-Za-z]{4,}', c)]
        if any(_lev(seg, 'anthony') <= 2 for seg in segments if 5 <= len(seg) <= 9):
            operator='Anthony'
            break
        if any(_lev(seg, 'nathan') <= 2 for seg in segments if 5 <= len(seg) <= 8):
            operator='Nathan'
            break

    # Learn from this master's prior entries and from values the user previously
    # confirmed. History only applies when the handwriting OCR is already close.
    known_operators=(master_index or {}).get('operator_counts',{})
    def _person_key(value): return ''.join(re.findall(r'[a-z]',str(value).lower()))
    learned=[]
    for known,count in known_operators.items():
        kk=_person_key(known)
        if len(kk)<3: continue
        best=min((_lev(_person_key(c),kk) for c in op_candidates if _person_key(c)),default=999)
        allowed=1 if len(kk)<=5 else 2 if len(kk)<=9 else 3
        if best<=allowed: learned.append((best,-min(int(count),20),known))
    if learned:
        operator=min(learned)[2]

    # Vehicle/Support can contain more than one code on the row (e.g. CT01 and ST08).
    # The Truck is the FIRST handwritten code immediately after the printed label, so crop
    # tightly around that first value and never include the second support-vehicle code.
    vg = cv2.cvtColor(veh_crop, cv2.COLOR_RGB2GRAY)
    vg = cv2.resize(vg, None, fx=5.0, fy=5.0, interpolation=cv2.INTER_CUBIC)
    veh_variants=[vg,
                  cv2.threshold(vg,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1],
                  cv2.adaptiveThreshold(vg,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,7)]
    truck_candidates=[]
    for vim in veh_variants:
        for psm in (7,8,13,6):
            for cfg_extra in ('', ' -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
                raw=cached_ocr_string(vim, config=f'--psm {psm}{cfg_extra}').strip().replace('\n',' ')
                c=_normalize_truck(raw)
                if c: truck_candidates.append(c)

    known_trucks = set((master_index or {}).get('trucks', set()))
    truck_counts=(master_index or {}).get('truck_counts',{})
    def edit1(a,b):
        return len(a)==len(b) and sum(x!=y for x,y in zip(a,b))
    def truck_score(c):
        score = 3 * truck_candidates.count(c)
        if c in known_trucks: score += 8
        score += min(int(truck_counts.get(c,0)),10)
        # If OCR gives ET01 but the master already contains CT01, prefer the known one
        # only when it is exactly one character away and shares the numeric suffix.
        return score
    truck = max(set(truck_candidates), key=truck_score) if truck_candidates else ''
    if truck and known_trucks and truck not in known_trucks:
        close=[k for k in known_trucks if k[2:]==truck[2:] and edit1(k,truck)==1]
        if len(close)==1:
            truck=close[0]

    # Small crops are carried into the confirmation dialog so the handwriting is visible
    # directly beside the editable OCR fields.  Keep the work-order preview independent
    # of the tight crop selected for OCR: shifted forms can place the first digits left
    # of an otherwise successful OCR crop (for example, 11976 appeared as 976 onscreen).
    # This wider value-box crop shows the complete handwritten number without changing
    # the OCR ensemble or its selected candidate.
    wo_preview = crop(.04,.043,.325,.090)
    op_preview = op_crop
    truck_preview = veh_crop
    return {'wo': wo, 'date': date, 'truck': truck, 'operator': operator, 'preview': img,
            'wo_preview': wo_preview, 'operator_preview': op_preview, 'truck_preview': truck_preview}

def _ocr_digits(cell_img, decimal=False, fast_plain=False):
    if cell_img is None or cell_img.size == 0:
        return []
    gray = cv2.cvtColor(cell_img, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    variants = [gray, cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]]
    if not fast_plain:
        # Legacy highlighted lists benefit from extra green-channel variants.
        try:
            green=cv2.normalize(cell_img[:,:,1],None,0,255,cv2.NORM_MINMAX)
            green=cv2.resize(green,None,fx=1.8,fy=1.8,interpolation=cv2.INTER_CUBIC)
            variants.extend(cv2.threshold(green,t,255,cv2.THRESH_BINARY)[1] for t in (120,140,160))
        except Exception:
            pass
    wl = '0123456789.' if decimal else '0123456789'
    found=[]
    for im in variants:
        for psm in ((7,) if fast_plain else (7,6)):
            t=cached_ocr_string(im, config=f'--psm {psm} -c tessedit_char_whitelist={wl}').strip()
            if decimal:
                for x in re.findall(r'\d+(?:\.\d+)?', t.replace(',','')):
                    try: found.append(float(x))
                    except: pass
            else:
                found.extend(re.findall(r'\d+', t))
    return found


def _edit_distance(a,b):
    a=str(a); b=str(b)
    if a==b: return 0
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):
            cur.append(min(cur[-1]+1, prev[j]+1, prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]


def _best_known_id(candidates, known, max_dist=1):
    # Exact is preferred. Fuzzy recovery remains available only after the caller
    # has ruled out the explicit existing-ID-plus-one-letter new-asset pattern.
    clean=[]
    for c in candidates:
        d=digits(c)
        if d: clean.append(d)
    for c in clean:
        if c in known: return c
    best=None; score=999
    for c in clean:
        for k in known:
            if abs(len(c)-len(k))>1: continue
            dist=_edit_distance(c,k)
            if dist<score: best,score=k,dist
    return best if best and score<=max_dist else ''


def _ocr_asset_candidates(cell_img, fast_plain=False):
    """Return full-ID OCR candidates, retaining letter prefixes and digits."""
    if cell_img is None or cell_img.size==0: return []
    rgb=cv2.resize(cell_img,None,fx=2.4,fy=2.4,interpolation=cv2.INTER_CUBIC)
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    variants=[gray,cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    if not fast_plain:
        try:
            green=cv2.normalize(rgb[:,:,1],None,0,255,cv2.NORM_MINMAX)
            variants.extend(cv2.threshold(green,t,255,cv2.THRESH_BINARY)[1] for t in (125,140,155))
        except Exception: pass
    out=[]
    for vi,im in enumerate(variants):
        for psm in ((7,) if fast_plain else ((7,6) if vi<2 else (7,))):
            txt=cached_ocr_string(im,config=f'--psm {psm}').strip().replace('\n',' ')
            if txt:
                out.extend(_ocr_id_text_variants(txt))
                out.extend(re.findall(r'\d{2,7}',txt))
    return list(dict.fromkeys(x for x in out if x))


def _ocr_known_r2_candidates(cell_img, known_items):
    """Recover exact known R2 IDs when the prefix becomes an OCR lookalike.

    This is intentionally a master-constrained fallback. It never creates a new
    identifier: every returned value must already be a complete endpoint in the
    selected master. A separated trailing lowercase ``r`` is also ignored because
    Tesseract can read the right grid rule as that extra character.
    """
    if cell_img is None or cell_img.size==0: return []
    known={asset_key(key):value for key,value in known_items.items()}
    known_r2={key for key in known if re.fullmatch(r'R2\d{3,8}[A-Z]?',key)}
    if not known_r2: return []
    width=cell_img.shape[1]
    pad=max(2,int(round(width*.04)))
    if width>pad*2+4: cell_img=cell_img[:,pad:width-pad]
    rgb=cv2.resize(cell_img,None,fx=3.2,fy=3.2,interpolation=cv2.INTER_CUBIC)
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    variants=[gray,cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    out=[]
    for image in variants:
        for psm in (7,6):
            text=cached_ocr_string(
                image,
                config=(f'--psm {psm} '
                        '-c tessedit_char_whitelist=Rr2-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            ).strip()
            key=asset_key(text)
            if key in known_r2:
                out.append(known[key])
                continue
            # R2-427 commonly OCRs as 32-427, 22-427, 52-427, or B2-427.
            # Preserve an attached suffix while repairing only the leading glyph.
            match=re.fullmatch(r'[A-Z0-9]2(\d{3,8}[A-Z]?)',key)
            if match:
                candidate='R2'+match.group(1)
                if candidate in known_r2:
                    out.append(known[candidate])
                    continue
            # Cropping away the grid can remove the bad leading glyph entirely,
            # leaving 2-417 for the printed R2-417.
            match=re.fullmatch(r'2(\d{3,8}[A-Z]?)',key)
            if match:
                candidate='R2'+match.group(1)
                if candidate in known_r2:
                    out.append(known[candidate])
                    continue
            # A separated lowercase r comes from the right-hand grid rule in the
            # attached scan. Do not strip a joined letter, which may be a real
            # new-asset suffix such as R2-414A.
            match=re.fullmatch(r'\s*R2[- ]?(\d{3,8})\s+r\s*',text)
            if match:
                candidate='R2'+match.group(1)
                if candidate in known_r2: out.append(known[candidate])
    return list(dict.fromkeys(out))


def _rank_asset_candidates(observations, known_items, max_full_dist=3, max_number_dist=1):
    """Rank canonical full IDs. Number-only OCR is accepted only when unique."""
    known_keys=list(known_items)
    full=[]; number=[]
    for raw in observations:
        for obs in _ocr_id_text_variants(raw):
            if re.search(r'[A-Z]',obs) and re.search(r'\d',obs): full.append(obs)
            elif obs.isdigit(): number.append(obs)
    scores={}
    for key in known_keys:
        best=999
        for obs in full:
            best=min(best,_edit_distance(obs,key))
        if best<=max_full_dist: scores[key]=best
    # A digit-only observation must resolve to exactly one full known identifier.
    for obs in number:
        ds=[]
        for key in known_keys:
            num=asset_number(key)
            if abs(len(obs)-len(num))<=1:
                d=_edit_distance(obs,num)
                if d<=max_number_dist: ds.append((d,key))
        if ds:
            md=min(d for d,_ in ds); winners={k for d,k in ds if d==md}
            if len(winners)==1:
                key=next(iter(winners)); scores[key]=min(scores.get(key,999),md+2)
    return scores


def _asset_id_parts(value):
    """Split a complete prefixed asset ID into prefix, number, and optional suffix."""
    key=asset_key(value)
    match=re.fullmatch(r'([A-Z]{1,6})(\d{2,8})([A-Z]?)',key)
    return match.groups() if match else None


def _authoritative_asset_candidates(observations,known_items):
    """Keep complete observed IDs whose prefix is already valid for this project."""
    prefixes={parts[0] for key in known_items if (parts:=_asset_id_parts(key))}
    out=[]
    for raw in observations:
        parts=_asset_id_parts(raw)
        if parts and parts[0] in prefixes:
            value=canonical_asset_id(''.join(parts))
            if value not in out: out.append(value)
    return out


def _new_suffix_asset_candidates(observations,known_items):
    """Return IDs made by appending exactly one letter to an existing master ID."""
    known_keys={asset_key(key) for key in known_items}
    out=[]
    for raw in observations:
        key=asset_key(raw)
        if len(key)>=2 and key[-1].isalpha() and key[:-1] in known_keys and key not in known_keys:
            value=canonical_asset_id(key)
            if value not in out: out.append(value)
    return out


def _base_asset_key(value,known_items):
    """Resolve an exact ID or its one-letter suffixed version to the base master key."""
    known_keys={asset_key(key) for key in known_items}
    key=asset_key(value)
    if key in known_keys: return key
    if len(key)>=2 and key[-1].isalpha() and key[:-1] in known_keys: return key[:-1]
    return ''


def _endpoint_base_options(observations,known_items):
    """Return (printed ID, base key, is new suffix) endpoint possibilities."""
    known_keys={asset_key(key) for key in known_items}
    out=[]
    for value in _authoritative_asset_candidates(observations,known_items):
        key=asset_key(value)
        if key in known_keys: out.append((value,key,False))
    for value in _new_suffix_asset_candidates(observations,known_items):
        out.append((value,asset_key(value)[:-1],True))
    return list(dict.fromkeys(out))


def _new_pipe_base_item(up_observations,dn_observations,master_index):
    """Find the existing pipe row that a suffixed endpoint pair is a new version of."""
    known_manhole_ids={}
    for item in master_index.get('pipe_items',[]):
        known_manhole_ids[item['up_key']]=item['up']
        known_manhole_ids[item['down_key']]=item['down']
    for key,item in master_index.get('manholes',{}).items():
        known_manhole_ids[asset_key(key)]=item.get('asset') or str(key)
    up_new=bool(_new_suffix_asset_candidates(up_observations,known_manhole_ids))
    dn_new=bool(_new_suffix_asset_candidates(dn_observations,known_manhole_ids))
    if not (up_new or dn_new): return None

    # Prefer the exact unsuffixed pair when it exists.
    direct={}
    for up_value,up_base,_ in _endpoint_base_options(up_observations,known_manhole_ids):
        for dn_value,dn_base,_ in _endpoint_base_options(dn_observations,known_manhole_ids):
            item=master_index.get('pipes',{}).get((up_base,dn_base))
            if item: direct[item['row']]=item
    if len(direct)==1: return next(iter(direct.values()))
    if len(direct)>1: return None

    # Some legitimate new pipes replace one endpoint with a lettered version of
    # the other endpoint (DE-1234 -> DE-1234A instead of DE-1234 -> DE-1235).
    # In that case retain the printed pair but use the unique closest master pair
    # only to choose where the approved new row should be inserted.
    endpoints={}
    for item in master_index.get('pipe_items',[]):
        endpoints[item['up_key']]=item['up']; endpoints[item['down_key']]=item['down']
    up_scores=_rank_asset_candidates(up_observations,endpoints,max_full_dist=6)
    dn_scores=_rank_asset_candidates(dn_observations,endpoints,max_full_dist=6)
    ranked=[]
    for item in master_index.get('pipe_items',[]):
        if item['up_key'] in up_scores and item['down_key'] in dn_scores:
            ranked.append((up_scores[item['up_key']]+dn_scores[item['down_key']],item))
    if not ranked: return None
    best=min(score for score,_ in ranked)
    winners={item['row']:item for score,item in ranked if score==best}
    return next(iter(winners.values())) if best<=8 and len(winners)==1 else None


def _best_observed_asset_id(observations,known_items):
    """Preserve the strongest complete printed ID for a new-asset review row."""
    known_keys={asset_key(key) for key in known_items}
    candidates=_authoritative_asset_candidates(observations,known_items)
    exact=[value for value in candidates if asset_key(value) in known_keys]
    if exact: return exact[0]
    suffix=_new_suffix_asset_candidates(observations,known_items)
    return suffix[0] if suffix else (candidates[0] if candidates else '')


def _resolve_full_asset(observations, known_items):
    authoritative=_authoritative_asset_candidates(observations,known_items)
    exact={asset_key(value) for value in authoritative} & set(known_items)
    if len(exact)==1:
        return known_items[next(iter(exact))],'Matched'
    if len(exact)>1:
        return None,'AMBIGUOUS ASSET'
    if _new_suffix_asset_candidates(observations,known_items):
        return None,'NEW MANHOLE'
    scores=_rank_asset_candidates(observations,known_items)
    if not scores:
        for raw in observations:
            obs=asset_number(raw)
            if obs and sum(asset_number(k)==obs for k in known_items)>1:
                return None,'AMBIGUOUS ASSET PREFIX'
        return None,'NOT MATCHED'
    best=min(scores.values()); winners=[k for k,v in scores.items() if v==best]
    if len(winners)!=1: return None,'AMBIGUOUS ASSET'
    return known_items[winners[0]],'Matched'


def _resolve_pipe_pair(up_observations,dn_observations,master_index):
    endpoints={}
    for item in master_index.get('pipe_items',[]):
        endpoints[item['up_key']]=item['up']; endpoints[item['down_key']]=item['down']
    known_manhole_ids=dict(endpoints)
    for key,item in master_index.get('manholes',{}).items():
        known_manhole_ids[asset_key(key)]=item.get('asset') or str(key)
    # First honor complete printed endpoint IDs. A new pipe is recognized only
    # when at least one endpoint is an existing manhole ID plus one final letter.
    up_full=_authoritative_asset_candidates(up_observations,known_manhole_ids)
    dn_full=_authoritative_asset_candidates(dn_observations,known_manhole_ids)
    exact_pairs={}
    for up in up_full:
        for dn in dn_full:
            item=master_index.get('pipes',{}).get((asset_key(up),asset_key(dn)))
            if item: exact_pairs[item['row']]=item
    if len(exact_pairs)==1:
        return next(iter(exact_pairs.values())),'Matched'
    if len(exact_pairs)>1:
        return None,'AMBIGUOUS PIPE PAIR'
    if _new_pipe_base_item(up_observations,dn_observations,master_index):
        return None,'NEW PIPE'
    # Pair matching can tolerate more surrounding OCR junk because both endpoints
    # must still form one real master pair; this is safer than loosening single-ID matches.
    up_scores=_rank_asset_candidates(up_observations,endpoints,max_full_dist=6)
    dn_scores=_rank_asset_candidates(dn_observations,endpoints,max_full_dist=6)
    ranked=[]
    for item in master_index.get('pipe_items',[]):
        uk,dk=item['up_key'],item['down_key']
        if uk in up_scores and dk in dn_scores:
            ranked.append((up_scores[uk]+dn_scores[dk],item))
    if not ranked:
        endpoint_keys=list(endpoints)
        for observations in (up_observations,dn_observations):
            for raw in observations:
                obs=asset_number(raw)
                if obs and sum(asset_number(k)==obs for k in endpoint_keys)>1:
                    return None,'AMBIGUOUS PIPE PREFIX'
        return None,'NOT MATCHED'
    best=min(x[0] for x in ranked); winners={x[1]['row']:x[1] for x in ranked if x[0]==best}
    if best>8: return None,'NOT MATCHED'
    if len(winners)!=1: return None,'AMBIGUOUS PIPE PAIR'
    return next(iter(winners.values())),'Matched'


def _parse_sheet_date(cell_img, expected_year=None):
    """Survey-list Date column is YYYY/DD/MM (e.g. 2026/10/08 = 08/10/2026)."""
    if cell_img is None or cell_img.size == 0:
        return None
    gray=cv2.cvtColor(cell_img, cv2.COLOR_RGB2GRAY)
    gray=cv2.resize(gray,None,fx=2.2,fy=2.2,interpolation=cv2.INTER_CUBIC)
    variants=[gray, cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    texts=[]
    for im in variants:
        for psm in (7,6):
            texts.append(cached_ocr_string(im,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/').strip())
    for txt in texts:
        nums=re.findall(r'\d+',txt)
        if len(nums)>=3:
            try:
                a,b,c=map(int,nums[:3])
                # Reno report lists use YYYY/DD/MM. Year 15 lists use M/D/YYYY.
                if a>=2020: y,d,m=a,b,c
                else: m,d,y=a,b,c; y=2000+y if y<100 else y
                if expected_year and y != expected_year:
                    # Year is fixed for a report packet and is a common OCR casualty (2026 -> 2020/2028).
                    y = expected_year
                if 2020 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                    return datetime(y,m,d)
            except: pass
    return None


def _parse_sheet_date_text_candidates(text, expected_date=None):
    """Return candidate sheet dates plus whether the printed year was read exactly.

    OCR frequently damages the 4-digit year while leaving month/day usable.  When
    an expected work-order/report date is available, its year may repair only the
    year component; month/day still come from the printed cell.
    """
    expected_year=expected_date.year if isinstance(expected_date,datetime) else None
    date_text=str(text or '')
    date_text=re.sub(r'(?<=[/-])\s*(\d)\s+(\d)\s*(?=[/-])',r'\1\2',date_text)
    date_text=re.sub(r'\s*([/-])\s*',r'\1',date_text)
    tokens=re.findall(r'\d+',date_text)
    out=[]
    for i in range(max(0,len(tokens)-2)):
        a_s,b_s,c_s=tokens[i:i+3]
        try: a,b,c=map(int,(a_s,b_s,c_s))
        except Exception: continue
        strong=False; repaired=False
        if 2020<=a<=2100:
            y,d,m=a,b,c; strong=len(a_s)==4
        else:
            m,d,y=a,b,c
            if y<100: y=2000+y
            strong=(len(c_s)==4 and 2020<=y<=2100)
        if expected_year and y!=expected_year:
            y=expected_year; repaired=True; strong=False
        if not (2020<=y<=2100 and 1<=m<=12 and 1<=d<=31):
            continue
        try: out.append((datetime(y,m,d),bool(strong and not repaired)))
        except Exception: pass
    return out


def _choose_sheet_date_evidence(texts, expected_date=None):
    """Choose one row date and retain vote strength for table-level reconciliation."""
    candidates=[]
    for txt in texts or []:
        candidates.extend(_parse_sheet_date_text_candidates(txt,expected_date))
    if not candidates:
        return {'date':None,'strong':False,'candidates':[],'votes':{},'strong_votes':{}}
    all_dates=[d for d,_ in candidates]
    strong_dates=[d for d,strong in candidates if strong]
    votes={d:all_dates.count(d) for d in set(all_dates)}
    strong_votes={d:strong_dates.count(d) for d in set(strong_dates)}
    pool=strong_dates or all_dates
    counts={d:pool.count(d) for d in set(pool)}
    most=max(counts.values())
    winners=sorted((d for d,n in counts.items() if n==most))
    if strong_dates:
        chosen=winners[0]
        return {'date':chosen,'strong':True,'candidates':all_dates,'votes':votes,'strong_votes':strong_votes}
    if isinstance(expected_date,datetime) and expected_date in counts:
        chosen=expected_date
    else:
        chosen=winners[0]
    return {'date':chosen,'strong':False,'candidates':all_dates,'votes':votes,'strong_votes':strong_votes}


def _date_outlier_is_well_supported(evidence, dominant_date, expected_date=None):
    """Keep a different date only when independent OCR evidence is strong enough."""
    if not evidence or dominant_date is None: return False
    date=evidence.get('date')
    if date is None or date==dominant_date: return True
    strong_votes=(evidence.get('strong_votes') or {}).get(date,0)
    # When the dominant table date agrees with the confirmed work-order date,
    # require three full-date reads before preserving an outlier. This fixes
    # clipped 8/11/2026 cells that can repeatedly look like 1/1 or 3/11 while
    # still preserving a genuinely different, clearly printed date.
    dominant_matches_expected=(isinstance(expected_date,datetime) and
                     dominant_date.date()==expected_date.date())
    required=3 if dominant_matches_expected else 2
    return strong_votes>=required


def _read_sheet_date_evidence(cell_img, expected_date=None):
    if cell_img is None or getattr(cell_img,'size',0)==0:
        return {'date':None,'strong':False,'candidates':[]}
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    gray=cv2.resize(gray,None,fx=2.2,fy=2.2,interpolation=cv2.INTER_CUBIC)
    variants=[gray,cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    texts=[]
    for im in variants:
        for psm in (7,6):
            texts.append(cached_ocr_string(im,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/').strip())
    return _choose_sheet_date_evidence(texts,expected_date)


def _dominant_sheet_date(evidences, expected_date=None):
    """Return a repeated table date only when several rows independently support it."""
    dates=[ev.get('date') for ev in evidences or [] if ev.get('date') is not None]
    if not dates: return None
    counts={d:dates.count(d) for d in set(dates)}
    if isinstance(expected_date,datetime) and counts.get(expected_date,0)>=3:
        return expected_date
    ranked=sorted(((n,d) for d,n in counts.items()),reverse=True)
    best_n,best_d=ranked[0]
    second_n=ranked[1][0] if len(ranked)>1 else 0
    if best_n>=3 and best_n>second_n:
        return best_d
    return None


def _ocr_gridless_number_candidates(cell_img, decimal=False):
    """OCR a numeric cell after removing printed table rules.

    Total rows often put the digits directly against the bottom border; ordinary
    OCR can then see only one digit.  Morphologically removing horizontal/vertical
    rules keeps the number independent from the row grid.
    """
    if cell_img is None or getattr(cell_img,'size',0)==0: return []
    gray=cv2.cvtColor(cell_img,cv2.COLOR_RGB2GRAY)
    wl='0123456789.' if decimal else '0123456789'
    found=[]
    for threshold in (190,200,210,220):
        inv=cv2.threshold(gray,threshold,255,cv2.THRESH_BINARY_INV)[1]
        hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(8,int(cell_img.shape[1]*.45)),1))
        vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(8,int(cell_img.shape[0]*.45))))
        lines=cv2.bitwise_or(cv2.morphologyEx(inv,cv2.MORPH_OPEN,hk),
                             cv2.morphologyEx(inv,cv2.MORPH_OPEN,vk))
        clean=255-cv2.subtract(inv,lines)
        for psm in (11,6,7):
            raw=cached_ocr_string(clean,config=f'--psm {psm} -c tessedit_char_whitelist={wl}').strip()
            if decimal:
                for value in re.findall(r'\d+(?:\.\d+)?',raw.replace(',','')):
                    try: found.append(float(value))
                    except Exception: pass
            else:
                found.extend(re.findall(r'\d+',raw))
    return found


def _printed_total_value_is_plausible(value, band_count):
    if value is None: return False
    try: numeric=float(value)
    except Exception: return False
    if not (0<numeric<1000000): return False
    # A lone digit from a table with many rows is almost certainly a clipped OCR
    # fragment. Fail closed and ask the user rather than treating it as a total.
    if int(band_count or 0)>=6 and numeric<10: return False
    return True


def _choose_length(cands, expected=None):
    cands=[float(x) for x in cands if 0 < float(x) < 5000]
    if not cands: return None
    if expected and expected > 0:
        # Surveyed length should usually be close to the GIS/master length.
        plausible=[x for x in cands if abs(x-expected)/max(expected,1) < .35]
        if plausible: return min(plausible,key=lambda x: abs(x-expected))
    return cands[-1]


def _choose_cleaning_length(cands, expected=None):
    """Choose a printed wheel-walk value by OCR consensus.

    The master length is used only to break an equal-vote tie.  It never creates
    or substitutes a value that OCR did not actually observe, so legitimate field
    differences remain visible as review warnings.
    """
    rounded=[round(float(x),2) for x in cands if 0<float(x)<5000]
    if not rounded: return None
    counts={value:rounded.count(value) for value in set(rounded)}
    most=max(counts.values())
    winners=[value for value,count in counts.items() if count==most]
    if expected not in (None,0):
        return min(winners,key=lambda value:(abs(value-float(expected)),value))
    return min(winners)


def _choose_printed_total(cands):
    """Return a total-length OCR winner and whether its OCR vote is confident."""
    rounded=[round(float(x),2) for x in cands if 0<float(x)<1000000]
    if not rounded: return None,False
    counts={value:rounded.count(value) for value in set(rounded)}
    most=max(counts.values())
    winners=sorted(value for value,count in counts.items() if count==most)
    if len(winners)!=1: return None,False
    return winners[0],most>=2


def _read_pair_table_printed_total(img,bands,table,value_box,up_box=None,dn_box=None,date_box=None):
    """Read the printed activity total independently from the data-row lengths."""
    result={'found':False,'value':None,'confident':False,'candidates':[],'method':'not found','band_index':None}
    if img is None or not bands or not table or not value_box: return result
    left,right=table; h,w=img.shape[:2]; tw=max(1,right-left)

    def cut(box,y1,y2):
        if not box: return None
        return img[max(0,int(y1)):min(h,int(y2)),
                   max(0,int(left+box[0]*tw)):min(w,int(left+box[1]*tw))]

    def read_value(y1,y2):
        cell=cut(value_box,y1,y2)
        if cell is None or cell.size==0: return []
        found=[]; width=cell.shape[1]
        for ratio in (0,.015,.030,.045,.060):
            pad=max(0,int(round(width*ratio)))
            sample=cell[:,pad:width-pad] if pad and width>pad*2+4 else cell
            found.extend(_ocr_digits(sample,True,fast_plain=True))
        # Total digits commonly touch the grid border, so also remove the printed
        # rules before OCR. This is what recovers 4476 from the 8-11 fixture.
        found.extend(_ocr_gridless_number_candidates(cell,True))
        if not found: found.extend(_ocr_digits(cell,True,fast_plain=False))
        return found

    def neighbor_has_number(box,y1,y2):
        cell=cut(box,y1,y2)
        if cell is None or cell.size==0: return False
        txt=' '.join(ocr_text(cell,psm) for psm in (6,11))
        return bool(re.search(r'\d{2,}',txt))

    def date_signal(y1,y2):
        cell=cut(date_box,y1,y2)
        if cell is None or getattr(cell,'size',0)==0: return False
        return _parse_sheet_date(cell) is not None

    def blank_total_row(y1,y2,method,band_index=None):
        candidates=read_value(y1,y2)
        if not candidates: return None
        if neighbor_has_number(up_box,y1,y2) or neighbor_has_number(dn_box,y1,y2) or date_signal(y1,y2):
            return None
        value,confident=_choose_printed_total(candidates)
        if not _printed_total_value_is_plausible(value,len(bands)):
            value=None; confident=False
        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':method,'band_index':band_index}

    # Explicit TOTAL label, when present.
    tail_start=max(0,len(bands)-4)
    for band_index,(y1,y2) in enumerate(list(bands)[-4:],tail_start):
        row=img[max(0,y1):min(h,y2),max(0,left):min(w,right)]
        if row.size==0: continue
        row_text=' '.join(ocr_text(row,psm) for psm in (6,11)).lower()
        compact=re.sub(r'[^a-z]+','',row_text)
        if not any(token in compact for token in ('total','tota','totai','totl')): continue
        candidates=read_value(y1,y2)
        value,confident=_choose_printed_total(candidates)
        if not _printed_total_value_is_plausible(value,len(bands)):
            value=None; confident=False
        return {'found':True,'value':value,'confident':confident,
                'candidates':candidates,'method':'labelled total row','band_index':band_index}

    # Some B&C sheets include the numeric total as the FINAL DETECTED GRID BAND.
    # v71/v72 incorrectly assumed the total was always below bands[-1], causing
    # 4476 on 8-11-2026 to be skipped and a stray single 4 to be accepted instead.
    in_grid=blank_total_row(bands[-1][0],bands[-1][1],'in-grid footer total',len(bands)-1)
    if in_grid is not None:
        return in_grid

    # Other sheets put one blank footer row immediately below the final detected
    # data band. Keep that path as a fallback.
    typical=float(statistics.median(max(1,b-a) for a,b in bands))
    fy1=max(0,int(bands[-1][1]-typical*.05))
    fy2=min(h,int(bands[-1][1]+typical*2.10))
    below=blank_total_row(fy1,fy2,'blank footer total',None)
    return below if below is not None else result

def _resolve_printed_total_sources(sources):
    """Resolve page total readings into one work-order/activity expected total."""
    sources=list(sources or [])
    found=[source for source in sources if (source.get('info') or {}).get('found')]
    if not found:
        return {'available':False,'value':None,'confident':False,'mode':'not found','pages':[]}
    values=[]; confident=True
    for source in found:
        info=source.get('info') or {}
        value=info.get('value')
        if value is not None: values.append(float(value))
        if not info.get('confident'): confident=False
    pages=[source.get('page') for source in found if source.get('page') is not None]
    if len(found)==1 and len(values)==1:
        total=round(values[0],2); mode='single printed work-order total'
    elif len(found)==len(sources) and len(values)==len(found):
        total=round(sum(values),2); mode='sum of printed page totals'
    elif values:
        total=round(sum(values),2); mode='partial printed page totals'; confident=False
    else:
        total=None; mode='printed total unreadable'; confident=False
    return {'available':True,'value':total,'confident':confident,'mode':mode,'pages':pages}


def _length_total_result(records,expected_total):
    """Compare exactly what is visible in the summary with a verified PDF total."""
    values=[]; missing=0
    for record in records:
        value=record.get('video_length')
        if value is None: missing+=1
        else:
            try: values.append(float(value))
            except Exception: missing+=1
    summary_total=round(sum(values),2)
    expected=None if expected_total is None else round(float(expected_total),2)
    difference=None if expected is None else round(summary_total-expected,2)
    matches=expected is not None and missing==0 and abs(difference)<=.01
    return {'summary_total':summary_total,'expected_total':expected,
            'difference':difference,'missing':missing,'matches':matches}


def _table_row_bands(img, min_y_ratio=.10, max_y_ratio=.86):
    """Find printed horizontal table separators and return row bands between them.

    This avoids cumulative drift from assuming a fixed row height. It works well on scans
    that are slightly stretched, skewed, or produced at different resolutions.
    """
    h,w=img.shape[:2]
    gray=cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    inv=cv2.threshold(gray,210,255,cv2.THRESH_BINARY_INV)[1]
    kernel=cv2.getStructuringElement(cv2.MORPH_RECT,(max(50,int(w*.06)),1))
    hor=cv2.morphologyEx(inv,cv2.MORPH_OPEN,kernel)
    contours,_=cv2.findContours(hor,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    raw=[]
    for c in contours:
        x,y,ww,hh=cv2.boundingRect(c)
        if ww >= w*.58 and hh <= max(12,h*.018) and min_y_ratio*h <= y <= max_y_ratio*h:
            raw.append((y,x,ww,hh))
    if not raw:
        return [], None
    raw.sort()
    # Merge multiple detections belonging to the same thick printed line.
    merged=[]
    for item in raw:
        if merged and abs(item[0]-merged[-1][0]) <= max(3,int(h*.004)):
            old=merged[-1]
            # Keep the longer representative.
            if item[2] > old[2]: merged[-1]=item
        else:
            merged.append(item)
    ys=[r[0]+r[3]//2 for r in merged]
    # Find the longest run of approximately equally-spaced table lines.
    best=[]
    for i in range(len(ys)):
        run=[merged[i]]
        prev=ys[i]
        gaps=[]
        for j in range(i+1,len(ys)):
            gap=ys[j]-prev
            if 12 <= gap <= max(80,int(h*.055)):
                if gaps:
                    med=float(np.median(gaps))
                    if not (med*.60 <= gap <= med*1.45):
                        break
                gaps.append(gap); run.append(merged[j]); prev=ys[j]
            elif gap <= 8:
                continue
            else:
                break
        if len(run)>len(best): best=run
    if len(best)<3:
        best=merged
    # Table left/right from median horizontal rule extents.
    left=int(np.median([x for _,x,ww,hh in best])); right=int(np.median([x+ww for _,x,ww,hh in best]))
    bands=[]
    centers=[y+hh//2 for y,x,ww,hh in best]
    for a,b in zip(centers,centers[1:]):
        if b-a >= 10:
            pad=max(2,int((b-a)*.12))
            bands.append((a+pad,b-pad))
    return bands,(left,right)


def parse_pipe_list(page, master_index, quick_text, on_row=None, on_progress=None):
    """Read Mainline Survey List using PSR -> pipe_id and the printed Surveyed Length column."""
    base=render_page(page,2.5)
    img=np.array(Image.fromarray(base).rotate(270,expand=True))
    h,w=img.shape[:2]
    known=master_index['pipe_by_id']
    expected_date=parse_date_text(quick_text)
    expected_year=expected_date.year if expected_date else None

    bands,table=_table_row_bands(img,.10,.88)
    # Safe fallback for unusual scans; unlike v7, no accumulated fixed-center drift.
    if not bands:
        top,bottom=int(.158*h),int(.80*h)
        step=max(18,int(.0256*h))
        bands=[(y+2,min(y+step-2,bottom)) for y in range(top,bottom,step)]
        table=(int(.055*w),int(.94*w))
    left,right=table
    tw=max(1,right-left)

    rows=[]
    for y1,y2 in bands:
        if on_progress: on_progress()
        # Column positions are relative to the detected printed table, not the page edges.
        date_img=img[y1:y2, max(0,int(left+.035*tw)):min(w,int(left+.125*tw))]
        psr_img=img[y1:y2, max(0,int(left+.120*tw)):min(w,int(left+.215*tw))]
        # IMPORTANT: this is ONLY the final "Surveyed Length" column, not Scheduled Length.
        len_img=img[y1:y2, max(0,int(left+.918*tw)):min(w,int(left+.998*tw))]

        full_pid_candidates=_ocr_asset_candidates(psr_img,fast_plain=False)
        pid_candidates=_ocr_digits(psr_img,False)+full_pid_candidates
        new_options=_new_suffix_asset_candidates(full_pid_candidates,known.keys())
        new_pid=new_options[0] if new_options else ''
        pid='' if new_pid else _best_known_id(pid_candidates,known.keys(),max_dist=1)
        if not pid and not new_pid:
            continue
        d=_parse_sheet_date(date_img,expected_year)
        length_candidates=_ocr_digits(len_img,True)
        match=known.get(pid) if pid else None
        expected_length=match.get('expected') if match else None
        length=_choose_length(length_candidates,expected_length)
        status='Matched' if match else 'NEW PIPE'
        length_diff = None
        if length is None:
            status='CHECK LENGTH' if match else 'NEW PIPE; CHECK LENGTH'
        elif expected_length is not None:
            length_diff = abs(float(length) - float(expected_length))
            if length_diff > 3.0:
                status=f'LENGTH DIFF {length_diff:.1f}'
        rec={'kind':'Pipe','asset':pid or new_pid,'up':match.get('up','') if match else '',
             'down':match.get('down','') if match else '',
             'video_length':length,'master_length':expected_length,'length_diff':length_diff,
             'row_date':d,'status':status}
        if not match: rec['skip_update']=True
        rows.append(rec)
        if on_row: on_row(rec)
    return rows


def parse_manhole_list(page, master_index, quick_text, on_row=None, on_progress=None):
    """Read Node Survey List rows using Node Number -> master ST_ID directly."""
    base=render_page(page,2.5)
    img=np.array(Image.fromarray(base).rotate(270,expand=True))
    h,w=img.shape[:2]
    known=master_index['manholes']
    rows=[]; blanks=0; seen=set()
    start=.1680*h; step=.0260*h
    for i in range(40):
        if on_progress: on_progress()
        yc=int(start+i*step)
        if yc >= .58*h: break
        half=max(16,int(step*.50)); y1,y2=max(0,yc-half),min(h,yc+half)
        date_img=img[y1:y2,int(.090*w):int(.180*w)]
        id_img=img[y1:y2,int(.155*w):int(.300*w)]
        full_sid_candidates=_ocr_asset_candidates(id_img,fast_plain=False)
        sid_candidates=_ocr_digits(id_img,False)+full_sid_candidates
        new_options=_new_suffix_asset_candidates(full_sid_candidates,known.keys())
        new_sid=new_options[0] if new_options else ''
        sid='' if new_sid else _best_known_id(sid_candidates,known.keys(),max_dist=1)
        if not sid and not new_sid:
            blanks+=1
            if i>2 and blanks>=4: break
            continue
        observed_sid=sid or new_sid
        if observed_sid in seen: continue
        seen.add(observed_sid)
        blanks=0
        rec={'kind':'Manhole','asset':observed_sid,'video_length':None,
             'row_date':_parse_sheet_date(date_img),'status':'Matched' if sid else 'NEW MANHOLE'}
        if not sid: rec['skip_update']=True
        rows.append(rec)
        if on_row: on_row(rec)
    return rows


def _year15_oriented(page, kind):
    base=render_page(page,2.5)
    best=None
    for deg in (0,270,90):
        img=base if deg==0 else np.array(Image.fromarray(base).rotate(deg,expand=True))
        txt=ocr_text(img[:max(1,int(img.shape[0]*.30)),:],11).lower()
        if kind=='cleaning':
            norm=re.sub(r'[^a-z0-9]+',' ',txt)
            score=(8*(('wheel walk' in norm) or ('wheel' in norm and 'walk' in norm))+
                   5*(('cleaning date' in norm) or ('cleaning' in norm and 'date' in norm))+
                   2*('up mh' in norm))
        elif kind=='pipes': score=8*('length surveyed' in txt or 'surveyed length' in txt)+3*('upstream' in txt)+3*('downstream' in txt)
        else: score=8*('manhole number' in txt)+4*('drainage area' in txt)
        if best is None or score>best[0]: best=(score,img)
    return best[1]


def _year15_all_row_bands(img,min_y_ratio=.04,max_y_ratio=.90):
    """Keep all Year 15 table rows, including bands around a double-height comment."""
    h,w=img.shape[:2]; gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    inv=cv2.threshold(gray,205,255,cv2.THRESH_BINARY_INV)[1]
    kernel=cv2.getStructuringElement(cv2.MORPH_RECT,(max(60,int(w*.09)),1))
    hor=cv2.morphologyEx(inv,cv2.MORPH_OPEN,kernel)
    contours,_=cv2.findContours(hor,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    lines=[]
    for c in contours:
        x,y,ww,hh=cv2.boundingRect(c)
        if ww>=w*.58 and hh<=max(14,h*.018) and min_y_ratio*h<=y<=max_y_ratio*h:
            lines.append((y+hh//2,x,x+ww))
    lines.sort(); merged=[]
    for line in lines:
        if merged and abs(line[0]-merged[-1][0])<=max(3,int(h*.004)):
            if line[2]-line[1]>merged[-1][2]-merged[-1][1]: merged[-1]=line
        else: merged.append(line)
    if len(merged)<3: return [],None
    # Select the largest vertically connected table group, tolerating one row
    # that is approximately twice normal height.
    groups=[]; cur=[merged[0]]
    for line in merged[1:]:
        if 4<=line[0]-cur[-1][0]<=max(120,int(h*.075)): cur.append(line)
        else:
            if len(cur)>=3: groups.append(cur)
            cur=[line]
    if len(cur)>=3: groups.append(cur)
    group=max(groups,key=len) if groups else merged
    left=int(np.median([x1 for _,x1,x2 in group])); right=int(np.median([x2 for _,x1,x2 in group]))
    bands=[]
    for (a,_,_),(b,_,_) in zip(group,group[1:]):
        if 8<=b-a<=max(120,int(h*.075)):
            pad=max(2,int((b-a)*.10)); bands.append((a+pad,b-pad))
    return bands,(left,right)


def _year15_compact_grid_bands(img):
    """Fallback for valid pair tables that occupy only a small part of the page.

    The normal Year 15 detector intentionally requires very long full-page grid
    rules. Some B&C scans place a perfectly valid table in only the upper quarter
    or third of the sheet, so those rules are short relative to the page even
    though they span essentially the entire table. This fallback first isolates
    the largest connected table-like region, then measures vertical continuity
    relative to that region. It is used only after the strict detector fails.
    """
    h,w=img.shape[:2]
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)

    # A slightly lighter threshold is appropriate only for locating the connected
    # table region. Actual column rules are re-validated below at a stricter level.
    inv=cv2.threshold(gray,235,255,cv2.THRESH_BINARY_INV)[1]
    connected=cv2.morphologyEx(
        inv,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)))
    contours,_=cv2.findContours(connected,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    candidates=[]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if ww>=w*.35 and hh>=h*.12 and ww*hh<=w*h*.85:
            candidates.append((ww*hh,x,y,ww,hh))
    if not candidates:
        return [],None,None

    _,bx,by,bw,bh=max(candidates)
    crop=img[by:by+bh,bx:bx+bw]
    if crop.size==0:
        return [],None,None

    cgray=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
    cinv=cv2.threshold(cgray,225,255,cv2.THRESH_BINARY_INV)[1]
    joined=cv2.morphologyEx(
        cinv,cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(3,int(bh*.012)))))
    vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(20,int(bh*.12))))
    vertical=cv2.morphologyEx(joined,cv2.MORPH_OPEN,vk)
    contours,_=cv2.findContours(vertical,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    # Short fragments at one x-coordinate are merged before judging continuity.
    # This repairs grid rules interrupted by printed text crossing the line.
    rules=[]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if hh>=bh*.18 and ww<=max(24,bw*.025):
            rules.append((x+ww//2,y,y+hh))
    rules.sort(); merged=[]
    for rule in rules:
        if merged and abs(rule[0]-merged[-1][0])<=max(5,int(bw*.006)):
            old=merged[-1]
            merged[-1]=((old[0]+rule[0])//2,min(old[1],rule[1]),max(old[2],rule[2]))
        else:
            merged.append(rule)
    if len(merged)<5:
        return [],None,None

    max_span=max(y2-y1 for _,y1,y2 in merged)
    strong=[rule for rule in merged if rule[2]-rule[1]>=max_span*.85]
    if len(strong)<5:
        return [],None,None

    xs=[]
    for x,_,_ in strong:
        full_x=bx+x
        if not xs or full_x-xs[-1]>max(4,int(bw*.004)):
            xs.append(full_x)
        else:
            xs[-1]=(xs[-1]+full_x)//2
    if len(xs)<5:
        return [],None,None
    left,right=xs[0],xs[-1]
    if right-left<w*.35:
        return [],None,None

    # Build row bands from horizontal rules inside the isolated table. A compact
    # table may have a title band before the actual column header, so keep the
    # first meaningful tall band and let header-role OCR choose among the first
    # four bands as it already does on normal layouts.
    roi=inv[by:by+bh,max(0,left):min(w,right)]
    hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(35,int((right-left)*.20)),1))
    horizontal=cv2.morphologyEx(roi,cv2.MORPH_OPEN,hk)
    contours,_=cv2.findContours(horizontal,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    ys=[by,by+bh-1]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if ww>=(right-left)*.45 and hh<=max(14,h*.018):
            ys.append(by+y+hh//2)
    ys.sort(); ymerged=[]
    for y in ys:
        if not ymerged or y-ymerged[-1]>max(3,int(h*.004)):
            ymerged.append(y)
        else:
            ymerged[-1]=(ymerged[-1]+y)//2

    bands=[]; first_meaningful=True
    for a,b in zip(ymerged,ymerged[1:]):
        gap=b-a
        if gap<10:
            continue
        gap_limit=max(140,int(bh*.30)) if first_meaningful else max(90,int(bh*.18))
        if gap<=gap_limit:
            pad=max(2,int(gap*.10))
            bands.append((a+pad,b-pad))
            first_meaningful=False
    if not bands:
        return [],None,None
    return bands,(left,right),xs


def _year15_grid_bands(img):
    """Find the complete table from its long vertical rules, then its row rules.

    This is deliberately independent of header OCR. It handles scans whose upper
    horizontal rules are faint or broken, which previously made the apparent table
    begin several data rows below the real header.
    """
    h,w=img.shape[:2]; gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    inv=cv2.threshold(gray,225,255,cv2.THRESH_BINARY_INV)[1]
    # Join small scan gaps before requiring a long vertical segment.
    joined=cv2.morphologyEx(inv,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(5,int(h*.012)))))
    vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(45,int(h*.16))))
    vertical=cv2.morphologyEx(joined,cv2.MORPH_OPEN,vk)
    contours,_=cv2.findContours(vertical,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    rules=[]
    for c in contours:
        x,y,ww,hh=cv2.boundingRect(c)
        if hh>=h*.45 and ww<=max(24,w*.025): rules.append((x+ww//2,y,y+hh))
    rules.sort(); merged=[]
    for rule in rules:
        if merged and abs(rule[0]-merged[-1][0])<=max(5,int(w*.006)):
            old=merged[-1]; merged[-1]=((old[0]+rule[0])//2,min(old[1],rule[1]),max(old[2],rule[2]))
        else: merged.append(rule)
    if len(merged)<5: return [],None,None
    top=max(0,int(statistics.median([y1 for x,y1,y2 in merged])))
    bottom=min(h,int(statistics.median([y2 for x,y1,y2 in merged])))
    if bottom-top<h*.25: return [],None,None
    # Re-select rules by dark-pixel coverage across the common table height.
    # Repeated text can form false vertical morphology contours, but unlike a
    # printed grid rule it is not dark through most rows.
    coverage=np.mean(gray[top:bottom,:] < 205,axis=0)
    candidates=[int(x) for x in np.where(coverage>=.65)[0]]
    xgroups=[]
    for x in candidates:
        if not xgroups or x-xgroups[-1][-1]>max(4,int(w*.004)): xgroups.append([x])
        else: xgroups[-1].append(x)
    xs=[]
    for group in xgroups:
        xs.append(max(group,key=lambda x:coverage[x]))
    # Keep the densest plausible table cluster if unrelated page rules exist.
    clusters=[]; cur=[]
    for x in xs:
        if cur and x-cur[-1]>w*.16:
            if len(cur)>=5: clusters.append(cur)
            cur=[]
        cur.append(x)
    if len(cur)>=5: clusters.append(cur)
    if clusters: xs=max(clusters,key=lambda g:(len(g),g[-1]-g[0]))
    if len(xs)<5: return [],None,None
    left,right=xs[0],xs[-1]; tw=right-left
    if tw<w*.35: return [],None,None
    # Detect even partial horizontal rules, but only inside the confirmed table.
    roi=inv[top:bottom,max(0,left):min(w,right)]
    hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(35,int(tw*.20)),1))
    horizontal=cv2.morphologyEx(roi,cv2.MORPH_OPEN,hk)
    contours,_=cv2.findContours(horizontal,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    ys=[]
    for c in contours:
        x,y,ww,hh=cv2.boundingRect(c)
        if ww>=tw*.23 and hh<=max(14,h*.018): ys.append(top+y+hh//2)
    ys.sort(); ymerged=[]
    for y in ys:
        if not ymerged or y-ymerged[-1]>max(3,int(h*.004)): ymerged.append(y)
        else: ymerged[-1]=(ymerged[-1]+y)//2
    # Ensure the vertical-grid endpoints participate as the outer row rules.
    for y in (top,bottom):
        if all(abs(y-z)>max(5,int(h*.008)) for z in ymerged): ymerged.append(y)
    ymerged.sort(); bands=[]
    normal_gap_limit=max(140,int(h*.085))
    # The first band is the printed header.  Some B&C cleaning sheets wrap the
    # labels across three or four lines, making only that band substantially
    # taller than a data row.  Keep one tall leading header without relaxing
    # the limit for comments or unrelated gaps elsewhere in the table.
    header_gap_limit=max(normal_gap_limit,int(h*.16))
    for band_index,(a,b) in enumerate(zip(ymerged,ymerged[1:])):
        gap=b-a
        gap_limit=header_gap_limit if band_index==0 else normal_gap_limit
        if 8<=gap<=gap_limit:
            pad=max(2,int(gap*.10)); bands.append((a+pad,b-pad))
    return bands,(left,right),xs


def _header_role(compact,kind):
    compact=str(compact or '').lower().replace(' ','')
    if (('up' in compact or compact.startswith('u')) and any(x in compact for x in ('mh','ma','mn'))) or compact.startswith(('upm','uma')): return 'up'
    if (('dn' in compact or compact.startswith('d')) and any(x in compact for x in ('mh','nh','mn'))) or compact.startswith(('dnm','dnh')): return 'down'
    if kind=='cleaning' and any(x in compact for x in ('wheel','wwalk','wheelwal')): return 'value'
    if kind=='pipes' and ('survey' in compact or ('length' in compact and 'scheduled' not in compact)): return 'value'
    if 'date' in compact: return 'date'
    return None


def _table_header_columns(img, header_bands, table, kind, column_bounds=None, return_details=False):
    """Locate activity columns from the printed header instead of fixed order."""
    left,right=table; h,w=img.shape[:2]
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    inv=cv2.threshold(gray,205,255,cv2.THRESH_BINARY_INV)[1]
    best={}; best_cells=[]
    # The first detected band is normally the header, but scans sometimes include
    # a title/spacer band. Try the first four bands rather than trusting one index.
    for band_index,(y1,y2) in enumerate(list(header_bands)[:4]):
        if band_index==0:
            bh=max(1,y2-y1)
            y1=max(0,int(y1-bh*.85)); y2=min(h,int(y2+bh*.15))
        roi=inv[max(0,y1):min(h,y2),max(0,left):min(w,right)]
        if roi.size==0: continue
        xs=list(column_bounds or [])
        if not xs:
            kernel=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(10,int(roi.shape[0]*.50))))
            ver=cv2.morphologyEx(roi,cv2.MORPH_OPEN,kernel)
            contours,_=cv2.findContours(ver,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            xs=[left,right]
            for c in contours:
                x,y,ww,hh=cv2.boundingRect(c)
                if hh>=roi.shape[0]*.42: xs.append(left+x+ww//2)
        xs=sorted(max(left,min(right,x)) for x in xs); merged=[]
        for x in xs:
            if not merged or x-merged[-1]>max(4,int((right-left)*.004)): merged.append(x)
            else: merged[-1]=(merged[-1]+x)//2
        if len(merged)<5: continue
        found={}; cells=[]; tw=max(1,right-left)
        for _raw_ci,(a,b) in enumerate(zip(merged,merged[1:])):
            if b-a<10: continue
            # Number only real cells.  A fallback table can seed its approximate
            # left edge a few pixels before the first detected vertical rule,
            # producing a tiny skipped interval.  Reusing the raw interval index
            # then left Column 1 blank and pushed the final Cleaning Date cell
            # beyond the headers list even though all ten real cells were found.
            ci=len(cells)
            cell=img[max(0,y1):min(h,y2),max(0,a+2):min(w,b-2)]
            if cell.size==0: continue
            scale=max(2,round(130/max(1,cell.shape[0])))
            enlarged=cv2.resize(cell,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
            # Fast first pass. Escalate only a header cell whose role is uncertain.
            texts=[ocr_text(enlarged,6)]
            compact=re.sub(r'[^a-z0-9]+','',texts[0].lower())
            role=_header_role(compact,kind)
            if not role:
                texts.append(ocr_text(enlarged,11))
                compact=re.sub(r'[^a-z0-9]+','',' '.join(texts).lower())
                role=_header_role(compact,kind)
            display=re.sub(r'\s+',' ',' '.join(x for x in texts if x).replace('\n',' ')).strip() or f'Column {ci+1}'
            box=((a-left)/tw,(b-left)/tw); cells.append((ci,box,compact,display))
            if role and role not in found: found[role]=box
        # Cleaning Date is normally the cell immediately after Wheel Walk. This
        # positional inference is safe only after Wheel Walk itself was identified.
        if kind=='cleaning' and 'value' in found and 'date' not in found:
            for ci,box,text,display in cells:
                if box==found['value']:
                    nxt=next((b for j,b,t,d in cells if j==ci+1),None)
                    if nxt: found['date']=nxt
                    break
        # Some B&C cleaning scans split the narrow final headers so OCR sees
        # "Length Length" and "Date" instead of "Wheel Walk Length" and
        # "Cleaning Date".  When Date is confidently recognized in the final
        # column, accept the immediately preceding Length-labelled column as the
        # Wheel Walk value.  Requiring adjacency + final-column Date keeps this
        # inference specific to the printed cleaning layout rather than treating
        # every generic Length header as Wheel Walk.
        if kind=='cleaning' and 'date' in found and 'value' not in found and cells:
            date_ci=next((ci for ci,box,text,display in cells if box==found['date']),None)
            if date_ci==len(cells)-1 and date_ci>0:
                prev=next(((box,text,display) for ci,box,text,display in cells if ci==date_ci-1),None)
                if prev and 'length' in (prev[1] or ''):
                    found['value']=prev[0]
        if len(found)>len(best): best,best_cells=dict(found),list(cells)
        if all(x in found for x in ('up','down','value','date')):
            if return_details: return found,cells,'header'
            return found
    # Preserve useful partial header evidence for the confirmable layout path.
    # Previously one missing role discarded all other recognized roles, which is
    # why an OCR-visible Date column could still default blank in the dialog.
    if return_details:
        return (best or None),best_cells,'header' if all(x in best for x in ('up','down','value','date')) else 'incomplete header'
    return best if all(x in best for x in ('up','down','value','date')) else None


def _column_index_for_box(box,column_boxes):
    if not box: return None
    center=sum(box)/2
    return min(range(len(column_boxes)),key=lambda i:abs(sum(column_boxes[i])/2-center)) if column_boxes else None


def _master_assisted_endpoint_columns(img,bands,table,column_boxes,master_index):
    """Choose endpoint columns by how many sampled pairs resolve in the master."""
    if len(column_boxes)<2 or len(bands)<2: return None,0,0
    left,right=table; tw=max(1,right-left)
    sample_bands=list(bands[1:8])
    observed=[[None for _ in sample_bands] for _ in column_boxes]
    for ci,box in enumerate(column_boxes):
        for ri,(y1,y2) in enumerate(sample_bands):
            cell=img[y1:y2,max(0,int(left+box[0]*tw)):min(img.shape[1],int(left+box[1]*tw))]
            observed[ci][ri]=_ocr_asset_candidates(cell,fast_plain=True)
    scored=[]
    for up_i in range(len(column_boxes)):
        for dn_i in range(len(column_boxes)):
            if up_i==dn_i: continue
            matched=0; exact_signal=0
            for ri in range(len(sample_bands)):
                item,status=_resolve_pipe_pair(observed[up_i][ri],observed[dn_i][ri],master_index)
                if item:
                    matched+=1
                    if any(re.search(r'[A-Z]',x) and re.search(r'\d',x) for x in observed[up_i][ri]+observed[dn_i][ri]): exact_signal+=1
            scored.append((matched,exact_signal,-abs(up_i-dn_i),up_i,dn_i))
    scored.sort(reverse=True)
    if not scored: return None,0,0
    best=scored[0]; second=scored[1][0] if len(scored)>1 else 0
    minimum=max(2,int(len(sample_bands)*.30))
    if best[0]<minimum: return None,best[0],second
    return (best[3],best[4]),best[0],second


def prepare_year15_pair_layout(page,master_index,kind):
    """Render once, detect the grid, read headers, and prepare a confirmable layout."""
    img=_year15_oriented(page,kind)
    bands,table,column_bounds=_year15_grid_bands(img)
    geometry_source='vertical grid'
    if not bands:
        bands,table,column_bounds=_year15_compact_grid_bands(img)
        if bands: geometry_source='compact table grid'
    if not bands:
        bands,table=_year15_all_row_bands(img,.04,.90); column_bounds=None; geometry_source='horizontal fallback'
    if not bands or not table:
        return {'kind':kind,'img':img,'bands':[],'table':None,'mapping':{},'headers':[],
                'column_boxes':[],'role_indices':{},'confidence':0,'source':'table not found','warnings':['TABLE STRUCTURE NOT RESOLVED']}
    left,right=table; tw=max(1,right-left)
    if column_bounds and len(column_bounds)>=2:
        column_boxes=[((a-left)/tw,(b-left)/tw) for a,b in zip(column_bounds,column_bounds[1:])]
    else:
        # Header-cell detection will provide boxes when long vertical rules are unavailable.
        column_boxes=[]
    mapping,cells,source=_table_header_columns(img,bands,table,kind,column_bounds,return_details=True)
    if cells and not column_boxes: column_boxes=[c[1] for c in sorted(cells,key=lambda x:x[0])]
    headers=[f'Column {i+1}' for i in range(len(column_boxes))]
    for ci,box,compact,display in cells:
        if 0<=ci<len(headers): headers[ci]=f'Column {ci+1} — {display}'
    mapping=dict(mapping or {}); role_indices={}
    for role,box in mapping.items():
        idx=_column_index_for_box(box,column_boxes)
        if idx is not None: role_indices[role]=idx
    warnings=[]; assisted_score=0; assisted_second=0
    if ('up' not in role_indices or 'down' not in role_indices) and column_boxes:
        pair,assisted_score,assisted_second=_master_assisted_endpoint_columns(img,bands,table,column_boxes,master_index)
        if pair:
            role_indices['up'],role_indices['down']=pair
            mapping['up'],mapping['down']=column_boxes[pair[0]],column_boxes[pair[1]]
            source='master-assisted'
        else: warnings.append('ENDPOINT COLUMNS NEED CONFIRMATION')
    missing=[r for r in ('up','down','value','date') if r not in role_indices]
    if missing: warnings.append('MISSING COLUMN ROLES: '+', '.join(x.upper() for x in missing))
    confidence=100 if not missing and source=='header' and geometry_source=='vertical grid' else (85 if not missing else max(30,75-15*len(missing)))
    fingerprint=hashlib.sha1((kind+'|'+ '|'.join(re.sub(r'[^a-z0-9]+','',x.lower()) for x in headers)).encode()).hexdigest()
    return {'kind':kind,'img':img,'bands':bands,'table':table,'mapping':mapping,'headers':headers,
            'column_boxes':column_boxes,'role_indices':role_indices,'confidence':confidence,
            'source':source+' / '+geometry_source,'warnings':warnings,'fingerprint':fingerprint,
            'master_pair_score':assisted_score,'master_pair_second':assisted_second}


def apply_confirmed_layout(layout,role_indices):
    layout['detected_confidence']=layout.get('confidence',0)
    layout['detection_warnings']=list(layout.get('warnings',[]))
    role_indices={k:int(v) for k,v in role_indices.items()}
    layout['role_indices']=role_indices
    layout['mapping']={role:layout['column_boxes'][idx] for role,idx in role_indices.items()}
    layout['confidence']=100; layout['source']=layout.get('source','')+' / user confirmed'; layout['warnings']=[]
    return layout


def _printed_asset_total(text,kind):
    """Read only a count printed directly beside the correct report label.

    Consor's rotated pipe report often places the number before the label in OCR
    reading order, while other scans place it after. A strict integer boundary
    prevents the 7 in a length such as 7,106.2 from becoming a row count.
    """
    source=re.sub(r'\s+',' ',str(text or '')).strip()
    integer=r'(?<![\d,.])(\d{1,3})(?![\d,.])'
    if kind=='cleaning':
        # Cleaning reports do not provide a row total for this validation.
        return None
    if kind=='pipes':
        label=r'(?:[ns]umber\s+of\s+surveys?\s+in\s*this|in\s*this)'
        patterns=[label+r'[\s:_\-]*'+integer,
                  integer+r'[\s:_\-]*'+label,
                  r'total\s+(?:pipe|survey)s?[\s:_\-]*'+integer]
    elif kind=='manholes':
        label=r'report\s+survey\s+count'
        patterns=[label+r'[\s:_\-]*'+integer,
                  integer+r'[\s:_\-]*'+label,
                  r'total\s+(?:manhole|asset|row)s?[\s:_\-]*'+integer]
    else:
        patterns=[r'total\s+(?:asset|row|pipe|manhole|survey)s?[\s:_\-]*'+integer]
    for pattern in patterns:
        m=re.search(pattern,source,re.I)
        if m:
            try: return int(m.group(1))
            except Exception: pass
    return None


def validate_page_rows(data,kind,text,page_number,layout=None,profile=None):
    """Validate counts, duplicates, match rate, and table structure per PDF page."""
    real=[r for r in data if r.get('asset')!='COLUMN HEADERS NOT RESOLVED']
    issues=[]; seen=set(); duplicates=0
    for r in real:
        if r.get('kind') in ('Pipe','Cleaning'):
            key=(asset_key(r.get('up','')),asset_key(r.get('down','')))
        else: key=r.get('asset_key') or asset_key(r.get('asset',''))
        # Repeated pipe rows can be legitimate split surveys. They remain in the
        # page row count and are combined by work order before the master update.
        if kind!='pipes' and key and key in seen:
            duplicates+=1; r.setdefault('validation_warnings',[]).append('DUPLICATE IN PDF'); r['skip_update']=True
        if key: seen.add(key)
    matched=sum(1 for r in real if not r.get('skip_update'))
    unmatched=len(real)-matched
    # Printed totals are a Consor/Reno report feature. Brown and Caldwell
    # masters (Year 15 and Phase 2) do not provide an applicable row count.
    expected=_printed_asset_total(text,kind) if profile=='reno' else None
    if expected is not None and expected!=len(real): issues.append(f'printed total {expected}, detected {len(real)}')
    if duplicates: issues.append(f'{duplicates} duplicate row(s)')
    if real and matched/len(real)<.80: issues.append(f'low master match rate {matched}/{len(real)}')
    if not real: issues.append('zero readable asset rows')
    if layout:
        cols=len(layout.get('column_boxes',[]))
        if cols<4: issues.append(f'unexpected table structure: only {cols} column(s)')
        grid_rows=max(0,len(layout.get('bands',[]))-1)
        if grid_rows and len(real)<max(1,grid_rows-2): issues.append(f'grid suggests about {grid_rows} data band(s), detected {len(real)}')
        if layout.get('detection_warnings'): issues.append('layout required confirmation: '+'; '.join(layout['detection_warnings']))
    return {'page':page_number,'kind':kind,'rows':len(real),'matched':matched,'unmatched':unmatched,
            'duplicates':duplicates,'expected':expected,'issues':issues}


def parse_year15_pair_list(page, master_index, kind, prepared=None, on_row=None, on_progress=None, expected_date=None):
    """Read Year 15 video/cleaning rows by the printed UP_MH + DN_MH pair."""
    prepared=prepared or prepare_year15_pair_layout(page,master_index,kind)
    img=prepared['img']; h,w=img.shape[:2]; bands=prepared.get('bands',[]); table=prepared.get('table')
    if not bands or not table: return []
    left,right=table; tw=max(1,right-left)
    detected=prepared.get('mapping')
    if detected:
        up_box=detected['up']; dn_box=detected['down']; val_box=detected['value']; date_box=detected['date']
    else:
        # Never reinterpret unrelated columns as assets. A visible review row is
        # safer than the old fixed-coordinate fallback, which could produce false
        # pairs such as DIA -> PROJECTYEAR.
        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe',
             'asset':'COLUMN HEADERS NOT RESOLVED','up':'?','down':'?',
             'video_length':None,'row_date':None,
             'status':'COLUMN HEADERS NOT RESOLVED','skip_update':True}
        if on_row: on_row(rec)
        return [rec]
    expected_date=expected_date if isinstance(expected_date,datetime) else None
    date_reads={}
    for date_band_index,(date_y1,date_y2) in enumerate(bands):
        date_cell=img[date_y1:date_y2,
                      max(0,int(left+date_box[0]*tw)):min(w,int(left+date_box[1]*tw))]
        date_reads[date_band_index]=_read_sheet_date_evidence(date_cell,expected_date)
    dominant_date=_dominant_sheet_date(list(date_reads.values()),expected_date)
    printed_total_info=_read_pair_table_printed_total(
        img,bands,table,val_box,up_box,dn_box,date_box)
    total_band_index=printed_total_info.get('band_index')

    endpoint_items={}
    for pipe_item in master_index.get('pipe_items',[]):
        endpoint_items[pipe_item['up_key']]=pipe_item['up']
        endpoint_items[pipe_item['down_key']]=pipe_item['down']
    for endpoint_key,manhole_item in master_index.get('manholes',{}).items():
        endpoint_items[asset_key(endpoint_key)]=manhole_item.get('asset') or str(endpoint_key)
    rows=[]; seen=set()
    typical_band=float(np.median([max(1,b-a) for a,b in bands]))
    def has_asset_digit_signal(observations):
        for raw in observations or []:
            key=asset_key(raw)
            if len(re.findall(r'\d',key))>=2:
                return True
        return False
    for band_index,(y1,y2) in enumerate(bands):
        if total_band_index is not None and band_index==total_band_index:
            # The printed total is validation evidence, never an asset row.
            continue
        if on_progress: on_progress()
        def cut(box): return img[y1:y2,max(0,int(left+box[0]*tw)):min(w,int(left+box[1]*tw))]
        def read_id(box,fast=True):
            cell=cut(box); obs=_ocr_asset_candidates(cell,fast_plain=fast)
            if y2-y1>typical_band*1.45:
                ch=cell.shape[0]
                obs+=_ocr_asset_candidates(cell[:max(1,int(ch*.62)),:],fast_plain=fast)
                obs+=_ocr_asset_candidates(cell[int(ch*.38):,:],fast_plain=fast)
            return list(dict.fromkeys(obs))
        up_obs=read_id(up_box,True); dn_obs=read_id(dn_box,True)
        match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)
        if not match:
            # Some clean R2 prefixes are consistently read as 2/22/32/52. Re-run
            # only unresolved endpoint cells with a focused whitelist and accept
            # only complete IDs that already exist in the selected master.
            up_obs=list(dict.fromkeys(up_obs+_ocr_known_r2_candidates(cut(up_box),endpoint_items)))
            dn_obs=list(dict.fromkeys(dn_obs+_ocr_known_r2_candidates(cut(dn_box),endpoint_items)))
            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)
        if not match:
            # Escalate only uncertain endpoint cells to the slower OCR ensemble.
            up_obs=list(dict.fromkeys(up_obs+read_id(up_box,False)))
            dn_obs=list(dict.fromkeys(dn_obs+read_id(dn_box,False)))
            match,match_status=_resolve_pipe_pair(up_obs,dn_obs,master_index)
        value_cell=cut(val_box)
        value_candidates=_ocr_digits(value_cell,True,fast_plain=True)
        if not value_candidates: value_candidates=_ocr_digits(value_cell,True,fast_plain=False)
        expected=match.get('expected') if match else None
        if kind=='cleaning':
            value=_choose_cleaning_length(value_candidates,expected)
            distinct={round(float(x),2) for x in value_candidates if 0<float(x)<5000}
            needs_consensus=(not value_candidates or value is None or len(distinct)>1 or
                (value is not None and expected not in (None,0) and
                 abs(float(value)-float(expected))>LENGTH_DIFF_THRESHOLD))
            if needs_consensus:
                # Re-read inside several small horizontal margins.  This removes
                # the vertical grid rules that caused 2 -> 7 and 224 -> 22 while
                # retaining the full digit string.  New crop pixels also avoid
                # reusing a stale OCR-cache result from the border-touching crop.
                consensus=list(value_candidates)
                width=value_cell.shape[1]
                for ratio in (.015,.030,.045,.060):
                    pad=max(2,int(round(width*ratio)))
                    if width>pad*2+4:
                        consensus.extend(_ocr_digits(value_cell[:,pad:width-pad],True,fast_plain=True))
                # If a digit touches or is distorted by a table rule, horizontal
                # trimming alone can repeatedly agree on the same wrong value
                # (for example 275 -> 75 or 224 -> 274).  Remove grid rules and
                # add those OCR observations to the same printed-value vote.
                consensus.extend(_ocr_gridless_number_candidates(value_cell,True))
                value=_choose_cleaning_length(consensus,expected)
        else:
            value=_choose_length(value_candidates,expected)
        if value is not None and expected not in (None,0) and abs(float(value)-float(expected))>max(100,float(expected)*1.5):
            # An implausible fast result gets the full OCR ensemble before review.
            expanded=_ocr_digits(cut(val_box),True,fast_plain=False)
            if expanded:
                value=_choose_length(list(value_candidates)+list(expanded),expected)
        date_evidence=date_reads.get(band_index,{'date':None,'strong':False,'candidates':[],'votes':{},'strong_votes':{}})
        d=date_evidence.get('date')
        endpoint_signal=has_asset_digit_signal(up_obs) and has_asset_digit_signal(dn_obs)
        # Structural filtering happens BEFORE date repair. Header labels such as
        # UPMI/WOM and footer OCR noise must never become rows merely because a
        # dominant table date can be inferred.
        edge_band=band_index in (0,len(bands)-1)
        tall_band=(y2-y1)>typical_band*1.45
        if not match and (edge_band or tall_band) and not endpoint_signal:
            continue
        if not match and not endpoint_signal:
            continue
        if dominant_date is not None and (match or endpoint_signal):
            if d is None or not _date_outlier_is_well_supported(date_evidence,dominant_date,expected_date):
                d=dominant_date
        if d is None:
            continue
        if match:
            status='Matched' if value is not None else ('CHECK WHEEL WALK' if kind=='cleaning' else 'CHECK LENGTH')
            up,down=match['up'],match['down']; asset=match.get('pipe_id','')
        else:
            status=match_status
            up=_best_observed_asset_id(up_obs,endpoint_items) or (canonical_asset_id(up_obs[0]) if up_obs else '?')
            down=_best_observed_asset_id(dn_obs,endpoint_items) or (canonical_asset_id(dn_obs[0]) if dn_obs else '?')
            asset='' if status=='NEW PIPE' else f'UNMATCHED ROW {len(rows)+1}'
        rec={'kind':'Cleaning' if kind=='cleaning' else 'Pipe','asset':asset,
             'up':up,'down':down,'video_length':value,'row_date':d,'status':status}
        if not match: rec['skip_update']=True
        if kind in ('pipes','cleaning'):
            rec['master_length']=match.get('expected') if match else None; rec['length_diff']=None
            if match and value is not None and match.get('expected') is not None:
                rec['length_diff']=abs(float(value)-float(match['expected']))
                if rec['length_diff']>LENGTH_DIFF_THRESHOLD:
                    suffix=' (WHEEL WALK)' if kind=='cleaning' else ''
                    rec['status']=f"LENGTH DIFF {rec['length_diff']:.1f}{suffix}"
        key=(asset_key(rec['up']),asset_key(rec['down'])) if not rec.get('skip_update') else ('unmatched',len(rows))
        # Cleaning still represents one measurement per pipe. Pipe video rows may
        # repeat when the same pipe was surveyed in multiple parts.
        if key in seen and kind!='pipes': continue
        seen.add(key); rows.append(rec)
        if on_row: on_row(rec)
    prepared['printed_total_info']=printed_total_info
    return rows


def parse_year15_manholes(page, master_index, on_row=None, on_progress=None):
    img=_year15_oriented(page,'manholes'); h,w=img.shape[:2]
    known=master_index['manholes']
    # This portrait report OCRs reliably as positioned words even when scan skew
    # prevents horizontal-line detection. Read every ID-like token in the left
    # portion first and resolve it against the master IDs.
    token_rows=[]; token_dates=[]
    for psm in (6,11):
        if on_progress: on_progress()
        gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
        data=pytesseract.image_to_data(gray,config=f'--psm {psm}',output_type=pytesseract.Output.DICT)
        for i,txt in enumerate(data.get('text',[])):
            x=int(data['left'][i]); y=int(data['top'][i]); hh=int(data['height'][i])
            parsed_date=parse_date_text(str(txt))
            if x>w*.62 and parsed_date:
                token_dates.append((y+hh//2,parsed_date))
            if x>w*.36: continue
            raw=str(txt)
            if not re.search(r'\d{3,6}',raw): continue
            item,status=_resolve_full_asset([raw],known)
            token_rows.append((y+hh//2,item,status,raw))
    if token_rows:
        token_rows.sort(key=lambda x:x[0]); clustered=[]
        for row in token_rows:
            if clustered and abs(row[0]-clustered[-1][0])<h*.012:
                # Prefer a matched reading over an ambiguous reading of the same row.
                if clustered[-1][1] is None and row[1] is not None: clustered[-1]=row
            else: clustered.append(row)
        seen=set(); out=[]
        for yc,item,status,raw in clustered:
            if on_progress: on_progress()
            sid=item['asset'] if item else (_best_observed_asset_id([raw],known) or canonical_asset_id(raw))
            unique_key=item['asset_key'] if item else f'row-{yc}'
            if unique_key in seen: continue
            row_date=None
            near=[x for x in token_dates if abs(x[0]-yc)<h*.025]
            if near: row_date=min(near,key=lambda x:abs(x[0]-yc))[1]
            rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',
                 'video_length':None,'row_date':row_date,'status':status}
            if item is None: rec['skip_update']=True
            seen.add(unique_key); out.append(rec)
            if on_row: on_row(rec)
        return out
    bands,table=_table_row_bands(img,.04,.72)
    if not bands:return []
    left,right=table; tw=max(1,right-left); rows=[]; seen=set()
    for y1,y2 in bands:
        if on_progress: on_progress()
        id_img=img[y1:y2,left:min(w,int(left+.27*tw))]
        observations=_ocr_asset_candidates(id_img); item,status=_resolve_full_asset(observations,known)
        if not observations: continue
        sid=item['asset'] if item else (_best_observed_asset_id(observations,known) or canonical_asset_id(observations[0]))
        date_img=img[y1:y2,int(left+.74*tw):right]
        rec={'kind':'Manhole','asset':sid,'asset_key':item['asset_key'] if item else '',
             'video_length':None,'row_date':_parse_sheet_date(date_img),'status':status}
        if item is None: rec['skip_update']=True
        if rec['asset'] in seen: continue
        seen.add(rec['asset']); rows.append(rec)
        if on_row: on_row(rec)
    return rows



def master_workbook_lock_reason(path):
    """Return a user-friendly reason when the master workbook cannot be safely edited.

    On Windows, Excel normally holds a sharing lock while a workbook is open.  We test
    for Excel's owner file and then request exclusive read/write access with CreateFileW.
    No workbook changes are attempted when either check indicates the file is in use.
    """
    path = os.path.abspath(path)
    folder = os.path.dirname(path)
    owner = os.path.join(folder, '~$' + os.path.basename(path))
    if os.path.exists(owner):
        return 'Excel appears to have this workbook open.'
    if sys.platform != 'win32':
        return ''
    try:
        import ctypes
        from ctypes import wintypes
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        FILE_ATTRIBUTE_NORMAL = 0x80
        INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        CreateFileW = kernel32.CreateFileW
        CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE]
        CreateFileW.restype = wintypes.HANDLE
        handle = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 0, None,
                             OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)
        if handle == INVALID_HANDLE_VALUE:
            err = ctypes.get_last_error()
            if err in (32, 33):
                return 'The master spreadsheet is open or locked by another program.'
            if err == 5:
                return 'Windows is not allowing the master spreadsheet to be edited.'
            return f'The master spreadsheet cannot be opened for exclusive editing (Windows error {err}).'
        kernel32.CloseHandle(handle)
    except Exception:
        # If the low-level lock probe itself fails, Excel's own open/save handling remains
        # the final safety net.  Do not incorrectly block a valid update just because the
        # diagnostic probe was unavailable.
        return ''
    return ''


def append_note(cell, note_text):
    """Append a warning to NOTES while preserving existing content and avoiding duplicates."""
    existing = str(cell.Value or '').strip()
    if not existing:
        cell.Value = note_text
        return
    if note_text.lower() in existing.lower():
        return
    sep = ' | ' if not existing.endswith(('|', ';')) else ' '
    cell.Value = existing + sep + note_text

def master_text(value):
    """Normalize user/OCR text immediately before it is written to Excel."""
    return str(value or '').strip().upper()

def write_excel_date(cell, value):
    """Write an Excel date with no displayed time component."""
    if isinstance(value, datetime):
        # Excel stores dates as serial values; NumberFormat controls display.
        # Zero out time defensively and force a date-only display.
        value = datetime(value.year, value.month, value.day)
    cell.Value = value
    cell.NumberFormat = 'mm/dd/yyyy'


APPROVED_NEW_ROW_GREEN=13561798  # Excel RGB(198,239,206), a readable light green.


def copy_master_row_below(ws,base_row):
    """Insert a row below base_row and copy its formulas, values, and formatting."""
    insert_row=int(base_row)+1
    last_col=max(1,int(ws.UsedRange.Columns.Count))
    ws.Rows(insert_row).Insert()
    source=ws.Range(ws.Cells(base_row,1),ws.Cells(base_row,last_col))
    destination=ws.Range(ws.Cells(insert_row,1),ws.Cells(insert_row,last_col))
    source.Copy(destination)
    try: ws.Rows(insert_row).RowHeight=ws.Rows(base_row).RowHeight
    except Exception: pass
    return insert_row,last_col


def clear_master_columns(ws,row,columns):
    for column in dict.fromkeys(column for column in columns if column):
        ws.Cells(row,column).ClearContents()


def highlight_approved_master_row(ws,row,last_col):
    target=ws.Range(ws.Cells(row,1),ws.Cells(row,last_col))
    target.Interior.Pattern=1
    target.Interior.Color=APPROVED_NEW_ROW_GREEN

def refresh_length_status(record):
    """Recalculate pipe-video or cleaning length warnings after manual edits."""
    if record.get('kind') not in ('Pipe','Cleaning'):
        return
    if record.get('skip_update') and str(record.get('status','')).startswith('NEW PIPE'):
        record['length_diff']=None
        return
    video = record.get('video_length')
    expected = record.get('master_length')
    if video is None:
        record['length_diff'] = None
        record['status'] = 'CHECK WHEEL WALK' if record.get('kind')=='Cleaning' else 'CHECK LENGTH'
        return
    if expected is None:
        record['length_diff'] = None
        # Preserve a non-length error if one exists; otherwise no comparison is available.
        if record.get('status','') in ('Matched', 'CHECK LENGTH') or str(record.get('status','')).startswith('LENGTH DIFF'):
            record['status'] = 'Matched'
        return
    diff = abs(float(video) - float(expected))
    record['length_diff'] = diff
    suffix=' (WHEEL WALK)' if record.get('kind')=='Cleaning' else ''
    record['status'] = f'LENGTH DIFF {diff:.1f}{suffix}' if diff > LENGTH_DIFF_THRESHOLD else 'Matched'


def split_pipe_identity(record):
    """Return the stable asset identity used to combine split pipe surveys."""
    if record.get('kind')!='Pipe' or record.get('skip_update'):
        return None
    pipe_id=asset_key(record.get('asset',''))
    if pipe_id and not pipe_id.startswith('UNMATCHED'):
        return ('pipe_id',pipe_id)
    up=asset_key(record.get('up','')); down=asset_key(record.get('down',''))
    return ('pair',up,down) if up and down else None


def combine_split_pipe_records(existing, additional):
    """Merge another segment of the same pipe/work order into one master row."""
    parts=list(existing.get('part_lengths',[]))
    if not parts:
        parts=[existing.get('video_length')]
    parts.append(additional.get('video_length'))
    existing['part_lengths']=parts
    existing['part_count']=len(parts)
    known=[float(value) for value in parts if value is not None]
    existing['video_length']=sum(known) if known else None

    pages=list(existing.get('source_pages',[]))
    if not pages and existing.get('source_page') is not None:
        pages=[existing.get('source_page')]
    if additional.get('source_page') is not None and additional.get('source_page') not in pages:
        pages.append(additional.get('source_page'))
    existing['source_pages']=pages
    if pages: existing['source_page']=', '.join(str(page) for page in pages)
    if existing.get('date') is None and additional.get('date') is not None:
        existing['date']=additional.get('date')
    existing['warnings']=list(dict.fromkeys(existing.get('warnings',[])+additional.get('warnings',[])))

    base=existing.get('display_asset_base') or existing.get('display_asset','')
    existing['display_asset_base']=base
    existing['display_asset']=f'{base}  ({len(parts)} parts combined)'
    if any(value is None for value in parts):
        existing['length_diff']=None
        existing['status']='CHECK PART LENGTH'
    else:
        refresh_length_status(existing)
    return existing


def review_status(record):
    parts=[]
    if int(record.get('part_count') or 0)>1:
        parts.append(f"MSA DETECTED — {int(record['part_count'])} PARTS COMBINED")
    status=str(record.get('status') or '')
    if status.startswith(('NEW PIPE','NEW MANHOLE')) and 'new_asset_approved' in record:
        parts.append(f"{status} — {'APPROVED FOR MASTER' if record.get('new_asset_approved') else 'NOT APPROVED'}")
    elif status and status!='Matched':
        parts.append(status)
    parts.extend(record.get('warnings', []))
    return '; '.join(dict.fromkeys(parts)) if parts else 'Matched'


def record_needs_review(record):
    """MSA feedback is informational; only actual errors/warnings need review."""
    if str(record.get('status','')).startswith(('NEW PIPE','NEW MANHOLE')) and record.get('new_asset_approved'):
        return bool(record.get('warnings'))
    return bool((record.get('status') and record.get('status')!='Matched') or record.get('warnings'))


def new_asset_base_info(record,master_index):
    """Locate the existing master row that an approved suffixed asset extends."""
    status=str(record.get('status',''))
    if status.startswith('NEW MANHOLE'):
        key=asset_key(record.get('asset',''))
        base_key=_base_asset_key(key,master_index.get('manholes',{}))
        item=master_index.get('manholes',{}).get(base_key)
        if item and base_key!=key:
            return {'kind':'Manhole','row':item['row'],'base_asset':item.get('asset') or base_key}
        return None
    if not status.startswith('NEW PIPE'):
        return None
    if record.get('up') and record.get('down'):
        item=_new_pipe_base_item([record.get('up')],[record.get('down')],master_index)
        if item:
            return {'kind':'Pipe','row':item['row'],'base_asset':f"{item['up']} -> {item['down']}"}
        return None
    pipe_id=asset_key(record.get('asset',''))
    base_id=_base_asset_key(pipe_id,master_index.get('pipe_by_id',{}))
    item=master_index.get('pipe_by_id',{}).get(base_id)
    if item and base_id!=pipe_id:
        return {'kind':'Pipe','row':item['row'],'base_asset':item.get('pipe_id') or base_id}
    return None


def processed_registry(master_path):
    folder=os.path.join(os.path.dirname(os.path.abspath(master_path)), 'Logs')
    return folder, os.path.join(folder, 'processed_pdfs.json')


def trouble_ticket_workbook_path(master_path):
    return os.path.join(os.path.dirname(os.path.abspath(master_path)),'Trouble Tickets.xlsx')


def migrate_trouble_ticket_workbook_v60(ws):
    """Convert the v60/v61 layout to v62 while preserving every prior row."""
    last_row=max(1,max(ws.Cells(ws.Rows.Count,col).End(-4162).Row for col in (1,2,3,18)))
    rows=[]
    for row in range(2,last_row+1):
        old=[ws.Cells(row,col).Value for col in range(1,19)]
        if not any(value not in (None,'') for value in old): continue
        operator=old[1] if old[1] not in (None,'') else old[14]
        rows.append([
            old[2],old[11],'Open','',old[0],old[12],old[13],operator,
            old[4],old[3],old[5],old[6],old[7],old[8],old[9],old[10],
            old[15],old[16],old[17]
        ])
    ws.Cells.Clear()
    for col,header in enumerate(TROUBLE_TICKET_HEADERS,1): ws.Cells(1,col).Value=header
    for row_no,values in enumerate(rows,2):
        for col,value in enumerate(values,1): ws.Cells(row_no,col).Value=value


def prepare_trouble_ticket_workbook(excel, path, tickets):
    """Open/create the ticket workbook and stage only nonduplicate rows."""
    exists=os.path.exists(path)
    twb=excel.Workbooks.Open(path) if exists else excel.Workbooks.Add()
    ws=twb.Worksheets(1)
    if not exists: ws.Name='Trouble Tickets'
    used=ws.UsedRange
    truly_empty=(used.Rows.Count==1 and used.Columns.Count==1 and ws.Cells(1,1).Value in (None,''))
    if truly_empty:
        for col,header in enumerate(TROUBLE_TICKET_HEADERS,1): ws.Cells(1,col).Value=header
    else:
        old_actual=[str(ws.Cells(1,col).Value or '').strip() for col in range(1,len(TROUBLE_TICKET_HEADERS_V60)+1)]
        if old_actual==TROUBLE_TICKET_HEADERS_V60:
            migrate_trouble_ticket_workbook_v60(ws)
        actual=[str(ws.Cells(1,col).Value or '').strip() for col in range(1,len(TROUBLE_TICKET_HEADERS)+1)]
        if actual!=TROUBLE_TICKET_HEADERS:
            raise ValueError('Trouble Tickets.xlsx has an unexpected column layout. Close it and rename or move it so the updater can create the standard workbook safely.')

    for col in (1,6,7,13,14,19): ws.Columns(col).NumberFormat='@'
    ws.Columns(5).NumberFormat='mm/dd/yyyy'

    key_col=TROUBLE_TICKET_HEADERS.index('Ticket Key')+1
    last_row=max(1,max(ws.Cells(ws.Rows.Count,col).End(-4162).Row for col in (1,2,5,key_col)))  # xlUp
    existing_keys=set()
    for row in range(2,last_row+1):
        key=str(ws.Cells(row,key_col).Value or '').strip()
        if key: existing_keys.add(key)

    added=[]; skipped=0
    for ticket in tickets:
        key=ticket.get('ticket_key') or trouble_ticket_key(ticket)
        if key in existing_keys:
            skipped+=1; continue

        # Upgrade a matching v60 content key to the page-based identity once.
        # Future tickets are never deduplicated merely for sharing content/asset.
        legacy_key=legacy_trouble_ticket_key(ticket)
        legacy_row=next((row for row in range(2,last_row+1)
                         if str(ws.Cells(row,key_col).Value or '').strip()==legacy_key),None)
        if legacy_row:
            ws.Cells(legacy_row,key_col).Value=key
            existing_keys.discard(legacy_key); existing_keys.add(key)
            skipped+=1; continue

        target_asset=trouble_ticket_asset_key(ticket)
        related=[]
        if target_asset:
            for existing_row in range(2,last_row+1):
                existing_ticket={'pipe_id':ws.Cells(existing_row,1).Value,
                                 'upstream':ws.Cells(existing_row,13).Value,
                                 'downstream':ws.Cells(existing_row,14).Value}
                if trouble_ticket_asset_key(existing_ticket)==target_asset:
                    related.append(existing_row)
        row=(max(related)+1) if related else max(2,last_row+1)
        if row<=last_row:
            ws.Rows(row).Insert()
        last_row+=1
        values=[ticket.get('pipe_id',''),ticket.get('description',''),
                ticket.get('tracker_status','Open') or 'Open',ticket.get('resolution_notes',''),
                ticket.get('date'),ticket.get('wo',''),ticket.get('truck',''),
                ticket.get('operator') or ticket.get('reported_by',''),ticket.get('panel',''),
                ticket.get('street_name',''),ticket.get('area',''),ticket.get('service_type',''),
                ticket.get('upstream',''),ticket.get('downstream',''),ticket.get('map_length'),
                ticket.get('pipe_size',''),ticket.get('source_pdf',''),ticket.get('source_page',''),key]
        for col,value in enumerate(values,1):
            if col==5 and isinstance(value,datetime): write_excel_date(ws.Cells(row,col),value)
            else: ws.Cells(row,col).Value=value
        existing_keys.add(key); added.append(ticket)

    # Apply the standard tracker style without changing any existing values.
    header=ws.Range(ws.Cells(1,1),ws.Cells(1,len(TROUBLE_TICKET_HEADERS)))
    header.Font.Bold=True; header.Font.Color=16777215; header.Interior.Color=5407764
    header.HorizontalAlignment=-4108; header.VerticalAlignment=-4108
    if not ws.AutoFilterMode: header.AutoFilter()
    widths=[16,45,18,42,12,13,10,18,14,22,30,18,20,22,12,11,25,9,12]
    for col,width in enumerate(widths,1): ws.Columns(col).ColumnWidth=width
    ws.Columns(2).WrapText=True; ws.Columns(4).WrapText=True
    try:
        status_range=ws.Range(ws.Cells(2,3),ws.Cells(10000,3))
        status_range.Validation.Delete()
        status_range.Validation.Add(Type=3,AlertStyle=1,Operator=1,
                                    Formula1='Open,In Progress,Resolved,No Action Needed')
        status_range.Validation.IgnoreBlank=True; status_range.Validation.InCellDropdown=True
    except Exception: pass
    ws.Columns(key_col).Hidden=True; ws.Rows(1).RowHeight=28
    try:
        ws.Activate(); excel.ActiveWindow.SplitRow=1; excel.ActiveWindow.FreezePanes=True
    except Exception: pass
    return twb,added,skipped,exists


class LayoutConfirmDialog(tk.Toplevel):
    """Let the user verify or correct a newly detected pair-table layout."""
    def __init__(self,parent,layout,page_number):
        super().__init__(parent); self.result=None; self.layout=layout
        apply_app_icon(self)
        self.title('Confirm PDF Table Layout'); self.transient(parent); self.grab_set(); self.resizable(True,False)
        ttk.Label(self,text=f"PDF page {page_number} — {layout['kind'].title()} table",font=('Segoe UI',11,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',padx=14,pady=(12,4))
        ttk.Label(self,text=f"Detection confidence: {layout.get('confidence',0)}%   Method: {layout.get('source','unknown')}").grid(row=1,column=0,columnspan=2,sticky='w',padx=14,pady=(0,8))
        if layout.get('warnings'):
            ttk.Label(self,text='; '.join(layout['warnings']),foreground='#9b0000',wraplength=700).grid(row=2,column=0,columnspan=2,sticky='w',padx=14,pady=(0,8))
        self.headers=list(layout.get('headers',[])); self.vars={}
        labels={'up':'Upstream node (UP_MH)','down':'Downstream node (DN_MH)',
                'value':'Wheel Walk' if layout['kind']=='cleaning' else 'Surveyed/Video Length','date':'Activity Date'}
        start=3
        for offset,role in enumerate(('up','down','value','date')):
            ttk.Label(self,text=labels[role]+':').grid(row=start+offset,column=0,sticky='e',padx=(14,7),pady=5)
            initial=''
            idx=layout.get('role_indices',{}).get(role)
            if idx is not None and 0<=idx<len(self.headers): initial=self.headers[idx]
            var=tk.StringVar(value=initial); self.vars[role]=var
            combo=ttk.Combobox(self,textvariable=var,values=self.headers,state='readonly',width=58)
            combo.grid(row=start+offset,column=1,sticky='ew',padx=(0,14),pady=5)
        ttk.Label(self,text='Confirm these mappings before asset rows are processed. Corrections apply to every matching table layout in this PDF.',wraplength=700).grid(row=start+4,column=0,columnspan=2,sticky='w',padx=14,pady=(8,5))
        buttons=ttk.Frame(self); buttons.grid(row=start+5,column=0,columnspan=2,pady=(5,12))
        ttk.Button(buttons,text='Confirm Layout',command=self.accept,style='Primary.TButton').pack(side='left',padx=6)
        ttk.Button(buttons,text='Cancel Analysis',command=self.cancel).pack(side='left',padx=6)
        self.columnconfigure(1,weight=1); self.protocol('WM_DELETE_WINDOW',self.cancel)
        self.update_idletasks(); self.geometry(f'+{parent.winfo_rootx()+80}+{parent.winfo_rooty()+80}')
    def accept(self):
        if any(not v.get() for v in self.vars.values()):
            messagebox.showwarning('Incomplete layout','Choose a column for all four fields.',parent=self); return
        indices={role:self.headers.index(var.get()) for role,var in self.vars.items()}
        if len(set(indices.values()))<4:
            messagebox.showwarning('Check column mappings','UP_MH, DN_MH, activity value, and activity date must use four different columns.',parent=self); return
        self.result=indices; self.destroy()
    def cancel(self): self.result=None; self.destroy()


class ConfirmDialog(tk.Toplevel):
    def __init__(self, parent, guesses):
        super().__init__(parent); self.result=None
        apply_app_icon(self)
        self.guessed_date=guesses.get('date')
        self.title('Confirm Work Order'); self.transient(parent); self.grab_set()
        self.resizable(False,False)
        ttk.Label(self,text='Confirm Work Order Information',font=('Segoe UI',12,'bold')).grid(row=0,column=0,columnspan=3,padx=12,pady=(12,8),sticky='w')
        self.vars={}
        vals=[('W/O',guesses.get('wo',''),'wo_preview'),('Operator (full name)',guesses.get('operator',''),'operator_preview'),('Truck',guesses.get('truck',''),'truck_preview')]
        self.crop_photos=[]
        for r,(lab,val,preview_key) in enumerate(vals,1):
            ttk.Label(self,text=lab+':').grid(row=r,column=0,sticky='e',padx=(12,6),pady=6)
            v=tk.StringVar(value=val); self.vars[lab]=v
            e=ttk.Entry(self,textvariable=v,width=34); e.grid(row=r,column=1,sticky='w',padx=6,pady=6)
            if not str(val).strip(): e.focus_set()
            crop=Image.fromarray(guesses.get(preview_key,guesses['preview'])); crop.thumbnail((360,75))
            photo=ImageTk.PhotoImage(crop); self.crop_photos.append(photo)
            ttk.Label(self,image=photo).grid(row=r,column=2,sticky='w',padx=(6,12),pady=4)
        self.initials_var=tk.StringVar(value=operator_master_name(self.vars['Operator (full name)'].get()))
        ttk.Label(self,text='Operator:').grid(row=4,column=0,sticky='e',padx=(12,6),pady=5)
        ttk.Label(self,textvariable=self.initials_var,font=('Segoe UI',10,'bold')).grid(row=4,column=1,sticky='w',padx=6,pady=5)
        self.vars['Operator (full name)'].trace_add('write', lambda *_: self.initials_var.set(operator_master_name(self.vars['Operator (full name)'].get()) or 'NEEDS FIRST + LAST'))
        ttk.Label(self,text='Check each scan image beside its field. OCR is only a pre-filled suggestion.',foreground='#8A5200').grid(row=5,column=0,columnspan=3,padx=12,pady=(5,8))
        b=ttk.Frame(self); b.grid(row=6,column=0,columnspan=3,pady=(0,12))
        ttk.Button(b,text='Cancel',command=self.cancel).pack(side='left',padx=6)
        ttk.Button(b,text='Confirm',command=self.ok,style='Primary.TButton').pack(side='left',padx=6)
        self.protocol('WM_DELETE_WINDOW',self.cancel)
    def ok(self):
        wo=self.vars['W/O'].get().strip(); truck=self.vars['Truck'].get().strip().upper(); full_op=self.vars['Operator (full name)'].get().strip()
        if not re.fullmatch(r'\d{4,5}', wo):
            messagebox.showwarning('Work order number','W/O must be 4 or 5 digits.',parent=self); return
        if not re.fullmatch(r'[A-Z]{2}\d{2}',truck):
            messagebox.showwarning('Check truck','Truck must be exactly 2 letters followed by 2 numbers, such as CT01.',parent=self); return
        master_op=operator_master_name(full_op)
        if not master_op:
            messagebox.showwarning('Operator name','Confirm or enter the operator name.',parent=self); return
        self.result={'wo':wo,'truck':truck,'operator':master_op,'operator_full':full_op,'date':self.guessed_date}; self.destroy()
    def cancel(self): self.result=None; self.destroy()


class ProgressFillButton(tk.Canvas):
    """Fixed-label button whose background gradually fills during processing."""
    def __init__(self,parent,text,command,width=145,height=35):
        super().__init__(parent,width=width,height=height,highlightthickness=0,
                         borderwidth=0,background='#f3f6fa',cursor='hand2')
        # Never reuse tkinter.Misc._w: Tkinter stores the widget's Tcl command
        # name there. Overwriting it makes every canvas command target "145".
        self._button_width=width; self._button_height=height; self._command=command
        self._enabled=True; self._working=False; self._progress=0.0
        self._base=self.create_rectangle(1,1,width-1,height-1,fill='#0878d1',outline='#0668b5',width=1)
        self._fill=self.create_rectangle(2,2,2,height-2,fill='#18a8df',outline='',state='hidden')
        self._text=self.create_text(width//2,height//2,text=text,fill='white',font=('Segoe UI Semibold',9))
        self.bind('<Button-1>',self._clicked); self.bind('<Enter>',self._enter); self.bind('<Leave>',self._leave)
    def _clicked(self,event=None):
        if self._enabled and not self._working and self._command: self._command()
    def _enter(self,event=None):
        if self._enabled and not self._working: self.itemconfigure(self._base,fill='#0567b5')
    def _leave(self,event=None):
        if not self._working: self.itemconfigure(self._base,fill='#0878d1')
    def start_progress(self):
        if self._working: return
        self._enabled=False; self._working=True; self._progress=3.0
        self.configure(cursor='arrow'); self.itemconfigure(self._base,fill='#075f9f')
        self.itemconfigure(self._fill,state='normal'); self._draw_progress()
    def advance_progress(self,amount=.8):
        if not self._working: return
        # Processing checkpoints advance the fill; reserve the final portion for completion.
        self._progress=min(94.0,self._progress+float(amount)); self._draw_progress()
    def _draw_progress(self):
        right=2+(self._button_width-4)*(self._progress/100.0)
        self.coords(self._fill,2,2,right,self._button_height-2)
        self.tag_raise(self._text)
    def stop_progress(self):
        self._working=False; self._enabled=True; self._progress=0.0
        self.itemconfigure(self._fill,state='hidden')
        self.itemconfigure(self._base,fill='#0878d1'); self.configure(cursor='hand2')


class App(tk.Tk):
    def __init__(self):
        super().__init__(); apply_app_icon(self); self.title(APP_TITLE)
        self.ui_scale=ui_scale_for(self)
        screen_w=max(1,self.winfo_screenwidth()); screen_h=max(1,self.winfo_screenheight())
        default_w=min(self.spx(1180),max(900,int(screen_w*.94)))
        default_h=min(self.spx(760),max(600,int(screen_h*.90)))
        self.geometry(f'{default_w}x{default_h}')
        self.minsize(min(self.spx(960),max(760,int(screen_w*.90))),
                     min(self.spx(620),max(560,int(screen_h*.85))))
        self.pdf_path=tk.StringVar(master=self); self.master_path=tk.StringVar(master=self); self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.pdf_hash=''
        self._analysis_running=False; self.cancel_requested=False
        self.configure(background='#f3f6fa')
        self.configure_styles()
        self.build_ui()
    def spx(self,value):
        return max(1,int(round(float(value)*self.ui_scale)))
    def configure_styles(self):
        style=ttk.Style(self)
        try: style.theme_use('clam')
        except Exception: pass
        style.configure('.',font=('Segoe UI',10),background='#f3f6fa',foreground='#172033')
        style.configure('TFrame',background='#f3f6fa')
        style.configure('Header.TFrame',background='#0b2f5b')
        style.configure('Header.TLabel',background='#0b2f5b',foreground='white',font=('Segoe UI Semibold',19))
        style.configure('HeaderSub.TLabel',background='#0b2f5b',foreground='#cfe4ff',font=('Segoe UI',10))
        style.configure('TLabelframe',background='#f3f6fa',bordercolor='#c9d5e3',relief='solid')
        style.configure('TLabelframe.Label',background='#f3f6fa',foreground='#28415f',font=('Segoe UI Semibold',10))
        style.configure('TEntry',fieldbackground='white',padding=self.spx(6),bordercolor='#b7c5d6')
        style.configure('TButton',padding=(self.spx(12),self.spx(7)),font=('Segoe UI Semibold',9))
        style.configure('Primary.TButton',background='#0878d1',foreground='white',bordercolor='#0878d1')
        style.map('Primary.TButton',background=[('active','#0567b5'),('pressed','#045a9e')])
        style.configure('Success.TButton',background='#148452',foreground='white',bordercolor='#148452')
        style.map('Success.TButton',background=[('active','#0f7145'),('pressed','#0c613b')])
        style.configure('Danger.TButton',background='#b33a3a',foreground='white',bordercolor='#b33a3a')
        style.map('Danger.TButton',background=[('active','#982f2f'),('pressed','#812828')])
        style.configure('Status.TLabel',background='#e8f2fc',foreground='#183b5f',padding=(self.spx(10),self.spx(8)),font=('Segoe UI',9))
        style.configure('Treeview',background='white',fieldbackground='white',foreground='#172033',rowheight=self.spx(28),bordercolor='#c9d5e3',font=('Segoe UI',9))
        style.configure('Treeview.Heading',background='#183f68',foreground='white',font=('Segoe UI Semibold',9),padding=(self.spx(7),self.spx(7)),relief='flat')
        style.map('Treeview',background=[('selected','#0878d1')],foreground=[('selected','white')])
        style.map('Treeview.Heading',background=[('active','#22527f')])
        style.configure('Hint.TLabel',background='#f3f6fa',foreground='#5d6c7d',font=('Segoe UI',9))
    def build_ui(self):
        top=ttk.LabelFrame(self,text='Source files',padding=12); top.pack(fill='x',padx=14,pady=(14,10))
        for row,(lab,var,typ) in enumerate([('Scanned PDF',self.pdf_path,'pdf'),('Master spreadsheet',self.master_path,'xlsx')]):
            ttk.Label(top,text=lab+':',width=18).grid(row=row,column=0,sticky='w',pady=5)
            ttk.Entry(top,textvariable=var).grid(row=row,column=1,sticky='ew',padx=8,pady=5)
            ttk.Button(top,text='Browse…',command=lambda v=var,t=typ:self.browse(v,t)).grid(row=row,column=2,padx=(4,0),pady=5)
        top.columnconfigure(1,weight=1)
        bar=ttk.Frame(self,padding=(14,0,14,6)); bar.pack(fill='x')
        controls=ttk.Frame(bar); controls.pack(fill='x')
        self.analyze_button=ProgressFillButton(controls,text='1. Analyze PDF',command=self.analyze,width=self.spx(145),height=self.spx(35))
        self.analyze_button.pack(side='left',padx=(0,8))
        ttk.Button(controls,text='Edit Selected',command=self.edit_selected).pack(side='left',padx=8)
        ttk.Button(controls,text='2. Update Master',command=self.update_master,style='Success.TButton').pack(side='left',padx=8)
        self.cancel_button=ttk.Button(controls,text='Cancel Current Process',command=self.cancel_current_process,style='Danger.TButton',state='disabled')
        self.cancel_button.pack(side='left',padx=(18,8))
        self.status=tk.StringVar(master=self, value='Select the PDF and master spreadsheet, then click Analyze PDF.')
        # Status and validation details get their own full-width line. Dynamic
        # wrapping keeps long warning summaries readable at any window size.
        self.status_label=ttk.Label(bar,textvariable=self.status,justify='left',anchor='w',wraplength=1000,style='Status.TLabel')
        self.status_label.pack(fill='x',pady=(9,0))
        bar.bind('<Configure>',lambda e:self.status_label.configure(wraplength=max(300,e.width-8)))
        cols=('type','asset','length','date','wo','truck','operator','status')
        table_frame=ttk.LabelFrame(self,text='Extracted rows',padding=(8,7)); table_frame.pack(fill='both',expand=True,padx=14,pady=(6,10))
        self.tree=ttk.Treeview(table_frame,columns=cols,show='headings',selectmode='browse')
        xscroll=ttk.Scrollbar(table_frame,orient='horizontal',command=self.tree.xview)
        yscroll=ttk.Scrollbar(table_frame,orient='vertical',command=self.tree.yview)
        self.tree.configure(xscrollcommand=xscroll.set,yscrollcommand=yscroll.set)
        heads={'type':'Type','asset':'Asset / Nodes','length':'Video / Wheel Walk / Map','date':'Date','wo':'W/O','truck':'Truck','operator':'Operator','status':'Status'}
        widths={'type':80,'asset':240,'length':145,'date':105,'wo':85,'truck':85,'operator':170,'status':520}
        for c in cols:
            scaled_width=self.spx(widths[c])
            self.tree.heading(c,text=heads[c]); self.tree.column(c,width=scaled_width,minwidth=scaled_width,stretch=c in ('asset','status'),anchor='center' if c not in ('asset','status') else 'w')
        self.tree.grid(row=0,column=0,sticky='nsew')
        self.tree.bind('<Double-1>',self.edit_double_clicked)
        yscroll.grid(row=0,column=1,sticky='ns')
        xscroll.grid(row=1,column=0,sticky='ew')
        table_frame.rowconfigure(0,weight=1); table_frame.columnconfigure(0,weight=1)
        # Length warnings are deliberately prominent during review.  The warning is
        # Length warnings are also appended to the pipe NOTES field when the master is updated.
        self.tree.tag_configure('total_warning', background='#8b0000', foreground='white')
        self.tree.tag_configure('length_warning', background='#c62828', foreground='white')
        self.tree.tag_configure('check_warning', background='#ffcccc', foreground='#7a0000')
        ttk.Label(self,text='Colored rows need review—see Status for the reason. Nothing is written until Update Master is clicked. Close the master workbook before updating.',style='Hint.TLabel',wraplength=self.spx(1100),justify='left',padding=(self.spx(14),0,self.spx(14),self.spx(12))).pack(fill='x')
    def browse(self,var,typ):
        ft=[('PDF files','*.pdf')] if typ=='pdf' else [('Excel files','*.xlsx')]
        p=filedialog.askopenfilename(filetypes=ft)
        if p:
            old=var.get().strip()
            changed=not old or os.path.normcase(os.path.abspath(p))!=os.path.normcase(os.path.abspath(old))
            var.set(p)
            if typ=='pdf' and changed:
                self.clear_extracted_rows('New PDF selected. Click Analyze PDF to extract its rows.')
    def clear_extracted_rows(self,status_text=None):
        self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.pdf_hash=''
        if hasattr(self,'tree'): self.tree.delete(*self.tree.get_children())
        if status_text and hasattr(self,'status'): self.status.set(status_text)
    def edit_double_clicked(self,event):
        iid=self.tree.identify_row(event.y)
        if not iid: return
        self.tree.selection_set(iid); self.tree.focus(iid)
        self.edit_selected()
    def cancel_current_process(self):
        if not getattr(self,'_analysis_running',False): return
        self.cancel_requested=True
        self.status.set('Cancelling current analysis…')
    def start_analysis_animation(self):
        self._analysis_running=True; self.cancel_requested=False
        self.cancel_button.configure(state='normal')
        self.analyze_button.start_progress()
    def stop_analysis_animation(self):
        self._analysis_running=False; self.cancel_requested=False
        try:
            self.analyze_button.stop_progress()
            self.cancel_button.configure(state='disabled')
        except Exception: pass
    def pump_analysis_ui(self):
        if getattr(self,'_analysis_running',False): self.analyze_button.advance_progress()
        self.update_idletasks()
        try: self.update()
        except tk.TclError: raise AnalysisCancelled()
        if getattr(self,'cancel_requested',False): raise AnalysisCancelled()
    def show_summary_record(self,index,follow=False):
        """Insert or refresh one summary row while analysis is still running."""
        r=self.records[index]
        tags=()
        if any(str(w).startswith('TOTAL LENGTH') for w in r.get('warnings',[])):
            tags=('total_warning',)
        elif str(r.get('status','')).startswith('LENGTH DIFF'):
            tags=('length_warning',)
        elif record_needs_review(r):
            tags=('check_warning',)
        values=(r['kind'],r['display_asset'],'' if r['video_length'] is None else f"{r['video_length']:.1f}",
                fmt_date(r['date']),r['wo'],r['truck'],r['operator'],review_status(r))
        iid=f'record:{index}'
        if self.tree.exists(iid): self.tree.item(iid,values=values,tags=tags)
        else: self.tree.insert('', 'end',iid=iid,values=values,tags=tags)
        if follow: self.tree.see(iid)
        # OCR runs synchronously on the GUI thread. update_idletasks() can leave
        # native Windows painting queued until a long OCR loop ends, so process a
        # complete Tk event cycle before starting the next row.
        if getattr(self,'_analysis_running',False):
            self.pump_analysis_ui()
        else:
            self.update_idletasks()
    def show_summary_ticket(self,index,follow=False):
        """Show a trouble ticket in the same live review table."""
        ticket=self.trouble_tickets[index]
        status=trouble_ticket_status(ticket)
        ticket['review_status']=status
        values=('Trouble',ticket.get('pipe_id',''),
                '' if ticket.get('map_length') is None else f"{ticket['map_length']:.1f}",
                fmt_date(ticket.get('date')),ticket.get('wo',''),ticket.get('truck',''),
                ticket.get('operator',''),status)
        iid=f'ticket:{index}'
        tags=('check_warning',) if status.startswith('Review') else ()
        if self.tree.exists(iid): self.tree.item(iid,values=values,tags=tags)
        else: self.tree.insert('','end',iid=iid,values=values,tags=tags)
        if follow: self.tree.see(iid)
        if getattr(self,'_analysis_running',False): self.pump_analysis_ui()
        else: self.update_idletasks()
    def commit_extracted_record(self,rec,current_wo,use_date,idx,page_number,processed):
        """Finish one parsed row and publish it to the live summary immediately."""
        if rec.get('kind')=='Pipe': refresh_length_status(rec)
        rec_date=rec.pop('row_date',None) or use_date
        rec.update({'wo':current_wo['wo'],'truck':current_wo['truck'],
                    'operator':current_wo['operator'],'date':rec_date})
        if rec['kind'] in ('Pipe','Cleaning'):
            if rec['kind']=='Pipe' and str(rec.get('status','')).startswith('NEW PIPE') and not rec.get('up') and not rec.get('down'):
                rec['display_asset']=rec.get('asset','')
            else:
                rec['display_asset']=f"{rec.get('up','')} -> {rec.get('down','')}" + (f"  (pipe {rec.get('asset')})" if rec.get('asset') else '')
            rec['display_asset_base']=rec['display_asset']
        else:
            rec['display_asset']=rec.get('asset','')
        rec['source_page']=page_number; rec['warnings']=list(rec.pop('validation_warnings',[]))
        if str(rec.get('status','')).startswith(('NEW PIPE','NEW MANHOLE')):
            base_info=new_asset_base_info(rec,idx)
            if base_info:
                rec['new_asset_base_row']=base_info['row']
                rec['new_asset_base_asset']=base_info['base_asset']
                label='pipe' if base_info['kind']=='Pipe' else 'manhole'
                rec['new_asset_approved']=messagebox.askyesno(
                    f'New {label.title()} Detected',
                    f"{rec['status']}\n\nScanned asset:\n{rec['display_asset']}\n\n"
                    f"Existing base {label}:\n{base_info['base_asset']}\n\n"
                    f"Add the new {label} directly below its base row in the master?\n\n"
                    'The inserted master row will be highlighted green.')
            else:
                rec['new_asset_approved']=False
                rec['warnings'].append('BASE MASTER ROW NOT FOUND')
        if rec['kind'] in ('Pipe','Cleaning'):
            master_item=idx['pipes'].get((asset_key(rec.get('up','')),asset_key(rec.get('down',''))))
        else:
            master_item=idx['manholes'].get(rec.get('asset_key') or asset_key(rec.get('asset','')))
        existing_key='clean_existing' if rec['kind']=='Cleaning' else 'existing'
        wo_key='clean_existing_wo' if rec['kind']=='Cleaning' else 'existing_wo'
        if master_item and master_item.get(existing_key): rec['warnings'].append('EXISTING DATA')
        same_wo=bool(master_item and master_item.get(wo_key)==current_wo['wo'])
        if same_wo: rec['warnings'].append('W/O ALREADY ENTERED')
        if processed and same_wo: rec['warnings'].append('PDF PREVIOUSLY PROCESSED')
        split_identity=split_pipe_identity(rec)
        if split_identity:
            for index,existing in enumerate(self.records):
                if (existing.get('wo')==rec.get('wo') and
                        split_pipe_identity(existing)==split_identity):
                    combine_split_pipe_records(existing,rec)
                    self.status.set(f'Processing page {page_number} — {len(self.records)} row(s) found; MSA detected...')
                    self.show_summary_record(index,follow=True)
                    return
        self.records.append(rec)
        self.status.set(f'Processing page {page_number} — {len(self.records)} row(s) found...')
        self.show_summary_record(len(self.records)-1,follow=True)
    def analyze(self):
        if not self.pdf_path.get() or not self.master_path.get(): messagebox.showwarning('Select files','Choose both the scanned PDF and the master spreadsheet.'); return
        tess=find_tesseract()
        if not tess:
            messagebox.showerror('Tesseract OCR not found','Install Tesseract OCR for Windows, then reopen this program.\n\nThe setup README includes the usual install location.'); return
        pytesseract.pytesseract.tesseract_cmd=tess
        self.start_analysis_animation()
        self.status.set('Reading master spreadsheet...'); self.pump_analysis_ui()
        try: idx=load_master_index(self.master_path.get()); self.master_index=idx
        except AnalysisCancelled:
            self.stop_analysis_animation(); self.status.set('Analysis cancelled.'); return
        except Exception as e:
            self.stop_analysis_animation(); messagebox.showerror('Master spreadsheet error',str(e)); return
        self.records=[]; self.trouble_tickets=[]; self.groups=[]; self.total_validations=[]; self.tree.delete(*self.tree.get_children())
        try: self.pdf_hash=hashlib.sha256(open(self.pdf_path.get(),'rb').read()).hexdigest()
        except Exception: self.pdf_hash=''
        init_ocr_cache(self.pdf_hash)
        log_folder, registry_path=processed_registry(self.master_path.get())
        try: processed=self.pdf_hash in json.load(open(registry_path,encoding='utf-8'))
        except Exception: processed=False
        try: doc=pymupdf.open(self.pdf_path.get())
        except Exception as e:
            self.stop_analysis_animation(); messagebox.showerror('PDF error',str(e)); return
        current_wo=None; current_list_kind=None; current_report_date=None; group_no=0
        try:
            # Stage 1: classify the complete packet first. No spreadsheet rows are
            # extracted until every work order has been confirmed.
            page_info=[]
            for pi,page in enumerate(doc):
                self.status.set(f'Finding work orders: page {pi+1} of {len(doc)}...'); self.pump_analysis_ui()
                orient,deg,txt,kind=classify_for_profile(page,idx.get('profile','reno'))
                page_info.append({'index':pi,'page':page,'orient':orient,'deg':deg,'text':txt,'kind':kind})

            work_items=[item for item in page_info if item['kind']=='workorder']
            trouble_items=[item for item in page_info if item['kind']=='trouble']
            if not work_items and not trouble_items:
                messagebox.showwarning('No work orders found','No work-order pages were detected, so no spreadsheet pages were processed.'); return

            # Prepare all handwriting crops/OCR guesses before displaying the first
            # dialog, so confirmation popups appear back-to-back without OCR waits.
            for n,item in enumerate(work_items,1):
                self.status.set(f'Preparing work order {n} of {len(work_items)}...'); self.pump_analysis_ui()
                item['guesses']=ocr_workorder_guesses(item['page'],idx)

            confirmed_by_page={}
            for n,item in enumerate(work_items,1):
                self.status.set(f'Confirm work order {n} of {len(work_items)}...'); self.pump_analysis_ui()
                dlg=ConfirmDialog(self,item['guesses']); self.wait_window(dlg)
                if dlg.result is None:
                    self.status.set('Analysis cancelled.'); return
                confirmed_by_page[item['index']]=dlg.result
                self.groups.append(dlg.result.copy())

            # Prepare and confirm every unique pair-table layout before any asset
            # rows are processed. Continuation pages inherit the preceding list kind.
            inherited_kind=None; after_workorder=False
            for item in page_info:
                if item['kind']=='workorder': inherited_kind=None; after_workorder=True; item['effective_kind']='workorder'
                elif item['kind']=='trouble': inherited_kind=None; item['effective_kind']='trouble'
                elif item['kind'] in ('pipes','manholes','cleaning'):
                    inherited_kind=item['kind']; item['effective_kind']=item['kind']
                elif item['kind']=='other' and inherited_kind: item['effective_kind']=inherited_kind
                else: item['effective_kind']=item['kind']
                item['after_workorder']=after_workorder
            confirmed_layouts={}; saved_layouts=load_layout_profiles()
            if idx.get('profile') in ('year15','phase2_year1'):
                pair_items=[]
                for item in page_info:
                    kind=item.get('effective_kind')
                    if kind in ('pipes','cleaning'):
                        pair_items.append(item); continue
                    if kind=='other' and item.get('after_workorder'):
                        # If header classification failed, let grid/header/master
                        # evidence test both pair-table activities before ignoring it.
                        options=[]
                        for candidate_kind in ('cleaning','pipes'):
                            candidate=prepare_year15_pair_layout(item['page'],idx,candidate_kind)
                            roles=candidate.get('role_indices',{})
                            if all(x in roles for x in ('up','down')) and candidate.get('column_boxes'):
                                options.append((len(roles),candidate.get('master_pair_score',0),candidate.get('confidence',0),candidate_kind,candidate))
                        if options:
                            _,_,_,chosen_kind,chosen=max(options,key=lambda x:x[:3])
                            item['effective_kind']=chosen_kind; item['preprepared_layout']=chosen; pair_items.append(item)
                for n,item in enumerate(pair_items,1):
                    kind=item['effective_kind']; pi=item['index']
                    self.status.set(f'Preparing table layout {n} of {len(pair_items)}...'); self.pump_analysis_ui()
                    layout=item.pop('preprepared_layout',None) or prepare_year15_pair_layout(item['page'],idx,kind)
                    if not layout.get('headers'):
                        messagebox.showerror('Table layout could not be detected',
                            f"PDF page {pi+1} does not contain enough grid information to map its columns safely.\n\n"
                            'No asset rows from this page were processed.'); return
                    fingerprint=layout.get('fingerprint') or f'{kind}-page-{pi+1}'
                    if fingerprint in confirmed_layouts:
                        apply_confirmed_layout(layout,confirmed_layouts[fingerprint])
                    else:
                        detected_roles=layout.get('role_indices',{})
                        if layout.get('confidence',0)>=100 and all(k in detected_roles for k in ('up','down','value','date')):
                            # A complete 100% native detection is already unambiguous;
                            # do not interrupt analysis with a confirmation dialog.
                            confirmed_layouts[fingerprint]=dict(detected_roles)
                        else:
                            saved=saved_layouts.get(fingerprint,{}).get('role_indices')
                            if saved and all(k in saved for k in ('up','down','value','date')) and all(0<=int(v)<len(layout['column_boxes']) for v in saved.values()):
                                apply_confirmed_layout(layout,saved); layout['source']=layout.get('source','')+' / saved layout'
                                confirmed_layouts[fingerprint]=dict(layout.get('role_indices',saved))
                            else:
                                dlg=LayoutConfirmDialog(self,layout,pi+1); self.wait_window(dlg)
                                if dlg.result is None:
                                    self.status.set('Analysis cancelled.'); return
                                confirmed_layouts[fingerprint]=dlg.result
                                apply_confirmed_layout(layout,dlg.result)
                                save_layout_profile(fingerprint,layout,dlg.result)
                    item['pair_layout']=layout

            # Stage 2: every work order is now confirmed. Process spreadsheet pages
            # sequentially and attach them to the most recent confirmed work order.
            self.status.set('All work orders confirmed. Processing spreadsheet pages...'); self.pump_analysis_ui()
            ignored_pages=[]; validation_reports=[]; total_sources={}
            for item in page_info:
                pi=item['index']; page=item['page']; txt=item['text']; kind=item.get('effective_kind',item['kind'])
                if kind=='workorder':
                    current_wo=confirmed_by_page[pi]
                    group_no += 1
                    current_list_kind=None
                    current_report_date=None
                    continue

                self.status.set(f'Processing spreadsheet pages: page {pi+1} of {len(doc)}...'); self.pump_analysis_ui()

                if kind=='trouble':
                    ticket=parse_trouble_ticket(page,pi+1,current_wo,self.pdf_path.get())
                    if ticket['ticket_key'] not in {t['ticket_key'] for t in self.trouble_tickets}:
                        self.trouble_tickets.append(ticket)
                        self.status.set(f'Processing page {pi+1} — {len(self.trouble_tickets)} trouble ticket(s) found...')
                        self.show_summary_ticket(len(self.trouble_tickets)-1,follow=True)
                    current_list_kind=None
                    continue

                if current_wo is None:
                    # Never attach spreadsheet rows to an unknown work order.
                    ignored_pages.append((pi+1,'no preceding confirmed work order'))
                    continue

                if kind in ('pipes','manholes','cleaning'):
                    current_list_kind=kind
                elif kind=='other' and current_list_kind:
                    # A list can span multiple pages. If a continuation page does not repeat
                    # enough header text for OCR classification, keep it with the current list.
                    kind=current_list_kind
                else:
                    ignored_pages.append((pi+1,'unrecognized or irrelevant document'))
                    continue

                page_date=parse_date_text(txt)
                if page_date:
                    current_report_date=page_date
                use_date=current_report_date or current_wo.get('date') or parse_date_text(txt)

                emit=lambda rec: self.commit_extracted_record(rec,current_wo,use_date,idx,pi+1,processed)
                if idx.get('profile') in ('year15', 'phase2_year1'):
                    if kind=='pipes': data=parse_year15_pair_list(page,idx,'pipes',item.get('pair_layout'),emit,self.pump_analysis_ui,use_date)
                    elif kind=='cleaning': data=parse_year15_pair_list(page,idx,'cleaning',item.get('pair_layout'),emit,self.pump_analysis_ui,use_date)
                    else: data=parse_year15_manholes(page,idx,emit,self.pump_analysis_ui)
                else:
                    # Reno lists can contain many OCR rows on one page. Publish each
                    # completed row from inside the parser rather than waiting for the
                    # entire page to return.
                    data=parse_pipe_list(page,idx,txt,emit,self.pump_analysis_ui) if kind=='pipes' else parse_manhole_list(page,idx,txt,emit,self.pump_analysis_ui)
                if idx.get('profile') in ('year15','phase2_year1') and kind in ('pipes','cleaning'):
                    layout=item.get('pair_layout') or {}
                    check_kind='Cleaning' if kind=='cleaning' else 'Pipe'
                    total_sources.setdefault((str(current_wo.get('wo','')),check_kind),[]).append(
                        {'page':pi+1,'info':dict(layout.get('printed_total_info') or {})})
                if not data:
                    messagebox.showwarning('Spreadsheet page could not be read',
                        f'PDF page {pi+1} was detected as a {kind} spreadsheet page, but it produced zero asset rows.\n\nThe page was not silently ignored.')
                report=validate_page_rows(data,kind,txt,pi+1,item.get('pair_layout'),idx.get('profile'))
                validation_reports.append(report)
            self.verify_length_totals(total_sources)
            if ignored_pages:
                ignored_text='\n'.join(f'Page {page_no}: {reason}' for page_no,reason in ignored_pages)
                messagebox.showinfo('Ignored PDF Pages',
                    'The following PDF pages were intentionally ignored and were not used to update the master:\n\n'+ignored_text)
            validation_issues=[r for r in validation_reports if r['issues']]
            if validation_issues:
                lines=[]
                for r in validation_issues:
                    lines.append(f"Page {r['page']} ({r['kind']}): {r['rows']} rows, {r['matched']} matched — "+'; '.join(r['issues']))
                messagebox.showwarning('PDF Validation Warnings',
                    'Automatic validation found items that need review:\n\n'+'\n'.join(lines))
        except AnalysisCancelled:
            self.clear_extracted_rows('Analysis cancelled. No extracted rows are available for update.')
            return
        finally:
            doc.close()
            save_ocr_cache()
            self.stop_analysis_animation()
        seen=set()
        for row_i,r in enumerate(self.records):
            key=((r.get('kind'),asset_key(r.get('up','')),asset_key(r.get('down',''))) if r.get('kind') in ('Pipe','Cleaning')
                 else (r.get('kind'),r.get('asset_key') or asset_key(r.get('asset',''))))
            if r.get('skip_update'): key=(key,'unmatched',r.get('source_page'),row_i)
            if key in seen:
                r.setdefault('warnings',[]).append('DUPLICATE IN PDF'); r['skip_update']=True
            seen.add(key)
        # Duplicate detection spans pages, so refresh rows once at the end to show
        # any warnings discovered after their initial real-time insertion.
        for i in range(len(self.records)):
            self.show_summary_record(i)
        for i in range(len(self.trouble_tickets)):
            self.show_summary_ticket(i)
        length_warnings=sum(1 for r in self.records if str(r.get('status','')).startswith('LENGTH DIFF'))
        total_failures=sum(1 for check in self.total_validations if not check.get('passed'))
        other_warnings=sum(1 for r in self.records if record_needs_review(r) and not str(r.get('status','')).startswith('LENGTH DIFF') and not any(str(w).startswith('TOTAL LENGTH') for w in r.get('warnings',[])))
        validation_warning_count=sum(len(r['issues']) for r in validation_reports)
        ticket_reviews=sum(1 for t in self.trouble_tickets if trouble_ticket_status(t).startswith('Review'))
        if length_warnings or total_failures or other_warnings or validation_warning_count or ticket_reviews:
            bits=[]
            if total_failures: bits.append(f'{total_failures} TOTAL LENGTH VALIDATION FAILURE(S) — UPDATE MASTER BLOCKED')
            if length_warnings: bits.append(f'{length_warnings} length difference warning(s) > {LENGTH_DIFF_THRESHOLD:.1f}')
            if other_warnings: bits.append(f'{other_warnings} other row(s) need review')
            if validation_warning_count: bits.append(f'{validation_warning_count} page validation warning(s)')
            if ticket_reviews: bits.append(f'{ticket_reviews} trouble ticket(s) need review')
            self.status.set(f"Found {len(self.records)} master update row(s) and {len(self.trouble_tickets)} trouble ticket(s) from {group_no} work order(s); ignored {len(ignored_pages)} PDF page(s). " + '; '.join(bits) + '.')
        else:
            suffix=' All extracted items are ready.'
            self.status.set(f'Found {len(self.records)} master update row(s) and {len(self.trouble_tickets)} trouble ticket(s) from {group_no} work order(s); ignored {len(ignored_pages)} PDF page(s).'+suffix)
    def _total_check_records(self,check):
        return [(i,r) for i,r in enumerate(self.records)
                if str(r.get('wo',''))==str(check.get('wo','')) and r.get('kind')==check.get('kind')]
    def refresh_total_check(self,check,redraw=True):
        indexed=self._total_check_records(check); rows=[r for _,r in indexed]
        expected=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')
        result=_length_total_result(rows,expected)
        check.update(result)
        trusted=bool(check.get('manual_verified') or check.get('pdf_total_confident'))
        check['passed']=bool(result['matches'] and trusted)
        for _,record in indexed:
            record['warnings']=[w for w in record.get('warnings',[]) if not str(w).startswith('TOTAL LENGTH')]
        if not check['passed']:
            if expected is None:
                warning='TOTAL LENGTH NEEDS VERIFICATION — PRINTED PDF TOTAL COULD NOT BE READ'
            elif result['missing']:
                warning=(f"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, "
                         f"SUMMARY {result['summary_total']:g}; {result['missing']} LENGTH(S) MISSING")
            elif not trusted:
                warning=(f"TOTAL LENGTH NEEDS VERIFICATION — PDF TOTAL {expected:g}, "
                         f"SUMMARY {result['summary_total']:g}")
            else:
                warning=(f"TOTAL LENGTH MISMATCH — {'VERIFIED' if check.get('manual_verified') else 'PDF'} TOTAL {expected:g}, "
                         f"SUMMARY {result['summary_total']:g}, DIFF {abs(result['difference']):g} FT")
            check['warning']=warning
            for _,record in indexed:
                if warning not in record.setdefault('warnings',[]): record['warnings'].append(warning)
        else:
            check['warning']=''
        if redraw:
            for index,_ in indexed: self.show_summary_record(index)
        return check['passed']
    def prompt_total_check(self,check):
        self.refresh_total_check(check)
        if check.get('passed'): return True
        expected=check.get('verified_total') if check.get('manual_verified') else check.get('pdf_total')
        page_text=', '.join(str(p) for p in check.get('pages',[])) or 'unknown'
        initial='' if expected is None else f'{float(expected):g}'
        while True:
            raw=simpledialog.askstring(
                'Verify Total Length',
                f"Work Order {check.get('wo','')} — {check.get('kind','')}\n\n"
                f"PDF page(s): {page_text}\n"
                f"PDF total read: {initial or 'UNREADABLE'}\n"
                f"Summary length total: {check.get('summary_total',0):g}\n"
                + (f"Difference: {abs(check.get('difference') or 0):g} ft\n" if expected is not None else '') +
                f"Missing summary lengths: {check.get('missing',0)}\n\n"
                'Enter the TOTAL LENGTH you verify by looking at the PDF.\n'
                'Changing this value corrects only the OCR of the printed total; it does not change any row length.\n\n'
                'The master update remains blocked until the verified total and the summary lengths match exactly.',
                initialvalue=initial,parent=self)
            if raw is None: return False
            try:
                verified=float(str(raw).replace(',','').strip())
                if verified<=0: raise ValueError
            except Exception:
                messagebox.showerror('Invalid total','Enter a positive numeric total length.',parent=self)
                continue
            check['verified_total']=verified; check['manual_verified']=True
            passed=self.refresh_total_check(check)
            if passed:
                messagebox.showinfo('Total Length Verified',
                    f"Work Order {check.get('wo','')} {check.get('kind','')} now reconciles exactly at {verified:g} ft.",parent=self)
            else:
                messagebox.showwarning('Total Still Does Not Match',
                    f"The verified PDF total is {verified:g} ft, but the summary currently totals {check.get('summary_total',0):g} ft.\n\n"
                    'The affected summary rows remain dark red and Update Master is blocked until the row lengths are corrected.',parent=self)
            return passed
    def verify_length_totals(self,total_sources):
        self.total_validations=[]
        for (wo,kind),sources in total_sources.items():
            resolved=_resolve_printed_total_sources(sources)
            if not resolved.get('available'): continue
            check={'wo':wo,'kind':kind,'sources':sources,'pages':resolved.get('pages',[]),
                   'pdf_total':resolved.get('value'),'pdf_total_confident':resolved.get('confident',False),
                   'pdf_total_mode':resolved.get('mode',''),'verified_total':None,'manual_verified':False}
            self.total_validations.append(check)
            self.refresh_total_check(check)
            if not check.get('passed'): self.prompt_total_check(check)
    def revalidate_total_checks_for_record(self,record):
        for check in self.total_validations:
            if str(record.get('wo',''))==str(check.get('wo','')) and record.get('kind')==check.get('kind'):
                self.refresh_total_check(check)
    def unresolved_total_checks(self):
        for check in self.total_validations: self.refresh_total_check(check,redraw=False)
        return [check for check in self.total_validations if not check.get('passed')]

    def edit_selected(self):
        sel=self.tree.selection()
        if not sel: messagebox.showinfo('Edit','Select a row first.'); return
        iid=sel[0]
        if iid.startswith('ticket:'):
            self.edit_trouble_ticket(int(iid.split(':',1)[1]))
            return
        i=int(iid.split(':',1)[1]); r=self.records[i]
        win=tk.Toplevel(self); apply_app_icon(win); win.title('Edit extracted row'); win.transient(self); win.grab_set()
        fields=['Activity Value','Date','W/O','Truck','Operator']; vars={}
        values=[('' if r['video_length'] is None else str(r['video_length'])),fmt_date(r['date']),r['wo'],r['truck'],r['operator']]
        for n,(lab,val) in enumerate(zip(fields,values)):
            ttk.Label(win,text=lab+':').grid(row=n,column=0,padx=8,pady=6,sticky='e'); v=tk.StringVar(value=val); vars[lab]=v; ttk.Entry(win,textvariable=v,width=30).grid(row=n,column=1,padx=8,pady=6)
        def save():
            try:
                r['video_length']=None if r['kind']=='Manhole' or not vars['Activity Value'].get().strip() else float(vars['Activity Value'].get())
                r['date']=datetime.strptime(vars['Date'].get().strip(),'%m/%d/%Y'); r['wo']=vars['W/O'].get().strip(); r['truck']=vars['Truck'].get().strip(); r['operator']=vars['Operator'].get().strip()
            except Exception as e: messagebox.showerror('Invalid value',str(e),parent=win); return
            refresh_length_status(r)
            self.revalidate_total_checks_for_record(r)
            self.show_summary_record(i)
            length_warnings=sum(1 for rec in self.records if str(rec.get('status','')).startswith('LENGTH DIFF'))
            total_failures=sum(1 for check in self.total_validations if not check.get('passed'))
            other_warnings=sum(1 for rec in self.records if record_needs_review(rec) and not str(rec.get('status','')).startswith('LENGTH DIFF') and not any(str(w).startswith('TOTAL LENGTH') for w in rec.get('warnings',[])))
            if length_warnings or total_failures or other_warnings:
                bits=[]
                if total_failures: bits.append(f'{total_failures} TOTAL LENGTH VALIDATION FAILURE(S) — UPDATE MASTER BLOCKED')
                if length_warnings: bits.append(f'{length_warnings} length difference warning(s) > {LENGTH_DIFF_THRESHOLD:.1f}')
                if other_warnings: bits.append(f'{other_warnings} other row(s) need review')
                self.status.set('; '.join(bits) + '.')
            else:
                self.status.set(f'All rows matched; no length differences greater than {LENGTH_DIFF_THRESHOLD:.1f}.')
            win.destroy()
        ttk.Button(win,text='Save',command=save,style='Primary.TButton').grid(row=len(fields),column=0,columnspan=2,pady=10)
    def edit_trouble_ticket(self,index):
        ticket=self.trouble_tickets[index]
        win=tk.Toplevel(self); apply_app_icon(win); win.title('Edit trouble ticket'); win.transient(self); win.grab_set()
        fields=[
            ('Pipe/MH ID',ticket.get('pipe_id','')),('Description',ticket.get('description','')),
            ('Status',ticket.get('tracker_status','Open')),('Resolution / Follow-up Notes',ticket.get('resolution_notes','')),
            ('Date',fmt_date(ticket.get('date'))),('Work Order',ticket.get('wo','')),
            ('Truck',ticket.get('truck','')),('Operator',ticket.get('operator','')),
            ('Panel',ticket.get('panel','')),('Street',ticket.get('street_name','')),
            ('Area / Major Intersection',ticket.get('area','')),
            ('Service Type',ticket.get('service_type','')),('Upstream Manhole',ticket.get('upstream','')),
            ('Downstream Manhole',ticket.get('downstream','')),('Map Length','' if ticket.get('map_length') is None else str(ticket['map_length'])),
            ('Pipe Size',ticket.get('pipe_size','')),
        ]
        vars={}
        for n,(label,value) in enumerate(fields):
            block=n%2; row=n//2; col=block*2
            ttk.Label(win,text=label+':').grid(row=row,column=col,padx=(10,5),pady=6,sticky='e')
            var=tk.StringVar(value=value); vars[label]=var
            if label=='Status':
                ttk.Combobox(win,textvariable=var,width=31,state='readonly',
                             values=('Open','In Progress','Resolved','No Action Needed')).grid(row=row,column=col+1,padx=(0,12),pady=6,sticky='ew')
            else:
                ttk.Entry(win,textvariable=var,width=34).grid(row=row,column=col+1,padx=(0,12),pady=6,sticky='ew')
        win.columnconfigure(1,weight=1); win.columnconfigure(3,weight=1)
        def save():
            try:
                raw_date=vars['Date'].get().strip()
                date=datetime.strptime(raw_date,'%m/%d/%Y') if raw_date else None
                raw_length=vars['Map Length'].get().strip()
                map_length=float(raw_length) if raw_length else None
            except Exception:
                messagebox.showerror('Invalid value','Use MM/DD/YYYY for Date and a number for Map Length.',parent=win); return
            ticket.update({
                'date':date,'pipe_id':canonical_asset_id(vars['Pipe/MH ID'].get()),'street_name':vars['Street'].get().strip(),
                'panel':vars['Panel'].get().strip(),'area':vars['Area / Major Intersection'].get().strip(),
                'service_type':vars['Service Type'].get().strip(),
                'upstream':canonical_asset_id(vars['Upstream Manhole'].get()),
                'downstream':canonical_asset_id(vars['Downstream Manhole'].get()),
                'map_length':map_length,'pipe_size':vars['Pipe Size'].get().strip(),
                'description':vars['Description'].get().strip(),'wo':vars['Work Order'].get().strip(),
                'truck':vars['Truck'].get().strip(),'operator':vars['Operator'].get().strip(),
                'reported_by':vars['Operator'].get().strip(),
                'tracker_status':vars['Status'].get().strip() or 'Open',
                'resolution_notes':vars['Resolution / Follow-up Notes'].get().strip(),
            })
            ticket['ticket_key']=trouble_ticket_key(ticket); ticket['review_status']=trouble_ticket_status(ticket)
            self.show_summary_ticket(index); win.destroy()
        ttk.Button(win,text='Save',command=save,style='Primary.TButton').grid(row=(len(fields)+1)//2,column=0,columnspan=4,pady=12)
    def update_master(self):
        if not self.records and not self.trouble_tickets: messagebox.showwarning('Nothing to update','Analyze a PDF first.'); return
        unresolved=self.unresolved_total_checks()
        if unresolved:
            for check in list(unresolved): self.prompt_total_check(check)
            unresolved=self.unresolved_total_checks()
            if unresolved:
                details='\n'.join(f"W/O {c.get('wo','')} {c.get('kind','')}: {c.get('warning','TOTAL LENGTH NOT VERIFIED')}" for c in unresolved)
                messagebox.showerror('Total Length Validation Failed',
                    'Update Master is blocked because the PDF total length does not reconcile with the lengths in the summary.\n\n'+details+
                    '\n\nCorrect the affected row length(s), or verify the printed PDF total when prompted, then try Update Master again.')
                return
        bad=[r for r in self.records if not r.get('new_asset_approved') and (r['status']=='NOT MATCHED' or r.get('skip_update'))]
        if bad and not messagebox.askyesno('Unmatched rows',f'{len(bad)} rows are not matched and will be skipped. Continue with matched rows?'): return
        protected=[r for r in self.records if not r.get('skip_update') and any(x in r.get('warnings',[]) for x in ('EXISTING DATA','W/O ALREADY ENTERED','PDF PREVIOUSLY PROCESSED'))]
        if protected and not messagebox.askyesno('Replace existing data?',
            f'{len(protected)} row(s) already contain target data or appear previously processed.\n\nReplace only the applicable activity fields for those rows?'):
            return
        master_count=len(self.records)-len(bad)
        approved_new=sum(1 for r in self.records if r.get('new_asset_approved'))
        prompt=f'Write {master_count} row(s) to the master spreadsheet'
        if approved_new: prompt+=f', including {approved_new} approved new asset(s)'
        if self.trouble_tickets: prompt+=f' and process {len(self.trouble_tickets)} trouble ticket(s) into Trouble Tickets.xlsx'
        if not messagebox.askyesno('Update spreadsheets',prompt+'?'): return
        src=os.path.abspath(self.master_path.get())
        trouble_path=trouble_ticket_workbook_path(src)
        lock_reason=master_workbook_lock_reason(src)
        if lock_reason:
            messagebox.showwarning('Master Spreadsheet Is Open',
                f'{lock_reason}\n\nPlease close the master spreadsheet in Excel (or any other program using it), then click Update Master again.\n\nNo changes have been made and no backup was created.')
            self.status.set('Update blocked: master spreadsheet is open or locked. Close it and try again.')
            return
        if self.trouble_tickets and os.path.exists(trouble_path):
            ticket_lock=master_workbook_lock_reason(trouble_path)
            if ticket_lock:
                messagebox.showwarning('Trouble Tickets Spreadsheet Is Open',
                    f'{ticket_lock}\n\nClose Trouble Tickets.xlsx, then click Update Master again. No changes have been made.')
                self.status.set('Update blocked: Trouble Tickets.xlsx is open or locked.')
                return
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); base,ext=os.path.splitext(src)
        backup_folder=os.path.join(os.path.dirname(src),'Backups'); os.makedirs(backup_folder,exist_ok=True)
        backup=os.path.join(backup_folder,f'{os.path.splitext(os.path.basename(src))[0]}_BACKUP_{stamp}{ext}'); shutil.copy2(src,backup)
        trouble_backup=''
        if self.trouble_tickets and os.path.exists(trouble_path):
            trouble_backup=os.path.join(backup_folder,f'Trouble Tickets_BACKUP_{stamp}.xlsx')
            shutil.copy2(trouble_path,trouble_backup)
        excel=win32com.client.DispatchEx('Excel.Application'); excel.Visible=False; excel.DisplayAlerts=False; wb=None; twb=None
        try:
            wb=excel.Workbooks.Open(src)
            profile=getattr(self,'master_index',{}).get('profile','reno')
            if profile in ('year15', 'phase2_year1'):
                cached_index=getattr(self,'master_index')
                ps=wb.Worksheets(cached_index['pipe_sheet']); pr=2; ph=cached_index['pipe_headers']
                ms=wb.Worksheets(cached_index['manhole_sheet']); mr=2; mh=cached_index['manhole_headers']
            else:
                ps=wb.Worksheets('Pipes'); pr,ph=locate_headers(ps,['pipe_id','upstream','downstream','video length','date','w/o','truck','operator','notes'])
                ms=wb.Worksheets('Manholes'); mr,mh=locate_headers(ms,['st_id','date','w/o','truck','operator'])
            # Analysis already resolved every asset to a master row. Reuse that
            # in-memory index instead of scanning thousands of Excel cells again.
            cached=getattr(self,'master_index',{})
            pipe_rows={key:item['row'] for key,item in cached.get('pipes',{}).items()}
            pipe_id_rows={key:item['row'] for key,item in cached.get('pipe_by_id',{}).items()}
            mh_rows={key:item['row'] for key,item in cached.get('manholes',{}).items()}
            written=0
            log_rows=[]
            for r in self.records:
                if r['status']=='NOT MATCHED' or r.get('skip_update'): continue
                if r['kind'] in ('Pipe','Cleaning'):
                    rr=pipe_id_rows.get(asset_key(r.get('asset',''))) or pipe_rows.get((asset_key(r.get('up','')),asset_key(r.get('down',''))))
                    if not rr: continue
                    if r['kind']=='Cleaning':
                        ps.Cells(rr,ph['clean wheel walk']).Value=r['video_length']; write_excel_date(ps.Cells(rr,ph['clean date']),r['date']); ps.Cells(rr,ph['clean w/o']).Value=master_text(r['wo']); ps.Cells(rr,ph['clean truck']).Value=master_text(r['truck']); ps.Cells(rr,ph['clean operator']).Value=master_text(r['operator'])
                    elif profile in ('year15', 'phase2_year1'):
                        ps.Cells(rr,ph['video length']).Value=r['video_length']; write_excel_date(ps.Cells(rr,ph['video date']),r['date']); ps.Cells(rr,ph['video w/o']).Value=master_text(r['wo']); ps.Cells(rr,ph['video truck']).Value=master_text(r['truck']); ps.Cells(rr,ph['video operator']).Value=master_text(r['operator'])
                    else:
                        ps.Cells(rr,ph['video length']).Value=r['video_length']; write_excel_date(ps.Cells(rr,ph['date']), r['date']); ps.Cells(rr,ph['w/o']).Value=master_text(r['wo']); ps.Cells(rr,ph['truck']).Value=master_text(r['truck']); ps.Cells(rr,ph['operator']).Value=master_text(r['operator'])
                    # Carry configured length warnings into NOTES when the project
                    # provides that column, and highlight the measured value itself.
                    diff=r.get('length_diff')
                    if diff is not None and float(diff) > LENGTH_DIFF_THRESHOLD:
                        if r['kind']=='Cleaning':
                            warning=f'WHEEL WALK DIFFERS FROM LENGTH BY {float(diff):.1f} FT'
                            warning_cell=ps.Cells(rr,ph['clean wheel walk'])
                        else:
                            warning=f'VIDEO LENGTH DIFFERS FROM LENGTH BY {float(diff):.1f} FT'
                            warning_cell=ps.Cells(rr,ph['video length'])
                        notes_col=ph.get('notes')
                        if notes_col: append_note(ps.Cells(rr,notes_col),warning)
                        # Excel Interior.Color uses the VBA RGB integer; 255 is red.
                        warning_cell.Interior.Pattern = 1
                        warning_cell.Interior.Color = 255
                    written+=1; log_rows.append(r)
                else:
                    rr=mh_rows.get(r.get('asset_key') or asset_key(r.get('asset','')))
                    if not rr: continue
                    write_excel_date(ms.Cells(rr,mh['date']), r['date']); ms.Cells(rr,mh['w/o']).Value=master_text(r['wo']); ms.Cells(rr,mh['truck']).Value=master_text(r['truck']); ms.Cells(rr,mh['operator']).Value=master_text(r['operator']); written+=1; log_rows.append(r)

            # Existing rows are updated first because inserting new rows changes
            # later Excel row numbers. Approved insertions then run bottom-up on
            # each sheet, preserving every cached base-row location safely.
            approved_pipe_rows=sorted(
                (r for r in self.records if r.get('new_asset_approved') and r.get('kind') in ('Pipe','Cleaning')),
                key=lambda r:int(r.get('new_asset_base_row') or 0),reverse=True)
            for r in approved_pipe_rows:
                base_row=int(r.get('new_asset_base_row') or 0)
                if not base_row: continue
                rr,last_col=copy_master_row_below(ps,base_row)
                if profile in ('year15','phase2_year1'):
                    clear_master_columns(ps,rr,[
                        ph.get('clean wheel walk'),ph.get('clean date'),ph.get('clean w/o'),
                        ph.get('clean truck'),ph.get('clean operator'),ph.get('video length'),
                        ph.get('video date'),ph.get('video w/o'),ph.get('video truck'),
                        ph.get('video operator'),ph.get('notes')])
                    ps.Cells(rr,ph['upstream']).Value=master_text(r.get('up'))
                    ps.Cells(rr,ph['downstream']).Value=master_text(r.get('down'))
                    ps.Cells(rr,ph['pipe_id']).Value=f"{master_text(r.get('up'))}-{master_text(r.get('down'))}"
                    if r['kind']=='Cleaning':
                        ps.Cells(rr,ph['clean wheel walk']).Value=r['video_length']
                        write_excel_date(ps.Cells(rr,ph['clean date']),r['date'])
                        ps.Cells(rr,ph['clean w/o']).Value=master_text(r['wo'])
                        ps.Cells(rr,ph['clean truck']).Value=master_text(r['truck'])
                        ps.Cells(rr,ph['clean operator']).Value=master_text(r['operator'])
                    else:
                        ps.Cells(rr,ph['video length']).Value=r['video_length']
                        write_excel_date(ps.Cells(rr,ph['video date']),r['date'])
                        ps.Cells(rr,ph['video w/o']).Value=master_text(r['wo'])
                        ps.Cells(rr,ph['video truck']).Value=master_text(r['truck'])
                        ps.Cells(rr,ph['video operator']).Value=master_text(r['operator'])
                else:
                    clear_master_columns(ps,rr,[ph.get('video length'),ph.get('date'),ph.get('w/o'),
                                                ph.get('truck'),ph.get('operator'),ph.get('notes')])
                    ps.Cells(rr,ph['pipe_id']).Value=master_text(r.get('asset'))
                    ps.Cells(rr,ph['video length']).Value=r['video_length']
                    write_excel_date(ps.Cells(rr,ph['date']),r['date'])
                    ps.Cells(rr,ph['w/o']).Value=master_text(r['wo'])
                    ps.Cells(rr,ph['truck']).Value=master_text(r['truck'])
                    ps.Cells(rr,ph['operator']).Value=master_text(r['operator'])
                highlight_approved_master_row(ps,rr,last_col)
                written+=1; log_rows.append(r)

            approved_manhole_rows=sorted(
                (r for r in self.records if r.get('new_asset_approved') and r.get('kind')=='Manhole'),
                key=lambda r:int(r.get('new_asset_base_row') or 0),reverse=True)
            for r in approved_manhole_rows:
                base_row=int(r.get('new_asset_base_row') or 0)
                if not base_row: continue
                rr,last_col=copy_master_row_below(ms,base_row)
                clear_master_columns(ms,rr,[mh.get('date'),mh.get('w/o'),mh.get('truck'),mh.get('operator'),mh.get('notes')])
                ms.Cells(rr,mh['st_id']).Value=master_text(r.get('asset'))
                write_excel_date(ms.Cells(rr,mh['date']),r['date'])
                ms.Cells(rr,mh['w/o']).Value=master_text(r['wo'])
                ms.Cells(rr,mh['truck']).Value=master_text(r['truck'])
                ms.Cells(rr,mh['operator']).Value=master_text(r['operator'])
                highlight_approved_master_row(ms,rr,last_col)
                written+=1; log_rows.append(r)

            ticket_added=[]; ticket_skipped=0; ticket_existed=False
            if self.trouble_tickets:
                twb,ticket_added,ticket_skipped,ticket_existed=prepare_trouble_ticket_workbook(excel,trouble_path,self.trouble_tickets)
            # Both workbooks are fully staged before either save begins.
            wb.Save()
            if twb:
                if ticket_existed: twb.Save()
                else: twb.SaveAs(trouble_path,FileFormat=51)
                twb.Close(True); twb=None
            wb.Close(True); wb=None
            remember_confirmed_entries(self.groups)
            log_folder,registry_path=processed_registry(src); os.makedirs(log_folder,exist_ok=True)
            log_path=os.path.join(log_folder,f'update_{stamp}.csv')
            with open(log_path,'w',newline='',encoding='utf-8-sig') as f:
                out=csv.writer(f); out.writerow(['Timestamp','PDF','Type','Asset','PDF Page','Date','Video Length / Wheel Walk','W/O','Truck','Operator','Review Status'])
                for r in log_rows: out.writerow([datetime.now().isoformat(timespec='seconds'),os.path.basename(self.pdf_path.get()),r['kind'],r.get('display_asset') or r.get('asset',''),r.get('source_page',''),fmt_date(r.get('date')),r.get('video_length',''),r.get('wo',''),r.get('truck',''),r.get('operator',''),review_status(r)])
            try: registry=json.load(open(registry_path,encoding='utf-8'))
            except Exception: registry={}
            if self.pdf_hash: registry[self.pdf_hash]={'pdf':os.path.basename(self.pdf_path.get()),'updated':datetime.now().isoformat(timespec='seconds'),'rows':written,'trouble_tickets_added':len(ticket_added)}
            with open(registry_path,'w',encoding='utf-8') as f: json.dump(registry,f,indent=2)
            ticket_note=''
            if self.trouble_tickets:
                ticket_note=f'\n\nTrouble tickets added: {len(ticket_added)}\nDuplicates skipped: {ticket_skipped}\n{trouble_path}'
            messagebox.showinfo('Finished',f'Updated {written} master row(s).{ticket_note}\n\nMaster backup created:\n{backup}\n\nUpdate log:\n{log_path}')
            self.status.set(f'Finished. Updated {written} master row(s) and added {len(ticket_added)} trouble ticket(s); {ticket_skipped} duplicate(s) skipped.')
        except Exception as e:
            messagebox.showerror('Update failed',f'{e}\n\nYour master backup is here:\n{backup}')
        finally:
            if twb:
                try: twb.Close(False)
                except: pass
            if wb:
                try: wb.Close(False)
                except: pass
            excel.Quit()

if __name__=='__main__':
    configure_windows_identity()
    App().mainloop()
