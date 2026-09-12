import os, re
src = open('main.py', encoding='utf-8').read()
m = re.search(r'cogs_to_load = \[(.*?)\]', src, re.S)
loaded = set(re.findall(r'"(\w+)"', m.group(1)))
disk = {f[:-3] for f in os.listdir('cogs') if f.endswith('.py') and f != '__init__.py'}
print('main.py lists:', len(loaded), 'cogs | on disk:', len(disk))
print('on disk but NOT loaded:', sorted(disk - loaded))
print('listed but missing file:', sorted(loaded - disk))