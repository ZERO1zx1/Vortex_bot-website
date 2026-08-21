#!/usr/bin/env python3
"""Expand utils/i18n.py DICT with common embed strings shared across all cogs.

Adds reusable keys: jail (🚔 Шорон) variants, hungry/angry/rest, common errors,
cooldowns, etc. This makes every cog ready to use t() / t_direct() without
duplicating strings. Existing keys are never modified.
"""
import re
import sys

F = "/home/ubuntu/gurtendev/utils/i18n.py"

# New keys: {key: (mn, en)}
NEW_KEYS = [
    # ============ COMMON STATES (used by many cogs) ============
    ("common.jail.title", "🚔 Шорон", "🚔 Jail"),
    ("common.jail.desc", "Та шоронд байна.", "You are in jail."),
    ("common.jail.cant_act", "❌ Шоронд байхдаа энэ үйлдэл боломжгүй.", "❌ You can't do that while in jail."),
    ("common.jail.no_crime", "❌ Шоронд гэмт хэрэг үйлдэх боломжгүй.", "❌ You can't commit crimes in jail."),
    ("common.jail.no_work", "❌ Шоронгоос урамшуулал авах боломжгүй.", "❌ You can't earn rewards from jail."),
    ("common.jail.no_food", "❌ Шоронд хоол захиалах боломжгүй.", "❌ You can't order food in jail."),
    ("common.jail.no_gift", "❌ Шоронд бэлэг өгөх боломжгүй.", "❌ You can't send gifts in jail."),
    ("common.jail.no_play", "❌ Шоронд тоглох боломжгүй.", "❌ You can't play while in jail."),
    ("common.hungry.title", "🍔 Өлсөж байна!", "🍔 You're hungry!"),
    ("common.hungry.desc", "`A!eat` командаар хоол идээрэй.", "Eat with `A!eat`."),
    ("common.angry.title", "😡 Ууртай байна!", "😡 You're angry!"),
    ("common.angry.desc", "`A!relax` командаар амраарай.", "Calm down with `A!relax`."),
    ("common.angry.no_play", "😡 Ууртай үед тоглох боломжгүй! `A!relax` командаар амраарай.", "😡 You can't play while angry! Use `A!relax` first."),
    ("common.rest.title", "⏳ АМРАЛТ", "⏳ COOLDOWN"),
    ("common.rest.desc", "**{m}м {s}с** хүлээ.", "Wait **{m}m {s}s**."),

    # ============ COMMON ERRORS / MISC ============
    ("common.missing_args", "❌ Аргумент дутуу байна: `{usage}`", "❌ Missing arguments: `{usage}`"),
    ("common.bad_amount", "❌ Мөнгөн дүн буруу байна. Эерэг тоо оруулна уу.", "❌ Invalid amount. Enter a positive number."),
    ("common.not_found", "❌ Олдсонгүй.", "❌ Not found."),
    ("common.need_mention", "❌ Хэрэглэгч дурдана уу (жишээ нь: `A!{cmd} @хүн`).", "❌ Mention a user (e.g. `A!{cmd} @user`)."),
    ("common.no_perm", "❌ Энэ коммандыг ашиглах эрх байхгүй.", "❌ You don't have permission to use this command."),
    ("common.only_slash", "❌ Энэ комманд зөвхөн `/` slash командаар ажиллана.", "❌ This command only works as a slash `/` command."),
    ("common.cooldown", "⏳ {time} хүлээгээрэй.", "⏳ Please wait {time}."),
    ("common.success", "✅ Амжилттай боллоо!", "✅ Success!"),

    # ============ HELP ============
    ("help.not_found", "❌ Тушаал олдсонгүй", "❌ Command not found"),
    ("help.not_found_desc", "`{key}` нэртэй тушаал байхгүй байна.{hint}", "No command named `{key}`.{hint}"),
]


def main() -> int:
    src = open(F).read()

    # Insert before the closing `}` of DICT (right before "# ── API ──")
    anchor = "# ── API ───────────────────────────────────────────"
    if anchor not in src:
        print("ERROR: anchor not found")
        return 1

    lines = []
    for key, mn, en in NEW_KEYS:
        # Check the key doesn't already exist
        if f'"{key}"' in src or f"'{key}'" in src:
            continue
        lines.append(f'    "{key}": {{"mn": {mn!r}, "en": {en!r}}},')

    if not lines:
        print("All keys already exist — nothing to add.")
        return 0

    block = "\n".join(lines) + "\n"
    src = src.replace(anchor, block + "\n" + anchor)
    open(F, "w").write(src)
    print(f"Added {len(lines)} keys to DICT.")

    # Syntax check
    import py_compile
    try:
        py_compile.compile(F, doraise=True)
    except py_compile.PyCompileError as e:
        print("SYNTAX ERROR:", e)
        return 2
    print("Syntax OK:", F)
    return 0


if __name__ == "__main__":
    sys.exit(main())
