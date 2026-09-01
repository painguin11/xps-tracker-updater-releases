import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


PDF = Path('upload/08_10_2026 Reno Work Orders.pdf')


def ocr(image, psm=11, whitelist=None):
    with tempfile.NamedTemporaryFile(suffix='.png') as source:
        image.save(source.name)
        cmd = ['tesseract', source.name, 'stdout', '--psm', str(psm)]
        if whitelist:
            cmd += ['-c', f'tessedit_char_whitelist={whitelist}']
        return re.sub(r'\s+', ' ', subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)).strip()


def crop(image, box):
    width, height = image.size
    x1, y1, x2, y2 = box
    return image.crop((int(width*x1), int(height*y1), int(width*x2), int(height*y2)))


def best_digits(image):
    candidates=[]
    variants=ocr_variants(image)
    for variant in variants:
        for psm in (6, 7, 11, 13):
            text=ocr(variant,psm,'0123456789')
            if text: candidates.append((psm,text))
    psm11=[text for psm,text in candidates if psm==11 and len(re.sub(r'\D','',text))==9]
    text=psm11[0] if psm11 else max((text for _,text in candidates),key=lambda x:(sum(ch.isalnum() for ch in x),-len(x)))
    return re.sub(r'\D','',text)


def ocr_variants(image):
    image=image.convert('L')
    pixels=np.asarray(image)
    hist=np.bincount(pixels.ravel(),minlength=256)
    total=pixels.size; sum_total=np.dot(np.arange(256),hist); weight_bg=0; sum_bg=0; best=0; threshold=0
    for value,count in enumerate(hist):
        weight_bg+=count
        if not weight_bg: continue
        weight_fg=total-weight_bg
        if not weight_fg: break
        sum_bg+=value*count
        between=weight_bg*weight_fg*((sum_bg/weight_bg)-((sum_total-sum_bg)/weight_fg))**2
        if between>best: best=between; threshold=value
    return (image,Image.fromarray(np.where(pixels>threshold,255,0).astype('uint8')))


def best_text(image):
    candidates=[ocr(variant,11) for variant in ocr_variants(image)]
    candidates=[text for text in candidates if text]
    return candidates[0]


with tempfile.TemporaryDirectory() as folder:
    prefix=Path(folder)/'page'
    subprocess.check_call(['pdftoppm','-f','5','-l','7','-r','180','-png',str(PDF),str(prefix)],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    pages=[Image.open(prefix.with_name(f'page-{n}.png')).convert('RGB') for n in (5,6,7)]
    expected=[
        ('150335003','EASEMENT','MAP 14','2ND ST / INTERSTATE 580'),
        ('150335025','EASEMENT','MAP 14',None),
        ('230124001','QUAIL FALLS DR','MAP 38','QUAIL FALLS DR / FINNSECH DR'),
    ]
    for page,(pipe,street,panel,area) in zip(pages,expected):
        assert 'TROUBLE TICKET' in ocr(crop(page,(0,.15,1,.28)),11).upper()
        actual_pipe=best_digits(crop(page,(.360,.242,.690,.268)))
        assert actual_pipe == pipe, (actual_pipe,pipe)
        actual_street=best_text(crop(page,(.085,.307,.690,.337))).strip('| -=')
        assert actual_street == street,(actual_street,street)
        assert panel in best_text(crop(page,(.690,.307,.915,.337))).upper()
        area_text=best_text(crop(page,(.085,.412,.590,.442))).strip('| -=')
        if area: assert area_text == area
        assert 'MANHOLE POSSIBLY BURIED' in best_text(crop(page,(.245,.582,.915,.800))).upper()
        scores=[]
        for box in ((.592,.412,.690,.442),(.692,.412,.802,.442),(.805,.412,.915,.442)):
            field=np.asarray(crop(page,box).convert('L'))
            h,w=field.shape
            field=field[int(h*.08):int(h*.70),int(w*.12):int(w*.88)]
            scores.append(float(np.mean(field<105)))
        assert scores[2]>.018 and scores[0]<=.018 and scores[1]<=.018, scores
print('Trouble-ticket fixture checks passed for pages 5-7.')
