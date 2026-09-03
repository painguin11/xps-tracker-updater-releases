from pathlib import Path
import re

APP=Path('working_source/app/reno_scan_updater.py')
V91=Path('working_source/tests/regression_v91_workorder_color_ocr.py')

src=APP.read_text(encoding='utf-8')
assert "APP_VERSION = '92'" in src, 'v93-work must start from released v92 source'

helper=r'''def _workorder_magenta_candidates\(cell_img\):\n.*?\n    return found\n'''
replacement='''def _workorder_magenta_candidates(cell_img):
    """Return exact 4/5-digit OCR observations from the isolated pink W/O ink."""
    found=[]
    for image in _workorder_magenta_variants(cell_img):
        for psm in (7,8,13,6):
            text=cached_ocr_string(
                image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789'
            ).strip()
            found.extend(re.findall(r'(?<!\\d)\\d{4,5}(?!\\d)',text))
    return found


def _workorder_magenta_structure_count(binary):
    """Count substantial horizontal digit-shaped ink clusters in an isolated W/O image.

    This is intentionally conservative. A barely visible number may still coax a
    plausible 4/5-digit string from OCR, but if the pink mask only contains two or
    three readable digit shapes we do not have enough visual evidence to prefill it.
    """
    if binary is None or getattr(binary,'size',0)==0 or getattr(binary,'ndim',0)!=2:
        return 0
    foreground=np.asarray(binary)<128
    h,w=foreground.shape
    if h<1 or w<1:
        return 0
    # A real digit contributes ink through a meaningful fraction of the image height.
    # Ignore isolated anti-aliasing/noise pixels before grouping occupied columns.
    min_column_ink=max(2,int(round(h*.03)))
    active=np.sum(foreground,axis=0)>=min_column_ink
    runs=[]; start=None
    for x,is_active in enumerate(active):
        if is_active and start is None:
            start=x
        elif not is_active and start is not None:
            runs.append((start,x-1)); start=None
    if start is not None:
        runs.append((start,w-1))
    min_width=max(3,int(round(h*.015)))
    return sum(1 for x1,x2 in runs if (x2-x1+1)>=min_width)


def _workorder_confident_magenta_candidate(cell_img):
    """Return (prefill, magenta_seen) and fail closed when pink W/O evidence is weak.

    Prefill requires OCR consensus plus the expected number of visible digit-shaped
    magenta clusters. ``magenta_seen`` remains True when pink ink is present but too
    weak to trust; callers use that to leave the popup blank instead of falling back
    to a grayscale guess.
    """
    variants=_workorder_magenta_variants(cell_img)
    if not variants:
        return '',False
    votes=[]; structure_counts=[]
    for image in variants:
        structure_counts.append(_workorder_magenta_structure_count(image))
        for psm in (7,8,13,6):
            text=cached_ocr_string(
                image,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789'
            ).strip()
            votes.extend(re.findall(r'(?<!\\d)\\d{4,5}(?!\\d)',text))
    if not votes:
        return '',True
    winner=max(set(votes),key=lambda x:(votes.count(x),len(x)))
    agreement=votes.count(winner)
    share=agreement/len(votes)
    structure_ok=any(count==len(winner) for count in structure_counts)
    if agreement<3 or share<0.67 or not structure_ok:
        return '',True
    return winner,True
'''
src,n=re.subn(helper,replacement,src,count=1,flags=re.S)
assert n==1, 'magenta candidate helper block not found exactly once'

start=src.index('    # Work order number: isolate the machine-typed pink/magenta ink first.')
end=src.index('    date_txt = _best_ocr_text',start)
new_block='''    # Work order number: isolate the machine-typed pink/magenta ink first.
    # Prefill only when the isolated color read has strong OCR consensus AND the
    # mask contains the expected 4 or 5 visible digit shapes. If pink ink exists
    # but is too faded/incomplete to meet that bar, deliberately leave W/O blank.
    wo_crop=candidate_wo_crops[0]
    color_results=[]; magenta_seen=False
    for candidate_crop in candidate_wo_crops:
        value,seen=_workorder_confident_magenta_candidate(candidate_crop)
        magenta_seen=magenta_seen or seen
        if value:
            color_results.append((value,candidate_crop))
    if color_results:
        values=[value for value,_crop in color_results]
        wo=max(set(values),key=lambda x:(values.count(x),len(x)))
        wo_crop=next(candidate_crop for value,candidate_crop in color_results if value==wo)
    elif magenta_seen:
        wo=''
    else:
        # A fully desaturated/black-and-white scan can destroy the color signal.
        # In that case only a strong multi-pass grayscale consensus may prefill.
        crop_results=[]
        for candidate_crop in candidate_wo_crops:
            gray=cv2.cvtColor(candidate_crop,cv2.COLOR_RGB2GRAY)
            gray=cv2.resize(gray,None,fx=2.4,fy=2.4,interpolation=cv2.INTER_CUBIC)
            hits=[]
            for psm in (6,7,8,11,13):
                t=cached_ocr_string(gray,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789').strip()
                hits+=re.findall(r'(?<!\\d)\\d{4,5}(?!\\d)',t)
            if hits:
                winner=max(set(hits),key=lambda x:(hits.count(x),len(x)))
                agreement=hits.count(winner); share=agreement/len(hits)
                if agreement>=3 and share>=0.67:
                    crop_results.append((agreement,share,len(winner),winner,candidate_crop))
        if crop_results:
            agreement,share,digits_count,wo,wo_crop=max(crop_results,key=lambda x:(x[0],x[1],x[2]))
        else:
            wo=''

'''
src=src[:start]+new_block+src[end:]
src=src.replace('except the five printed W/O digits','except the 4 or 5 printed W/O digits')
APP.write_text(src,encoding='utf-8')

# Keep the historical v91 regression aligned with the newer confidence-gated
# implementation while preserving its original color-first requirement.
t=V91.read_text(encoding='utf-8')
t=t.replace("assert '_workorder_magenta_candidates(candidate_crop)' in s", "assert '_workorder_confident_magenta_candidate(candidate_crop)' in s")
t=t.replace("assert block.index('_workorder_magenta_candidates(candidate_crop)') < block.index('gray=cv2.cvtColor(candidate_crop')", "assert block.index('_workorder_confident_magenta_candidate(candidate_crop)') < block.index('gray=cv2.cvtColor(candidate_crop')")
V91.write_text(t,encoding='utf-8')

print('Applied v93 fail-closed Work Order confidence gate.')
