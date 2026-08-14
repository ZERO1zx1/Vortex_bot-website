import os

# Check for the incorrect capital E in the branding string
# The canonical name is: Aether  蒼穹 (with small script e)
# The wrong name has: Aether  蒼穹 (with capital script E)
# We check by looking for the Chinese characters and then examining the code points

files = [
    'database/supabase_schema.sql',
    'tests/test_fonts.py',
    'utils/fonts.py',
    'utils/branding.py',
    'cogs/help.py',
    'main.py',
]

results = []
for f in files:
    if not os.path.exists(f):
        results.append(f'{f}: FILE NOT FOUND')
        continue
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    # Find lines with the Chinese characters (part of branding)
    for i, line in enumerate(content.split('\n'), 1):
        if '蒼穹' in line:
            # Extract the branding string and check code points
            # Find the script characters before 蒼穹
            idx = line.index('蒼穹')
            prefix = line[max(0,idx-10):idx]
            codepoints = [hex(ord(c)) for c in prefix if ord(c) > 127]
            results.append(f'{f} L{i}: codepoints={codepoints} | {line.strip()[:120]}')

with open('branding_result2.txt', 'w', encoding='utf-8') as out:
    out.write('\n'.join(results))
    out.write('\n--- done ---\n')
