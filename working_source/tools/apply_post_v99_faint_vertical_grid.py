from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'app' / 'reno_scan_updater.py'
s = SOURCE.read_text(encoding='utf-8')

old = '''    # Clean scans should resolve from the raw binary image. This is both faster
    # and much less likely to mistake repeated text strokes for vertical rules.
    strong=collect_vertical_rules(cinv,.18,.80)
    if not (5<=len(strong)<=20):
        # Broken/faint grids still get the older gap-joining repair, but reject an
        # implausibly large rule set rather than feeding dozens of fake columns
        # into the expensive master-assisted OCR stage.
        joined=cv2.morphologyEx(
            cinv,cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(3,int(bh*.012)))))
        strong=collect_vertical_rules(joined,.12,.85)
    if not (5<=len(strong)<=20):
        return [],None,None
'''

new = '''    # Clean scans should resolve from the raw binary image. This is both faster
    # and much less likely to mistake repeated text strokes for vertical rules.
    strong=collect_vertical_rules(cinv,.18,.80)
    if not (5<=len(strong)<=20):
        # Broken/faint grids still get the older gap-joining repair, but reject an
        # implausibly large rule set rather than feeding dozens of fake columns
        # into the expensive master-assisted OCR stage.
        joined=cv2.morphologyEx(
            cinv,cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(3,int(bh*.012)))))
        strong=collect_vertical_rules(joined,.12,.85)
    if not (5<=len(strong)<=20):
        # Some image-only B&C scans preserve the horizontal table rules clearly
        # while the interior vertical rules are several shades lighter than the
        # normal 225 threshold.  Escalate only after both established dark-grid
        # passes fail.  The lighter pass still has to produce a plausible count
        # of long, near-full-height rules spanning most of the already-isolated
        # table region; later row-rule and header-role checks remain unchanged.
        faint_inv=cv2.threshold(cgray,240,255,cv2.THRESH_BINARY_INV)[1]
        faint_joined=cv2.morphologyEx(
            faint_inv,cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(3,int(bh*.012)))))
        faint_strong=collect_vertical_rules(faint_joined,.12,.80)
        if 5<=len(faint_strong)<=20:
            max_span=max(y2-y1 for _,y1,y2 in faint_strong)
            x_span=faint_strong[-1][0]-faint_strong[0][0]
            if max_span>=bh*.75 and x_span>=bw*.70:
                strong=faint_strong
    if not (5<=len(strong)<=20):
        return [],None,None
'''

if old not in s:
    if 'faint_inv=cv2.threshold(cgray,240,255,cv2.THRESH_BINARY_INV)[1]' in s:
        print('post-v99 faint vertical-grid recovery already applied.')
        raise SystemExit(0)
    raise SystemExit('Target compact vertical-grid block not found; refusing broad edit.')

s = s.replace(old, new, 1)
SOURCE.write_text(s, encoding='utf-8')
print('Applied post-v99 faint vertical-grid recovery.')
