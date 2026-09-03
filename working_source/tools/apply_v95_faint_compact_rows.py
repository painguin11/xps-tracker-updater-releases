from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'app' / 'reno_scan_updater.py'
s = SOURCE.read_text(encoding='utf-8')

old = '''    horizontal_inv=cv2.threshold(gray,240,255,cv2.THRESH_BINARY_INV)[1]
    roi=horizontal_inv[by:by+bh,max(0,left):min(w,right)]
    hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(35,int((right-left)*.20)),1))
    horizontal=cv2.morphologyEx(roi,cv2.MORPH_OPEN,hk)
    contours,_=cv2.findContours(horizontal,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    ys=[by,by+bh-1]
    for contour in contours:
        x,y,ww,hh=cv2.boundingRect(contour)
        if ww>=(right-left)*.45 and hh<=max(14,h*.018):
            ys.append(by+y+hh//2)
'''

new = '''    horizontal_inv=cv2.threshold(gray,240,255,cv2.THRESH_BINARY_INV)[1]
    roi=horizontal_inv[by:by+bh,max(0,left):min(w,right)]
    hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(35,int((right-left)*.20)),1))

    def compact_horizontal_rule_ys(source):
        horizontal=cv2.morphologyEx(source,cv2.MORPH_OPEN,hk)
        contours,_=cv2.findContours(horizontal,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        found=[]
        for contour in contours:
            x,y,ww,hh=cv2.boundingRect(contour)
            if ww>=(right-left)*.45 and hh<=max(14,h*.018):
                found.append(by+y+hh//2)
        return found

    rule_ys=compact_horizontal_rule_ys(roi)
    if len(rule_ys)<4:
        # Some compact B&C scans have real row rules printed as faint/dashed
        # segments.  Keep the normal raw-line pass authoritative; only when it
        # finds almost no table rows, join tiny horizontal gaps and retry the
        # same long-rule test.  This repairs the physical grid without inferring
        # rows from OCR text or from the master workbook.
        join_width=max(3,int(round((right-left)*.003)))
        repaired=cv2.morphologyEx(
            roi,cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT,(join_width,1)))
        repaired_ys=compact_horizontal_rule_ys(repaired)
        if len(repaired_ys)>len(rule_ys):
            rule_ys=repaired_ys

    ys=[by,by+bh-1]+rule_ys
'''

if old not in s:
    if 'def compact_horizontal_rule_ys(source):' in s:
        print('v95 faint compact-row repair already applied.')
        raise SystemExit(0)
    raise SystemExit('Target compact horizontal-rule block not found; refusing broad edit.')

s = s.replace(old, new, 1)
SOURCE.write_text(s, encoding='utf-8')
print('Applied v95 faint compact-row repair.')
