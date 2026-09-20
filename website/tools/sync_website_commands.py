#!/usr/bin/env python3
"""Regenerate website/js/commands.js from src/cogs/help.py COMMAND_INFO (source of truth).

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
HELP = os.path.join(REPO, "src", "cogs", "help.py")
WEB_JS = os.path.join(WEB, "js", "commands.js")
BACKEND_JSON = os.path.join(REPO, "backend", "data", "commands.json")
COGS_DIR = os.path.join(REPO, "src", "cogs")
LOADER = os.path.join(REPO, "src", "utils", "cog_loader.py")

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
    "government": "Economy", "economy-config": "Economy",
    "treasury": "Economy", "economy": "Economy",
    # Leveling
    "addxp": "Leveling", "removexp": "Leveling", "leveling_setup": "Leveling",
    "rank": "Leveling", "leaderboard": "Leveling", "serveractivity": "Leveling",
    # Social (family / marriage / confession / relationship)
    "adopt": "Social", "disown": "Social", "divorce": "Social", "familytree": "Social",
    "gift": "Social", "marriage_setup": "Social", "marriagepro": "Social",
    "propose": "Social", "spouse": "Social", "love": "Social", "tree": "Social",
    "marriage marry": "Social", "marriage divorce": "Social", "marriage adopt": "Social",
    "marriage makeparent": "Social", "marriage runaway": "Social",
    "marriage partners": "Social", "marriage parent": "Social",
    "marriage children": "Social", "marriage tree": "Social",
    "marriage fulltree": "Social", "marriage relationship": "Social",
    "marriage familysize": "Social", "marriage disown": "Social",
    "marriage love": "Social", "marriage gift": "Social",
    "marriage profile": "Social", "marriage autoaccept": "Social",
    "marriage setup": "Social",
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

HELP_CAT_FALLBACK = {
    "Эдийн засаг": "Economy",
    "Түвшин": "Leveling",
    "Гэр бүл": "Social",
    "Тоглоом": "Games",
    "Модераци": "Moderation",
    "Админ": "Admin",
    "Хэрэгсэл": "Utility",
    "Бусад": "Utility",
    "Дэлгүүр": "Economy",
    "Даалгавар": "Utility",
    "Урилга": "Admin",
    "Giveaway": "Games",
    "Казино": "Games",
    "Хөгжилтэй": "Utility",
    "Нууц": "Social",
    "Хоол": "Economy",
    "Ticket": "Admin",
    "Automation": "Admin",
}

def load_help():
    src = open(HELP, encoding="utf-8-sig").read()
    tree = ast.parse(src)
    info = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "COMMAND_INFO":
                    info = ast.literal_eval(node.value)
        elif (
            info is not None and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "COMMAND_INFO"
            and node.value.func.attr == "update"
            and node.value.args
        ):
            info.update(ast.literal_eval(node.value.args[0]))
    if info is None:
        raise SystemExit("COMMAND_INFO not found")
    return info


def active_command_roots():
    """Read the active cog manifest and discover command roots without imports."""
    loader_tree = ast.parse(open(LOADER, encoding="utf-8-sig").read())
    active_cogs = set()
    for node in loader_tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "ACTIVE_COGS" for t in node.targets
        ):
            call = node.value
            if isinstance(call, ast.Call) and call.args:
                active_cogs = set(ast.literal_eval(call.args[0]))
    if not active_cogs:
        raise SystemExit("ACTIVE_COGS not found")

    roots = set()
    for cog in active_cogs:
        path = os.path.join(COGS_DIR, f"{cog}.py")
        tree = ast.parse(open(path, encoding="utf-8-sig").read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    call = dec if isinstance(dec, ast.Call) else None
                    fn = call.func if call else dec
                    if not isinstance(fn, ast.Attribute) or fn.attr not in {"command", "hybrid_command"}:
                        continue
                    name = node.name
                    if call:
                        for kw in call.keywords:
                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                name = kw.value.value
                    roots.add(name)
                    if isinstance(fn.value, ast.Name) and fn.value.id not in {"commands", "app_commands"}:
                        roots.add(fn.value.id)
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                fn = node.value.func
                if isinstance(fn, ast.Attribute) and fn.attr == "Group":
                    group_name = None
                    for kw in node.value.keywords:
                        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                            group_name = kw.value.value
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            roots.add(target.id)
                    if group_name:
                        roots.add(group_name)
    return roots

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
    active_roots = active_command_roots()
    info = {name: data for name, data in info.items() if name.split()[0] in active_roots}
    icons = existing_icons()

    missing = [
        n for n, d in info.items()
        if n not in WEB_CAT and d.get("category") not in HELP_CAT_FALLBACK
    ]
    if missing:
        raise SystemExit("Unmapped commands (add to WEB_CAT): " + ", ".join(missing))

    rows = []
    for name, d in info.items():
        wcat = WEB_CAT.get(name) or HELP_CAT_FALLBACK[d.get("category")]
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
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Command catalog (auto-generated from src/cogs/help.py COMMAND_INFO)
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
    backend_rows = [{k: v for k, v in row.items() if k != "_order"} for row in rows]
    with open(BACKEND_JSON, "w", encoding="utf-8") as fh:
        json.dump(backend_rows, fh, ensure_ascii=False, indent=4)
        fh.write("\n")
    print(f"Wrote {BACKEND_JSON} ({total} commands)")

if __name__ == "__main__":
    main()
