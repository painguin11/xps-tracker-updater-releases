from pathlib import Path

p=Path('working_source/app/reno_scan_updater.py')
text=p.read_text(encoding='utf-8')

old='''        if cleaning_header and ('project yea' in norm or 'field crew' in norm or score): kind='cleaning'; s=25+score
        elif 'manhole number' in norm or ('drainage area' in norm and 'street' in norm and 'date' in norm): kind='manholes'; s=20
        elif ('length surveyed' in norm or 'surveyed length' in norm) and score: kind='pipes'; s=20+score
        else: kind='other'; s=sum(x in l for x in ('up mh','dn mh','wheel walk','manhole number','length surveyed'))
'''
new='''        if cleaning_header and ('project yea' in norm or 'field crew' in norm or score): kind='cleaning'; s=25+score
        elif 'manhole number' in norm: kind='manholes'; s=20
        elif ('length surveyed' in norm or 'surveyed length' in norm) and score: kind='pipes'; s=20+score
        elif (('drainage area' in norm and 'street' in norm and 'date' in norm) and
              not ('length surveyed' in norm or 'surveyed length' in norm)): kind='manholes'; s=20
        else: kind='other'; s=sum(x in l for x in ('up mh','dn mh','wheel walk','manhole number','length surveyed'))
'''
assert text.count(old)==1,'fast classification block changed'
text=text.replace(old,new,1)

old_retry='''            if cleaning_header and ('project yea' in retry_norm or 'field crew' in retry_norm or endpoint_score):
                retry_kind='cleaning'; retry_score=25+endpoint_score
            elif ('manhole number' in retry_norm or
                  ('drainage area' in retry_norm and 'street' in retry_norm and 'date' in retry_norm)):
                retry_kind='manholes'; retry_score=20
            elif ('length surveyed' in retry_norm or 'surveyed length' in retry_norm) and endpoint_score:
                retry_kind='pipes'; retry_score=20+endpoint_score
            else:
                retry_kind='other'; retry_score=0
'''
new_retry='''            if cleaning_header and ('project yea' in retry_norm or 'field crew' in retry_norm or endpoint_score):
                retry_kind='cleaning'; retry_score=25+endpoint_score
            elif 'manhole number' in retry_norm:
                retry_kind='manholes'; retry_score=20
            elif ('length surveyed' in retry_norm or 'surveyed length' in retry_norm) and endpoint_score:
                retry_kind='pipes'; retry_score=20+endpoint_score
            elif (('drainage area' in retry_norm and 'street' in retry_norm and 'date' in retry_norm) and
                  not ('length surveyed' in retry_norm or 'surveyed length' in retry_norm)):
                retry_kind='manholes'; retry_score=20
            else:
                retry_kind='other'; retry_score=0
'''
assert text.count(old_retry)==1,'high-resolution classification block changed'
text=text.replace(old_retry,new_retry,1)
p.write_text(text,encoding='utf-8')
print('Adjusted explicit Pipe/Manhole header precedence')
