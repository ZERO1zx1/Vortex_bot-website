"""Mock smoke test: games.py-г импортлоод бүх View класс, TRIVIA_QUESTIONS,
командууд зөв бүртгэгдсэн эсэхийг Discord gateway-гүйгээр баталгаажуулна."""
import sys
import os
import importlib.util
import types

# environment хуурамч утгаар тохируулна
os.environ.setdefault("DISCORD_TOKEN", "mock-token")
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-key")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Бусад модулиудыг mock/авах
config_manager = types.ModuleType("config_manager")
config_manager.load_config = lambda: {'prefix': '!', 'bonus_percent': 10}
sys.modules["config_manager"] = config_manager

utils_branding = types.ModuleType("utils.branding")
utils_branding.BOT_NAME = '𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹'
utils_branding.BOT_FOOTER = 'test'
utils_branding.footer_text = 'test'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
utils_pkg = types.ModuleType("utils")
utils_pkg.__path__ = []
sys.modules["utils"] = utils_pkg
sys.modules["utils.branding"] = utils_branding

utils_constants = types.ModuleType("utils.constants")
utils_constants.DEFAULT_PREFIX = '!'
utils_constants.EMBED_COLOR = 0x2b2d31
utils_constants.SUCCESS_COLOR = 0x57f287
utils_constants.ERROR_COLOR = 0xed4245
utils_constants.WARNING_COLOR = 0xfee75c
utils_constants.GOLD_COLOR = 0xfab387
utils_constants.INFO_COLOR = 0x3498db
sys.modules["utils.constants"] = utils_constants

def find_root(start: str):
    """Tools/ хавтасаас ажиллахэд ч project root-г олох: cogs/ байгаа хүртэл дээшээ өөрнө."""
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, "cogs")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.dirname(os.path.abspath(__file__))
        d = parent


base = find_root(__file__)
for util_name, filename in [("fonts", "utils/fonts.py"), ("supabase_cog", "utils/supabase_cog.py")]:
    path = os.path.join(base, filename)
    if os.path.exists(path):
        try:
            mod = load_module(path, f"utils.{util_name}")
            sys.modules[f"utils.{util_name}"] = mod
        except Exception as e:
            print(f"⚠ utils.{util_name} load skipped: {e}")

# Үндсэн тест
games_spec = importlib.util.spec_from_file_location("games", os.path.join(base, "cogs", "games.py"))
games = importlib.util.module_from_spec(games_spec)
sys.modules["games"] = games
games_spec.loader.exec_module(games)  # noqa: E402

errors = []

# 1. View классууд байгаа эсэх
expected_views = ["GambleView", "CoinflipView", "SlotsView", "RouletteView",
                  "DiceView", "RPSView", "NumberGuessView", "HighCardView", "CrashView"]
for name in expected_views:
    if not hasattr(games, name):
        errors.append(f"MISSING VIEW: {name}")
    else:
        print(f"  ✅ {name}")

# 2. TRIVIA_QUESTIONS
if not games.TRIVIA_QUESTIONS:
    errors.append("MISSING TRIVIA_QUESTIONS")
else:
    print(f"  ✅ TRIVIA_QUESTIONS: {len(games.TRIVIA_QUESTIONS)} асуулт")

# 3. Cog командууд бүртгэгдсэн эсэх
cmd_names = [c.name for c in games.Games.__cog_commands__]
expected_cmds = ["gamble", "coinflipgame", "slot", "roulettegame", "dice", "rps",
                 "numberguess", "highcard", "crash", "trivia", "gamestats"]
for cmd in expected_cmds:
    if cmd not in cmd_names:
        errors.append(f"MISSING COMMAND: {cmd}")
    else:
        print(f"  ✅ /{cmd}")

# 4. Games Cog үүсэх боломжтой эсэх (mock bot-оор)
import discord  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

mock_bot = MagicMock()
mock_bot.config = {"bonus_percent": 10}
try:
    cog = games.Games(mock_bot)
    print("  ✅ Games Cog instance үүсгэгдлээ")
except Exception as e:
    errors.append(f"Cog init failed: {e}")

# 5. View-үүд Discord UI-тай нийцэж байгаа эсэх (mock ctx-ээр бүтээх)
# discord.py >= 2.4: View.__init__ нь asyncio.get_running_loop() шаарддаг тул
# View үүсгэх заавал ажиллаж буй event loop дотор хийгдэнэ (бот дээр async
# команд дотор үүсдэгтэй ижил нөхцөл).
import asyncio  # noqa: E402
from discord.ext import commands  # noqa: E402

mock_ctx = MagicMock(spec=commands.Context)
mock_ctx.author.id = 12345


async def _build_views():
    for cls, args in [(games.GambleView, (cog, mock_ctx, 1000)),
                      (games.CoinflipView, (cog, mock_ctx, 1000)),
                      (games.SlotsView, (cog, mock_ctx, 1000)),
                      (games.RouletteView, (cog, mock_ctx, 1000)),
                      (games.DiceView, (cog, mock_ctx, 1000)),
                      (games.RPSView, (cog, mock_ctx, 1000)),
                      (games.NumberGuessView, (cog, mock_ctx, 1000, 5)),
                      (games.HighCardView, (mock_ctx, cog, 1000)),
                      (games.CrashView, (cog, mock_ctx, 1000))]:
        try:
            v = cls(*args)
            print(f"  ✅ {cls.__name__} бүтээгдлээ, {len(v.children)} товчлууртай")
        except Exception as e:
            errors.append(f"{cls.__name__} init failed: {e}")


asyncio.run(_build_views())

if errors:
    print("\n❌ АЛДААНУУД:")
    for e in errors:
        print(f"   - {e}")
    sys.exit(1)

print("\n🎉 БҮГД ЗӨВ! Smoke test амжилттай.")
