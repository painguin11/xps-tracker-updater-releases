from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REORDERED=ROOT/'working_source/tests/regression_post_v103_manhole_reordered_columns.py'
EXPECTED=ROOT/'working_source/tests/regression_post_v102_manhole_expected_count_retry.py'


def patch_reordered():
    text=REORDERED.read_text(encoding='utf-8')
    old='''class _CV2Stub:\n    COLOR_RGB2GRAY=1\n    BORDER_CONSTANT=0\n    @staticmethod\n    def cvtColor(image,code):\n        return image[:,:,0] if getattr(image,'ndim',0)==3 else image\n    @staticmethod\n    def copyMakeBorder(image,*args,**kwargs):\n        return image\n'''
    new='''class _CV2Stub:\n    COLOR_RGB2GRAY=1\n    BORDER_CONSTANT=0\n    THRESH_BINARY=0\n    @staticmethod\n    def cvtColor(image,code):\n        return image[:,:,0] if getattr(image,'ndim',0)==3 else image\n    @staticmethod\n    def bitwise_not(image):\n        return 255-image\n    @staticmethod\n    def threshold(image,*args):\n        return (0,image)\n    @staticmethod\n    def copyMakeBorder(image,*args,**kwargs):\n        return image\n'''
    if old in text:
        text=text.replace(old,new,1)
    elif 'def bitwise_not(image):' not in text:
        raise SystemExit('reordered regression CV2 anchor not found')

    old_count="assert len(rows)==37,rows\n"
    new_count="assert len(rows)==37, f'expected 37 physical rows including NEW DN-1788A; got {len(rows)} rows: {[row[\"asset\"] for row in rows]}'\n"
    if old_count in text:
        text=text.replace(old_count,new_count,1)
    elif 'expected 37 physical rows including NEW DN-1788A' not in text:
        raise SystemExit('reordered regression row-count assertion anchor not found')

    old_assert="assert [row['asset'] for row in rows]==IDS,[row['asset'] for row in rows]\n"
    new_assert="assert [row['asset'] for row in rows]==IDS, f'expected exact 37-row asset order including NEW DN-1788A; got assets: {[row[\"asset\"] for row in rows]}'\n"
    if old_assert in text:
        text=text.replace(old_assert,new_assert,1)
    elif 'expected exact 37-row asset order including NEW DN-1788A' not in text:
        raise SystemExit('reordered regression asset-order assertion anchor not found')

    if "assert 'grid_has_confirmed_new' in text" not in text:
        marker="retry_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_retry_year15_manhole_rows')\n"
        if marker in text:
            text=text.replace(marker,marker+"assert 'grid_has_confirmed_new' in text or '_mh_suffix_confirmed' not in text\n",1)
    REORDERED.write_text(text,encoding='utf-8')


def patch_expected():
    text=EXPECTED.read_text(encoding='utf-8')
    needle="    '_ocr_asset_candidates':ocr_assets,\n"
    addition=needle+"    '_confirmed_suffix_asset_candidates':lambda cell,known_items,asset_format=None: [],\n"
    if "'_confirmed_suffix_asset_candidates':" not in text:
        if needle not in text:
            raise SystemExit('expected-count regression namespace anchor not found')
        text=text.replace(needle,addition,1)
    EXPECTED.write_text(text,encoding='utf-8')


if __name__=='__main__':
    patch_reordered()
    patch_expected()
    print('Fixed post-v104 NEW MANHOLE regression harnesses')
