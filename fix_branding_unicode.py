"""Fix the 𝓔𝓮𝓽𝓖 branding typo across all files using exact BOT_NAME from branding.py."""
import os

# ── 1. Read the canonical BOT_NAME from branding.py ──
with open("utils/branding.py", "r", encoding="utf-8") as f:
    branding_src = f.read()

# Extract BOT_NAME value
import re
m = re.search(r'BOT_NAME\s*=\s*"([^"]+)"', branding_src)
if not m:
    print("ERROR: Could not find BOT_NAME in branding.py")
    exit(1)

canonical_name = m.group(1)
print(f"Canonical BOT_NAME from branding.py: {canonical_name}")

# Get the codepoints
print(f"Canonical codepoints: { [hex(ord(c)) for c in canonical_name] }")

# ── 2. Define the typo (wrong 'g' character) ──
# The typo is the canonical name but with the 'h' character replaced by a capital 'G'
# We need to find what the wrong character is in each file
# The git grep pattern was 𝓔𝓮𝓽𝓖 (capital G instead of lowercase h)
# Let's find the exact wrong character by looking at what differs

# Build the typo version: replace the 4th character (h) with G variant
correct_codepoints = [ord(c) for c in canonical_name]
# The 'h' in the canonical name - find which position has a character that maps to 'h'
for i, cp in enumerate(correct_codepoints):
    char_name = chr(cp)
    print(f"  Position {i}: {char_name} = U+{cp:04X}")

# ── 3. Find and fix in target files ──
target_files = [
    "database/supabase_schema.sql",
    "utils/fonts.py",
    "tests/test_fonts.py",
]

for filepath in target_files:
    if not os.path.exists(filepath):
        print(f"\nSKIP {filepath}: file not found")
        continue
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all lines that contain any character from the typo pattern
    # The typo is 𝓔𝓮𝓽𝓖 (capital G variant) instead of 𝓔𝓮𝓽𝓜 (lowercase h variant)
    # We need to find the wrong 'G' character and replace it with the correct 'h' character

    # Get the correct h character from canonical_name
    # Find the character in canonical_name that corresponds to 'h'
    canonical_h = None
    for i, cp in enumerate(correct_codepoints):
        c = chr(cp)
        # The canonical name is 𝓔𝓮𝓽𝓜𝓮𝓻  蒼穹
        # Position 3 should be 'h' (0-indexed: 𝓔=0, 𝓮=1, 𝓽=2, 𝓜=3)
        if i == 3:
            canonical_h = c
            break

    if canonical_h is None:
        print(f"ERROR: Could not find h character in canonical name")
        exit(1)

    print(f"\nCorrect h character: {canonical_h} = U+{ord(canonical_h):04X}")

    # Now find the wrong character in the file
    # It should be at the same position in the typo string
    # The typo has a capital G at position 3
    # We need to find this character

    lines = content.split("\n")
    changed = False
    for i, line in enumerate(lines):
        if "蒼穹" in line or "𝓔𝓮𝓣" in line or "𝓔𝓮𝓽" in line:
            # This line has the bot name - check for the wrong G
            # Try to find and replace the wrong character
            old_line = line
            # Replace any occurrence of the wrong G variant with the correct h
            # The wrong character is at position 3 in the typo version
            # We can find it by looking for the pattern where the 4th script char is a capital G
            for j in range(len(line) - 5):
                if line[j:j+6] == canonical_name[:3] + "?" + canonical_name[4:]:
                    # Found the pattern - but we don't know the wrong char yet
                    pass

            # More robust: look for common G-variant characters
            # The wrong character could be 𝓖 (U+1D4D6) or 𝔊 (U+1D506) or 𝕲 (U+1D57C) etc.
            # Let's check what characters in the line at position 3 differ from canonical
            for j in range(len(line)):
                if line[j] == "蒼" and j >= 4:
                    # The bot name ends with 蒼穹, so the bot name is the 6 chars before 蒼
                    name_start = j - 6
                    if name_start >= 0:
                        name_in_file = line[name_start:j]
                        if name_in_file != canonical_name:
                            print(f"  Found wrong name in {filepath} line {i+1}: {name_in_file}")
                            print(f"  Wrong codepoints: {[hex(ord(c)) for c in name_in_file]}")
                            # Replace the wrong character at position 3
                            if name_in_file[3] != canonical_h:
                                wrong_char = name_in_file[3]
                                print(f"  Wrong char at position 3: {wrong_char} = U+{ord(wrong_char):04X}")
                                print(f"  Correct char at position 3: {canonical_h} = U+{ord(canonical_h):04X}")
                                line = line[:name_start+3] + canonical_h + line[name_start+4:]
                                changed = True
                                print(f"  Fixed: {canonical_name[:3]}{canonical_h}{canonical_name[4:]}")
                                break
            lines[i] = line

    if changed:
        new_content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  ✓ Fixed {filepath}")
    else:
        # Try a more direct approach - replace the wrong G with correct h
        # Look for any script G character followed by the rest of the name
        print(f"  No automatic fix found for {filepath}, trying direct replacement...")
        # Check if the wrong name appears anywhere
        for cp in range(0x1D400, 0x1DC00):
            c = chr(cp)
            if c != canonical_h:
                wrong_name = canonical_name[:3] + c + canonical_name[4:]
                if wrong_name in content:
                    print(f"  Found wrong char U+{cp:04X} in {filepath}")
                    content = content.replace(wrong_name, canonical_name)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"  ✓ Fixed {filepath} (direct replacement)")
                    changed = True
                    break
        if not changed:
            print(f"  No typo found in {filepath}")

print("\n=== Verification ===")
# Verify no more wrong characters
import subprocess
result = subprocess.run(["git", "grep", "-n", "𝓔𝓮𝓣𝓖"], capture_output=True, text=True)
# Actually, let's check for the specific wrong character
# The wrong G character could be various Unicode chars
# Let's check all files for any character that's similar to G but not the correct h
for filepath in ["database/supabase_schema.sql", "utils/fonts.py", "tests/test_fonts.py"]:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if canonical_name in content:
            print(f"  ✓ {filepath}: contains canonical name")
        # Check for any remaining wrong G characters
        found_wrong = False
        for cp in range(0x1D400, 0x1DC00):
            c = chr(cp)
            if c != canonical_h and c != canonical_name[3]:
                wrong_name = canonical_name[:3] + c + canonical_name[4:]
                if wrong_name in content:
                    print(f"  ✗ {filepath}: still has wrong char U+{cp:04X}: {wrong_name}")
                    found_wrong = True
        if not found_wrong:
            print(f"  ✓ {filepath}: no wrong characters found")
