from pathlib import Path
p=Path('working_source/tests/regression_v83_length_recovery.py')
s=p.read_text(encoding='utf-8')
s=s.replace("ns={}\nexec(compile(ast.Module(body=nodes,type_ignores=[]),'<helpers>','exec'),ns)",
            "ns={'re':re}\nexec(compile(ast.Module(body=nodes,type_ignores=[]),'<helpers>','exec'),ns)")
p.write_text(s,encoding='utf-8')
print('fixed v83 regression harness')
