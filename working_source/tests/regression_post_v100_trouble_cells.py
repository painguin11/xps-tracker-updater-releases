"""Public synthetic OCR regression; optional private PDF expectations stay local.

python working_source/tests/regression_post_v100_trouble_cells.py
python working_source/tests/regression_post_v100_trouble_cells.py --fixtures /private/expected.json

The optional JSON is a list of {pdf, pages: [{page, expected: {...}}]} objects.
It must never be committed: it may contain customer field values.
"""
import argparse
import ast
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
names={'render_page','digits','asset_key','canonical_asset_id','parse_float','parse_date_text','fmt_date',
       '_ticket_crop','_clean_ticket_text','_ticket_field_text','_ticket_service_types',
       '_ticket_asset_id','_ticket_cell_image','_ticket_detect_cells','_ticket_detected_values',
       'legacy_trouble_ticket_key','trouble_ticket_key','trouble_ticket_asset_key',
       'trouble_ticket_status','parse_trouble_ticket'}
ns=dict(cv2=cv2,np=np,pymupdf=pymupdf,Image=Image,re=re,os=os,
        hashlib=hashlib,datetime=datetime,_PAGE_CACHE_FOLDER='')
cache={}
def ocr(img,config=''):
    key=(hashlib.sha256(img.tobytes()).digest(),img.shape,config)
    if key not in cache: cache[key]=pytesseract.image_to_string(img,config=config)
    return cache[key]
ns['cached_ocr_string']=ocr
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],
                        type_ignores=[]),str(SOURCE),'exec'),ns)


def form(left=38,top=165,width=530,pipe_id='ZX-1234A-ZX-5678',blank=False):
    doc=pymupdf.open();page=doc.new_page(width=612,height=792)
    def row(y,labels,values,widths):
        x=left
        for label,value,fraction in zip(labels,values,widths):
            cell_width=width*fraction
            page.draw_rect(pymupdf.Rect(x,y,x+cell_width,y+16),width=.8)
            page.draw_rect(pymupdf.Rect(x,y+16,x+cell_width,y+40),width=.8)
            page.insert_text((x+5,y+11),label,fontsize=8,fontname='hebo')
            if value: page.insert_text((x+9,y+31),value,fontsize=9,fontname='hebo')
            x+=cell_width
    row(top,['Reported by:','Pipe ID #','Date:'],['TEST  A',pipe_id,'1/2/2026'],[.37,.37,.26])
    row(top+65,['Street Name','Panel'],['TEST ROAD','MAP 42'],[.74,.26])
    row(top+140,['Area/Major Intersection','Vac Truck','Pipe Survey','MH Survey'],
        ['TEST INTERSECTION','','' if blank else 'X','X' if blank else ''],[.62,.12,.13,.13])
    row(top+215,['Upstream Manhole','Downstream Manhole','Map Length','Pipe Size'],
        ['','','',''] if blank else ['ZX-1234A','ZX-5678','62','10'],[.37,.37,.13,.13])
    y=top+255
    page.draw_rect(pymupdf.Rect(left,y,left+width,y+145),width=.8)
    page.insert_text((left+6,y+23),'Description :',fontsize=10,fontname='hebo')
    page.insert_text((left+110,y+23),'FIRST LINE OF THE ISSUE',fontsize=9,fontname='hebo')
    page.insert_text((left+6,y+46),'LEFT EDGE CONTINUATION MUST SURVIVE',fontsize=9,fontname='hebo')
    for offset in (30,55,80,105,125):
        page.draw_line((left,y+offset),(left+width,y+offset),width=.8)
    return doc


def synthetic_checks():
    for left,top,width,identifier,blank in [(38,165,530,'ZX-1234A-ZX-5678',False),
                                           (64,185,490,'123456789',True)]:
        doc=form(left,top,width,identifier,blank)
        wo={'wo':'12345','truck':'TT01','operator':'FALLBACK B','date':datetime(2025,1,1)}
        ticket=ns['parse_trouble_ticket'](doc[0],1,wo)
        assert not ticket.get('_ticket_layout_unverified'),ticket['review_status']
        assert ticket['pipe_id']==identifier,ticket['pipe_id']
        assert ticket['date']==datetime(2026,1,2),ticket['date']
        assert ticket['operator']=='TEST A',ticket['operator']
        assert ticket['street_name']=='TEST ROAD',ticket['street_name']
        assert ticket['panel']=='MAP 42',ticket['panel']
        assert ticket['area']=='TEST INTERSECTION',ticket['area']
        assert ticket['wo']=='12345' and ticket['truck']=='TT01'
        assert ticket['service_type']==('MH Survey' if blank else 'Pipe Survey'),ticket['service_type']
        assert ticket['upstream']==('' if blank else 'ZX-1234A'),ticket['upstream']
        assert ticket['downstream']==('' if blank else 'ZX-5678'),ticket['downstream']
        assert ticket['map_length']==(None if blank else 62),ticket['map_length']
        assert ticket['pipe_size']==('' if blank else '10'),ticket['pipe_size']
        assert 'FIRST LINE OF THE ISSUE' in ticket['description'],ticket['description']
        assert 'LEFT EDGE CONTINUATION MUST SURVIVE' in ticket['description'],ticket['description']
        preview=ticket['_field_previews']['description']
        assert preview.shape[1]>width*2,preview.shape
        assert ticket['_field_preview_pages']['description']==[1]
        assert ticket['ticket_key']==ns['parse_trouble_ticket'](doc[0],1,wo)['ticket_key']
        doc.close()
    for identifier in ('ZX-1234A-ZX-5678','R2-280','123456789','ZX-5678B'):
        assert ns['_ticket_asset_id'](identifier)==identifier
    assert ns['_ticket_detect_cells'](np.full((1980,1530,3),255,np.uint8)) is None
    assert ns['_ticket_cell_image'](np.full((120,300,3),245,np.uint8),(0,0,300,120)) is None
    ready=dict(date=datetime(2026,1,2),pipe_id='ZX-1234A',operator='TEST A',description='TEST')
    assert ns['trouble_ticket_status'](ready).startswith('Ready')
    assert ns['trouble_ticket_status'](dict(ready,_ticket_layout_unverified=True)).startswith('Review')
    assert ns['trouble_ticket_status'](dict(ready,_ticket_uncertain={'pipe_id':'ZX-1234A'})).startswith('Review')
    # Exercise the real ticket editor Save callback without a GUI. A no-op edit
    # must preserve the full pair and page identity and acknowledge OCR review.
    app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and any(
        isinstance(m,ast.FunctionDef) and m.name=='edit_trouble_ticket' for m in n.body))
    editor=next(n for n in app.body if isinstance(n,ast.FunctionDef) and n.name=='edit_trouble_ticket')
    save=next(n for n in editor.body if isinstance(n,ast.FunctionDef) and n.name=='save')
    class Value:
        def __init__(self,value): self.value=value
        def get(self): return self.value
    labels=['Date','Pipe/MH ID','Street','Panel','Area / Major Intersection','Service Type',
            'Upstream Manhole','Downstream Manhole','Map Length','Pipe Size','Description',
            'Work Order','Truck','Operator','Status','Resolution / Follow-up Notes']
    values={label:Value('') for label in labels}
    for label,value in {'Date':'01/02/2026','Pipe/MH ID':'ZX-1234A-ZX-5678',
                        'Operator':'TEST A','Description':'TEST','Map Length':'62'}.items():
        values[label]=Value(value)
    ticket=dict(ready,source_page_hash='test-page',_ticket_uncertain={'operator':'TEST A'},
                _ticket_layout_unverified=True)
    key=ns['trouble_ticket_key'](ticket)
    ns.update(ticket=ticket,vars=values,index=0,
              self=type('App',(),{'show_summary_ticket':lambda self,index:None})(),
              win=type('Window',(),{'destroy':lambda self:None})())
    exec(compile(ast.Module(body=[save],type_ignores=[]),str(SOURCE),'exec'),ns)
    ns['save']()
    assert ticket['pipe_id']=='ZX-1234A-ZX-5678'
    assert ticket['ticket_key']==key
    assert not ticket.get('_ticket_uncertain') and not ticket.get('_ticket_layout_unverified')
    print('PASS synthetic ticket geometry, IDs, dates, wrapping, blanks, previews, and edit/save')


def private_checks(path):
    total=0
    for fixture in json.loads(Path(path).read_text()):
        with pymupdf.open(fixture['pdf']) as doc:
            for case in fixture['pages']:
                ticket=ns['parse_trouble_ticket'](doc[case['page']-1],case['page'])
                assert not ticket.get('_ticket_layout_unverified'),case['page']
                for key,expected in case['expected'].items():
                    actual=ns['fmt_date'](ticket[key]) if key=='date' else ticket[key]
                    assert actual==expected,(case['page'],key,actual,expected)
                total+=1
    print(f'PASS {total} private fixture tickets (customer data remains local)')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures');args=parser.parse_args()
    synthetic_checks()
    if args.fixtures: private_checks(args.fixtures)
    else: print('SKIP private PDFs: supply --fixtures for exact field comparisons')
