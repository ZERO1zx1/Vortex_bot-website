"""Fix branding typo in test_fonts.py using BOT_NAME from branding.py as canonical reference."""
import re

# Read canonical BOT_NAME from branding.py
with open("utils/branding.py", "r", encoding="utf-8") as f:
    branding_src = f.read()
m = re.search(r'BOT_NAME\s*=\s*"([^"]+)"', branding_src)
canonical_name = m.group(1)
canonical_h = canonical_name[3]  # The 'h' character
wrong_g = chr(0x1D4F0)  # 𝓰 - the wrong 'g' character

results = []
results.append(f"Canonical: {canonical_name}")
results.append(f"Canonical[3] U+{ord(canonical_h):04X}")
results.append(f"Wrong G: U+{ord(wrong_g):04X}")

# ── Fix test_fonts.py ──
filepath = "tests/test_fonts.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

if wrong_g in content:
    # Replace all occurrences of the wrong character with the correct one
    content = content.replace(wrong_g, canonical_h)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    results.append(f"✓ Fixed {filepath}: replaced {wrong_g} with {canonical_h}")
else:
    results.append(f"No wrong char found in {filepath}")

# ── Verify supabase_schema.sql and fonts.py are already fixed ──
for fp in ["database/supabase_schema.sql", "utils/fonts.py"]:
    with open(fp, "r", encoding="utf-8") as f:
        c = f.read()
    if wrong_g in c:
        results.append(f"✗ {fp} still has wrong char!")
        c = c.replace(wrong_g, canonical_h)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(c)
        results.append(f"✓ Fixed {fp}")
    elif canonical_name[:4] in c:
        results.append(f"✓ {fp}: already correct")
    else:
        results.append(f"  {fp}: no bot name found (may be OK)")

# ── Final verification: check all files for the wrong character ──
import os
all_files = []
for root, dirs, files in os.walk("."):
    # Skip hidden dirs, __pycache__, .agents, node_modules
    dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__" and d != ".agents"]
    for fn in files:
        if fn.endswith((".py", ".sql", ".md", ".txt", ".json")):
            all_files.append(os.path.join(root, fn))

wrong_remaining = []
for fp in all_files:
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            c = f.read()
        if wrong_g in c:
            wrong_remaining.append(fp)
    except Exception:
        pass

if wrong_remaining:
    results.append(f"\n✗ Files still containing wrong char:")
    for fp in wrong_remaining:
        results.append(f"  {fp}")
else:
    results.append(f"\n✓ No files contain the wrong character U+{ord(wrong_g):04X}")

with open("branding_fix_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
