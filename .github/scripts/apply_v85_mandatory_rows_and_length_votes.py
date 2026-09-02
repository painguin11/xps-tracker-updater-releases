from pathlib import Path

APP = Path('working_source/app/reno_scan_updater.py')
TEST = Path('working_source/tests/regression_v85_mandatory_rows_and_length_votes.py')
src = APP.read_text(encoding='utf-8')

old = """def _select_independent_length_candidate(gray_values,threshold_values,kind='Pipe',expected=None):
    \"\"\"Select only among OCR-observed values; never round or manufacture a length.\"\"\"
    gray=[float(v) for v in (gray_values or []) if _valid_row_length_value(v)]
    threshold=[float(v) for v in (threshold_values or []) if _valid_row_length_value(v)]
    values=gray+threshold
    if not values:
        return None,False,'no valid OCR values'
    counts={value:values.count(value) for value in set(values)}
    # A reread must have at least two independent observations of the same value.
    eligible={value:count for value,count in counts.items() if count>=2}
    if not eligible:
        return None,False,'independent views disagree'
    strongest=max(eligible.values())
    winners=[value for value,count in eligible.items() if count==strongest]
    if len(winners)==1:
        return winners[0],True,'strongest independent support'
    if kind=='Pipe':
        # On this B&C scan grayscale can preserve a damaged grid-connected glyph
        # while the 4x threshold view resolves it (242.15 -> 242.16, 260.3 -> 360.3).
        threshold_counts={value:threshold.count(value) for value in winners}
        best_threshold=max(threshold_counts.values()) if threshold_counts else 0
        threshold_winners=[value for value,count in threshold_counts.items()
                           if count==best_threshold and count>=2]
        if len(threshold_winners)==1:
            return threshold_winners[0],True,'threshold-supported tie break'
    if expected not in (None,0):
        # The master may only choose between equally supported OCR observations.
        distances={value:abs(value-float(expected)) for value in winners}
        nearest=min(distances.values())
        nearest_values=[value for value,distance in distances.items() if distance==nearest]
        if len(nearest_values)==1:
            return nearest_values[0],True,'master tie break between OCR values'
    return None,False,'independent views remain tied'
"""
new = """def _select_independent_length_candidate(gray_values,threshold_values,kind='Pipe',expected=None):
    \"\"\"Select only among OCR-observed values; never round or manufacture a length.\"\"\"
    gray=[float(v) for v in (gray_values or []) if _valid_row_length_value(v)]
    threshold=[float(v) for v in (threshold_values or []) if _valid_row_length_value(v)]
    values=gray+threshold
    if not values:
        return None,False,'no valid OCR values'

    # During mismatch recovery the master is allowed to reject a wildly implausible
    # OCR hallucination, but it never supplies a replacement value. If at least one
    # actually-observed candidate is within 35% of the master, ignore observations
    # outside that window before comparing independent views. This is what keeps a
    # grid-connected 774 from outvoting the visibly printed 77.4.
    master_filtered=False
    if expected not in (None,0):
        expected_value=float(expected)
        plausible=[value for value in values
                   if abs(value-expected_value)/max(abs(expected_value),1.0)<.35]
        if plausible:
            allowed=set(plausible); master_filtered=True
            gray=[value for value in gray if value in allowed]
            threshold=[value for value in threshold if value in allowed]
            values=gray+threshold

    counts={value:values.count(value) for value in set(values)}
    if master_filtered and len(counts)==1:
        # The value still came from OCR. The master only eliminated impossible
        # alternatives; it did not create or round this measurement.
        value=next(iter(counts))
        return value,True,'sole master-plausible OCR value'

    # Prefer values repeated by independent views whenever possible.
    eligible={value:count for value,count in counts.items() if count>=2}
    if eligible:
        strongest=max(eligible.values())
        winners=[value for value,count in eligible.items() if count==strongest]
        if len(winners)==1:
            return winners[0],True,'strongest independent support'
        if kind=='Pipe':
            threshold_counts={value:threshold.count(value) for value in winners}
            best_threshold=max(threshold_counts.values()) if threshold_counts else 0
            threshold_winners=[value for value,count in threshold_counts.items()
                               if count==best_threshold and count>=1]
            if len(threshold_winners)==1:
                return threshold_winners[0],True,'threshold-supported tie break'
        if expected not in (None,0):
            distances={value:abs(value-float(expected)) for value in winners}
            nearest=min(distances.values())
            nearest_values=[value for value,distance in distances.items() if distance==nearest]
            if len(nearest_values)==1:
                return nearest_values[0],True,'master tie break between OCR values'
        return None,False,'independent views remain tied'

    # A subtle one-hundredth glyph difference can leave exactly one grayscale and
    # one threshold observation (242.15 vs 242.16). When both are already inside
    # the master-plausible window and differ by no more than five hundredths, the
    # high-resolution threshold view is the safer reading of the printed digit.
    unique=sorted(counts)
    if kind=='Pipe' and master_filtered and len(unique)==2:
        threshold_unique=sorted(set(threshold))
        if len(threshold_unique)==1 and all(abs(threshold_unique[0]-v)<=.05 for v in unique):
            return threshold_unique[0],True,'threshold-supported close disagreement'
    return None,False,'independent views disagree'
"""
if src.count(old) != 1:
    raise SystemExit('independent length selector block not found exactly once')
src = src.replace(old, new)

old = """    total_band_index=printed_total_info.get('band_index')
    batch_cleaning_values=(
"""
new = """    total_band_index=printed_total_info.get('band_index')
    header_band_index=prepared.get('header_band_index')
    mandatory_data_bands=set()
    if (header_band_index is not None and total_band_index is not None and
            int(total_band_index)>int(header_band_index)):
        # Once both structural anchors are known, every physical grid band between
        # the printed header and total is a real table row. OCR failure may make the
        # row review-only, but it must never make the row disappear from the summary
        # or from total-length arithmetic.
        mandatory_data_bands=set(range(int(header_band_index)+1,int(total_band_index)))
    batch_cleaning_values=(
"""
if src.count(old) != 1:
    raise SystemExit('total/header anchor block not found exactly once')
src = src.replace(old, new)

old = """    for band_index,(y1,y2) in enumerate(bands):
        header_band_index=prepared.get('header_band_index')
        if header_band_index is not None and band_index==header_band_index:
"""
new = """    for band_index,(y1,y2) in enumerate(bands):
        mandatory_data_band=band_index in mandatory_data_bands
        if header_band_index is not None and band_index==header_band_index:
"""
if src.count(old) != 1:
    raise SystemExit('band loop anchor block not found exactly once')
src = src.replace(old, new)

old = """        if not match and (edge_band or tall_band) and not endpoint_signal:
            continue
        if not match and not endpoint_signal:
            continue
"""
new = """        if not mandatory_data_band and not match and (edge_band or tall_band) and not endpoint_signal:
            continue
        if not mandatory_data_band and not match and not endpoint_signal:
            continue
"""
if src.count(old) != 1:
    raise SystemExit('endpoint row-drop block not found exactly once')
src = src.replace(old, new)

old = """            if not _keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,asset_format=asset_format):
                continue
"""
new = """            if (not mandatory_data_band and
                    not _keep_unresolved_pair_row(unresolved_up,unresolved_dn,value,d,asset_format=asset_format)):
                continue
"""
if src.count(old) != 1:
    raise SystemExit('unresolved structural row-drop block not found exactly once')
src = src.replace(old, new)

old = """        if d is None:
            continue
"""
new = """        if d is None and not mandatory_data_band:
            continue
"""
if src.count(old) != 1:
    raise SystemExit('date row-drop block not found exactly once')
src = src.replace(old, new)

old = """        if key in seen and kind!='pipes': continue
        seen.add(key); rows.append(rec)
"""
new = """        if key in seen and kind!='pipes':
            # A duplicated OCR identity is not permission to delete a physical
            # table row. Keep it visible and review-only so its printed length still
            # participates in total validation.
            rec.setdefault('validation_warnings',[]).append('DUPLICATE IN PDF')
            rec['skip_update']=True
        seen.add(key); rows.append(rec)
"""
if src.count(old) != 1:
    raise SystemExit('cleaning duplicate-drop block not found exactly once')
src = src.replace(old, new)

APP.write_text(src, encoding='utf-8')

TEST.write_text(r'''from pathlib import Path
import ast

src=Path('working_source/app/reno_scan_updater.py').read_text(encoding='utf-8')
assert 'mandatory_data_bands=set(range(int(header_band_index)+1,int(total_band_index)))' in src
assert 'mandatory_data_band=band_index in mandatory_data_bands' in src
assert 'if not mandatory_data_band and not match and not endpoint_signal:' in src
assert 'if d is None and not mandatory_data_band:' in src
assert "rec.setdefault('validation_warnings',[]).append('DUPLICATE IN PDF')" in src
assert "if key in seen and kind!='pipes': continue" not in src

# Exercise the production candidate selector without importing Windows-only deps.
tree=ast.parse(src)
names={'_valid_row_length_value','_select_independent_length_candidate'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
ns={'MAX_ROW_LENGTH':1700.0}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v85-length-votes>','exec'),ns)
select=ns['_select_independent_length_candidate']

# Grid strokes can make the wrong value win by raw vote count. A visibly observed
# master-plausible value must survive without the master manufacturing anything.
value,confident,source=select([774.0,77.4],[774.0,774.0],'Pipe',76.095994)
assert confident and value==77.4 and source=='sole master-plausible OCR value',(value,source)

# The expanded gray/threshold views can differ only in the final hundredth.
# High-resolution threshold wins this close, already-plausible disagreement.
value,confident,source=select([242.15],[242.16],'Pipe',242.12554)
assert confident and value==242.16 and source=='threshold-supported close disagreement',(value,source)

# Repeated correct observations still win normally.
value,confident,source=select([245.8,245.8],[58.0,285.8],'Pipe',245.343454)
assert confident and value==245.8,(value,source)

# If every OCR view genuinely disagrees and the master cannot safely narrow it,
# fail closed rather than inventing a result.
value,confident,source=select([100.0],[600.0],'Pipe',300.0)
assert not confident and value is None

print('v85 mandatory-row and independent-length-vote regression passed.')
''', encoding='utf-8')

print('Applied v85 mandatory-row retention and length-vote recovery patch.')
