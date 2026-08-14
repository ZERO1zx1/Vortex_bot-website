import os

bad_e = chr(0x1D494)  # MATHEMATICAL SCRIPT CAPITAL E
good_e = chr(0x1D4E6)  # MATHEMATICAL SCRIPT SMALL E

files = [
    'database/supabase_schema.sql',
    'tests/test_fonts.py',
    'utils/fonts.py',
    'utils/branding.py',
]

results = []
for f in files:
    if not os.path.exists(f):
        results.append(f'{f}: FILE NOT FOUND')
        continue
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    has_bad = bad_e in content
    has_good = good_e in content
    results.append(f'{f}: bad_E={has_bad}, good_e={has_good}')
    for i, line in enumerate(content.split('\n'), 1):
        if bad_e in line or good_e in line:
            results.append(f'  L{i}: {line.strip()[:120]}')

with open('branding_result.txt', 'w', encoding='utf-8') as out:
    out.write('\n'.join(results))
    out.write('\n--- done ---\n')
