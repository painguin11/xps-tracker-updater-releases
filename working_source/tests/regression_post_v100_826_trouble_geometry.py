"""Permanent synthetic regression for skewed B&C Trouble Ticket ruled cells.

The 8-26 private packet exposed scan perspective where a value-cell contour can
start a few pixels above the bottom of its label cell. This synthetic form keeps
customer data out of Git while reproducing that geometry.
"""
import ast
import hashlib
import re
from pathlib import Path

import cv2
import numpy as np
import pymupdf
import pytesseract

SOURCE=Path(__file__).resolve().parents[1]/'app'/'reno_scan_updater.py'
tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
names={'_clean_ticket_text','_ticket_asset_id','_ticket_cell_image',
       '_ticket_detect_cells','_ticket_detected_values'}
ns=dict(cv2=cv2,np=np,re=re)
cache={}
def ocr(img,config=''):
    key=(hashlib.sha256(img.tobytes()).digest(),img.shape,config)
    if key not in cache: cache[key]=pytesseract.image_to_string(img,config=config)
    return cache[key]
ns['cached_ocr_string']=ocr
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],
                        type_ignores=[]),str(SOURCE),'exec'),ns)


def make_form():
    left,top,width=38,165,530
    doc=pymupdf.open(); page=doc.new_page(width=612,height=792)
    def row(y,labels,values,widths):
        x=left
        for label,value,fraction in zip(labels,values,widths):
            cell_width=width*fraction
            page.draw_rect(pymupdf.Rect(x,y,x+cell_width,y+16),width=.8)
            page.draw_rect(pymupdf.Rect(x,y+16,x+cell_width,y+40),width=.8)
            page.insert_text((x+5,y+11),label,fontsize=8,fontname='hebo')
            if value: page.insert_text((x+9,y+31),value,fontsize=9,fontname='hebo')
            x+=cell_width
    row(top,['Reported by:','Pipe ID #','Date:'],['TEST A','ZX-1234A','1/2/2026'],[.37,.37,.26])
    row(top+65,['Street Name','Panel'],['TEST ROAD','MAP 42'],[.74,.26])
    row(top+140,['Area/Major Intersection','Vac Truck','Pipe Survey','MH Survey'],
        ['TEST INTERSECTION','','','X'],[.62,.12,.13,.13])
    row(top+215,['Upstream Manhole','Downstream Manhole','Map Length','Pipe Size'],
        ['','','',''],[.37,.37,.13,.13])
    y=top+255
    page.draw_rect(pymupdf.Rect(left,y,left+width,y+145),width=.8)
    # Reproduce harmless leading OCR debris before the printed description label.
    page.insert_text((left+2,y+23),'. .',fontsize=7,fontname='hebo')
    page.insert_text((left+25,y+23),'Description :',fontsize=10,fontname='hebo')
    page.insert_text((left+130,y+23),'FIELD GEOMETRY SURVIVES.',fontsize=9,fontname='hebo')
    for offset in (30,55,80,105,125):
        page.draw_line((left,y+offset),(left+width,y+offset),width=.8)
    return doc


def render(page,scale=2.5):
    pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3].copy()


def main():
    doc=make_form(); image=render(doc[0]); h,w=image.shape[:2]
    # Vertical shear gives the same contour symptom as the private scan: some
    # adjacent value boxes begin slightly above the label box's lowest point.
    shear=.008
    matrix=np.float32([[1,0,0],[shear,1,-shear*w/2]])
    skewed=cv2.warpAffine(image,matrix,(w,h),borderValue=(255,255,255))
    layout=ns['_ticket_detect_cells'](skewed)
    assert layout is not None,'skewed ruled form must keep detected-cell layout'
    values,uncertain=ns['_ticket_detected_values'](skewed,layout)
    expected={
        'pipe_id':'ZX-1234A','date':'1/2/2026','street_name':'TEST ROAD',
        'panel':'MAP 42','area':'TEST INTERSECTION','service_type':'MH Survey',
        'description':'FIELD GEOMETRY SURVIVES.',
    }
    for key,value in expected.items():
        assert values[key]==value,(key,values[key],value)
    assert values['upstream']=='' and values['downstream']==''
    assert values['map_length']=='' and values['pipe_size']==''
    assert not values['description'].startswith(('.',':','-')),values['description']
    assert values['description'].endswith('.'),values['description']
    # A plain blank image still cannot be accepted as a ticket layout.
    assert ns['_ticket_detect_cells'](np.full((1980,1530,3),255,np.uint8)) is None
    doc.close()
    print('PASS bounded skewed Trouble Ticket cell geometry and description cleanup')


if __name__=='__main__':
    main()
