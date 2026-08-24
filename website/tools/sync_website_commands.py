#!/usr/bin/env python3
"""Regenerate website/js/commands.js from cogs/help.py COMMAND_INFO (source of truth).

The bot's own help categories are coarse (94 commands dumped into one bucket),
so we map every command into the website's 7 user-facing filter categories
by command name/semantics — producing a balanced, well-structured catalog.

Run from anywhere:
    python3 tools/sync_website_commands.py

Outputs:
  - accurate MN (description_mn) + EN (description_en)
  - correct slash/text type derived from the `usage` field
  - 7-category mapping, icons preserved from the old catalog where present
"""
import ast
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))          # website/tools
WEB = os.path.dirname(HERE)                                 # website
REPO = os.path.dirname(WEB)                                # repo root
HELP = os.path.join(REPO, "cogs", "help.py")
WEB_JS = os.path.join(WEB, "js", "commands.js")

CAT_ORDER = ["Economy", "Leveling", "Social", "Games", "Moderation", "Admin", "Utility"]
CAT_ICON = {
    "Economy": "💰", "Leveling": "📊", "Social": "💍", "Games": "🎲",
    "Moderation": "🛡️", "Admin": "⚙️", "Utility": "🔧",
}

WEB_CAT = {
    # Economy (money, work, cafe/shop items, bank)
    "admin-panel": "Economy", "bail": "Economy", "crime": "Economy", "jobs": "Economy",
    "taxinfo": "Economy", "workphrase": "Economy", "daily": "Economy", "work": "Economy",
    "balance": "Economy", "addmoney": "Economy", "removemoney": "Economy",
    "market": "Economy", "dine": "Economy", "cafe": "Economy",
    "deposit": "Economy", "withdraw": "Economy", "bankprotect": "Economy",
    "rob": "Economy", "transfer": "Economy", "shop": "Economy", "buy": "Economy",
    "sell": "Economy", "accessories": "Economy", "drink": "Economy", "eat": "Economy",
    "equip": "Economy", "equipped": "Economy", "iteminfo": "Economy", "sogtol": "Economy",
    "trade": "Games", "mp": "Games", "unequip": "Economy", "use": "Economy",
    "vape": "Economy", "inventory": "Utility",
    # Leveling
    "addxp": "Leveling", "removexp": "Leveling", "leveling_setup": "Leveling",
    "rank": "Leveling", "leaderboard": "Leveling", "serveractivity": "Leveling",
    # Social (family / marriage / confession / relationship)
    "adopt": "Social", "disown": "Social", "divorce": "Social", "familytree": "Social",
    "gift": "Social", "marriage_setup": "Social", "marriagepro": "Social",
    "propose": "Social", "spouse": "Social", "love": "Social", "tree": "Social",
    "confess": "Social", "confess_setup": "Social", "confess_stats": "Social",
    "confess_delete": "Social", "confess_blacklist": "Social",
    # Games
    "8ball": "Games", "blackjack": "Games", "cgive": "Games", "coin": "Games",
    "coinflipgame": "Games", "count_save": "Games", "count_stats_server": "Games",
    "count_stats_user": "Games", "crash": "Games", "dice": "Games", "gamble": "Games",
    "gamestats": "Games", "highcard": "Games", "highlow": "Games", "mafia_setup": "Games",
    "mafiacreate": "Games", "mafiaend": "Games", "mafiastart": "Games", "mines": "Games",
    "numberguess": "Games", "roll": "Games", "roulettegame": "Games", "rps": "Games",
    "slot": "Games", "trivia": "Games",
    # Moderation
    "ban": "Moderation", "banlist": "Moderation", "clear": "Moderation",
    "kick": "Moderation", "lock": "Moderation", "unlock": "Moderation",
    "unban": "Moderation", "untimeout": "Moderation", "warn": "Moderation",
    "warned": "Moderation", "warnedusers": "Moderation", "warnings": "Moderation",
    "set_log_channel": "Moderation", "avatar_config": "Moderation", "rrlist": "Moderation",
    "staff_counts": "Moderation", "staff_setup": "Moderation", "staff_status": "Moderation",
    "temprole_config": "Moderation", "unwarnid": "Moderation",
    # Admin
    "announce": "Admin", "counting_setup": "Admin", "greeting_reset": "Admin",
    "greeting_status": "Admin", "info": "Admin", "lang": "Admin", "rolelist": "Admin",
    "status": "Admin", "stick": "Admin", "unstick": "Admin", "voicesettings": "Admin",
    "voicesetup": "Admin", "template_create": "Admin", "template_delete": "Admin",
    "template_edit": "Admin", "template_list": "Admin", "template_preview": "Admin",
    # Utility (info, fun/emote, misc)
    "angry": "Utility", "autoaccept": "Utility", "avatar": "Utility", "bite": "Utility",
    "boop": "Utility", "bully": "Utility", "cat": "Utility", "cry": "Utility",
    "cuddle": "Utility", "dance": "Utility", "dog": "Utility", "fox": "Utility",
    "gif": "Utility", "hack": "Utility", "handhold": "Utility", "happy": "Utility",
    "help": "Utility", "highfive": "Utility", "hug": "Utility", "kiss": "Utility",
    "laugh": "Utility", "meme": "Utility", "pat": "Utility", "ping": "Utility",
    "placeholders": "Utility", "poke": "Utility", "profile": "Utility", "punch": "Utility",
    "quest": "Utility", "relax": "Utility", "slap": "Utility", "sleep": "Utility",
    "snuggle": "Utility", "stare": "Utility", "think": "Utility", "wave": "Utility",
}

def load_help():
    src = open(HELP, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "COMMAND_INFO":
                    return ast.literal_eval(node.value)
    raise SystemExit("COMMAND_INFO not found")

def existing_icons():
    if not os.path.exists(WEB_JS):
        return {}
    text = open(WEB_JS, encoding="utf-8").read()
    m = {}
    for mm in re.finditer(r"name:\s*'([^']+)',\s*cat:\s*'[^']+',\s*icon:\s*'([^']+)'", text):
        m[mm.group(1)] = mm.group(2)
    return m

def parse_args(usage):
    out = []
    for tok in re.findall(r"<([^>]+)>", usage):
        tok = tok.strip()
        optional = tok.endswith("?")
        key = tok.rstrip("?").split()[0]
        out.append({"key": key, "req": not optional})
    return out

def main():
    info = load_help()
    icons = existing_icons()

    missing = [n for n in info if n not in WEB_CAT]
    if missing:
        raise SystemExit("Unmapped commands (add to WEB_CAT): " + ", ".join(missing))

    rows = []
    for name, d in info.items():
        wcat = WEB_CAT[name]
        usage = d.get("usage", f"A!{name}")
        icon = icons.get(name) or CAT_ICON[wcat]
        rows.append({
            "name": name, "cat": wcat, "icon": icon,
            "desc": d.get("description_mn", ""), "descEN": d.get("description_en", ""),
            "args": parse_args(usage), "example": usage,
            "_order": (CAT_ORDER.index(wcat), name),
        })
    rows.sort(key=lambda r: r["_order"])

    total = len(rows)
    cats = {}
    for r in rows:
        cats[r["cat"]] = cats.get(r["cat"], 0) + 1
    slash = sum(1 for r in rows if r["example"].startswith("/"))
    text = total - slash
    print(f"TOTAL={total}  slash={slash} text={text}")
    for c in CAT_ORDER:
        print(f"  {c}: {cats.get(c,0)}")

    def jsobj(r):
        args_js = json.dumps(r["args"], ensure_ascii=False)
        return (
            "  { name: '%s', cat: '%s', icon: '%s', desc: %s, descEN: %s, "
            "args: %s, example: '%s' }"
            % (r["name"], r["cat"], r["icon"],
               json.dumps(r["desc"], ensure_ascii=False),
               json.dumps(r["descEN"], ensure_ascii=False),
               args_js, r["example"])
        )

    body = ",\n".join(jsobj(r) for r in rows)
    out = f"""/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Command catalog (auto-generated from cogs/help.py COMMAND_INFO)
   {total} commands · slash={slash} text={text} · generated by tools/sync_website_commands.py
   Mapped into the website's 7 user-facing filter categories.
   ============================================================ */
const COMMANDS = [
{body}
];

/* Command policy: a command whose usage starts with '/' is slash-only;
   everything else uses the A! text prefix. */
const TYPED_COMMANDS = COMMANDS.map(c => ({{
  ...c,
  type: c.example.trim().startsWith('/') ? 'slash' : 'text',
}}));
/* Dedupe (guard) and export */
const seen = new Set();
window.COMMAND_LIST = TYPED_COMMANDS.filter(c => {{
  if (seen.has(c.name)) return false;
  seen.add(c.name);
  return true;
}});
window.COMMAND_CATS = ['all', 'Economy', 'Leveling', 'Social', 'Games', 'Moderation', 'Admin', 'Utility'];

/* Category metadata: mongolian label, theme color, emoji */
window.CAT_META = {{
  all:        {{ label: 'Бүгд',        labelEN: 'All',           color: '#89B4FA', icon: '🗂️' }},
  Economy:    {{ label: 'Economy',     labelEN: 'Economy',       color: '#89B4FA', icon: '💰' }},
  Leveling:   {{ label: 'Leveling',    labelEN: 'Leveling',      color: '#94E2D5', icon: '📊' }},
  Social:     {{ label: 'Гэр бүл',     labelEN: 'Family',        color: '#F38BA8', icon: '💍' }},
  Games:      {{ label: 'Тоглоом',     labelEN: 'Games',         color: '#FAB387', icon: '🎲' }},
  Moderation: {{ label: 'Модерац',     labelEN: 'Moderation',    color: '#A6E3A1', icon: '🛡️' }},
  Admin:      {{ label: 'Админ',       labelEN: 'Admin',         color: '#B4BEFE', icon: '⚙️' }},
  Utility:    {{ label: 'Бусад',       labelEN: 'Utility',       color: '#8C8FA1', icon: '🔧' }},
}};
"""
    open(WEB_JS, "w", encoding="utf-8").write(out)
    print(f"Wrote {WEB_JS} ({total} commands)")

if __name__ == "__main__":
    main()
