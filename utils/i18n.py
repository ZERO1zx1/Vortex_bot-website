# -*- coding: utf-8 -*-
"""
AETHER i18n — Монгол/Англи хоёр хэлтэй хариуны үсгийн сан.

Хэрэглээ:
    from utils.i18n import t, set_guild_lang, get_guild_lang

    embed.description = t(guild_id, "economy.daily.success", amount=amount)

Хэлний тохиргоо Supabase guild_config хүснэгтийн `lang` баганад хадгалагдана
(ANON key-ээр шууд бичиж уншина — bot_status-тэй ижил).
Хүснэгт байхгүй бол in-memory dictionary-д хадгалж бот restart хүртэл хэвээр үлдэнэ
(backend ажиллаж байгаа үед alдааны горим).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

SUPABASE_URL = "https://onpxpvemmjesobxpilgd.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ucHhwdmVtbWplc29ieHBpbGdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2ODQ2OTcsImV4cCI6MjEwMjI2MDY5N30."
    "Wh5O6JJLuYbykLBbfHSuvrj2-sC_AqlkWp0ix3X_jMk"
)

logger = logging.getLogger("aether.i18n")

DEFAULT_LANG = "mn"
SUPPORTED_LANGS = ("mn", "en")

# ── In-memory fallback cache ──────────────────────────────
_guild_lang_cache: Dict[str, str] = {}

# ── Text dictionaries ─────────────────────────────────────
# Формат: {key: {"mn": "...", "en": "..."}}
# Placeholder-ууд: {name} — Python str.format() ашиглана.
DICT: Dict[str, Dict[str, str]] = {
    # ============ CORE / LANG ============
    "core.lang_current": {"mn": "Энэ серверийн хэл одоо **{lang_mn}** байна.", "en": "This server's language is now **{lang_en}**."},
    "core.lang_changed": {"mn": "✅ Хэл **{new}** болж солигдлоо!", "en": "✅ Language changed to **{new}**!"},
    "core.lang_invalid": {"mn": "❌ Буруу хэл: `{given}`. Зөвхөн `mn` эсвэл `en` ашиглаарай.", "en": "❌ Invalid language: `{given}`. Use only `mn` or `en`."},
    "core.lang_no_perm": {"mn": "❌ Хэл солихын тулд серверийн удирдлагын эрх хэрэгтэй (Manage Server).", "en": "❌ You need Manage Server permission to change the language."},
    "core.lang_mn": {"mn": "Монгол", "en": "Mongolian"},
    "core.lang_en": {"mn": "Англи", "en": "English"},
    "core.lang_changed_note": {"mn": "Командын хариунууд одооноос энэ хэлээр ирнэ.", "en": "Command responses will now come in this language."},
    "core.not_setup": {"mn": "Энэ серверт бот тохируулагдаагүй байна.", "en": "This bot is not set up for this server."},

    # ============ ECONOMY ============
    "economy.balance.title": {"mn": "💳 Таны мөнгөн дүн", "en": "💳 Your balance"},
    "economy.balance.amount": {"mn": "Мөнгө: **{amount:,}** ₮", "en": "Money: **{amount:,}** ₮"},
    "economy.balance.position": {"mn": "Server-ийн жагсаалтад: **#{pos}**", "en": "Server rank: **#{pos}**"},
    "economy.daily.already": {"mn": "📅 Та дараагийн урамшуулалаа **{time_left}**-д авч болно.", "en": "📅 You can claim again in **{time_left}**."},
    "economy.daily.reward_field": {"mn": "💰 Шагнал", "en": "💰 Reward"},
    "economy.daily.footer": {"mn": "Дараагийн урамшуулал 24 цагийн дараа", "en": "Next reward in 24 hours"},
    "economy.daily.success": {"mn": "🎉 Та {amount:,} ₮ авлаа! Хөдөлмөрлөөд баяжина!", "en": "🎉 You received {amount:,} ₮! Work hard and get rich!"},
    "economy.daily.streak": {"mn": "🔥 Дараалсан өдрүүд: **{streak}**", "en": "🔥 Streak: **{streak}**"},
    "economy.work.success": {"mn": "💼 {job} ажил хийж **{amount:,}** ₮ оллоо!", "en": "💼 You worked as {job} and earned **{amount:,}** ₮!"},
    "economy.pay.success": {"mn": "💸 {target} рүү **{amount:,}** ₮ шилжүүллээ.", "en": "💸 Sent **{amount:,}** ₮ to {target}."},
    "economy.pay.no_money": {"mn": "❌ Таны мөнгө хүрэлцэхгүй байна.", "en": "❌ You don't have enough money."},
    "economy.pay.self": {"mn": "❌ Өөртөө мөнгө шилжүүлж болохгүй.", "en": "❌ You can't send money to yourself."},
    "economy.rob.success": {"mn": "🦹 {target}-с **{amount:,}** ₮ хулгайлсан!", "en": "🦹 You robbed **{amount:,}** ₮ from {target}!"},
    "economy.rob.caught": {"mn": "🚨 Савагдлаа! **{amount:,}** ₮ торгууль төллөө.", "en": "🚨 Caught! You paid **{amount:,}** ₮ fine."},
    "economy.rob.target_nope": {"mn": "❌ Энэ хүнээс мөнгө хулгайлах боломжгүй.", "en": "❌ Can't rob that user."},
    "economy.pay.negative": {"mn": "❌ Мөнгөн дүн эерэг байх ёстой.", "en": "❌ Amount must be positive."},

    # ============ GAMES ============
    "games.coinflip.title": {"mn": "🪙 Зоос шидэх", "en": "🪙 Coinflip"},
    "games.coinflip.win": {"mn": "🎉 {choice} таарлаа! **+{amount:,}** ₮ ялсан!", "en": "🎉 It's {choice}! You won **+{amount:,}** ₮!"},
    "games.coinflip.lose": {"mn": "😢 {result} таарлаа... **-{amount:,}** ₮ алдсан.", "en": "😢 It's {result}... You lost **-{amount:,}** ₮."},
    "games.dice.title": {"mn": "🎲 Шоо шидэх", "en": "🎲 Roll dice"},
    "games.dice.result": {"mn": "{user} **{roll}** дугаартай шоо гаргалаа!", "en": "{user} rolled a **{roll}**!"},
    "games.rps.title": {"mn": "✊ Чулуу-Цаас-Хайч", "en": "✊ Rock Paper Scissors"},
    "games.rps.win": {"mn": "🎉 {user} ялсан! ({me} vs {you})", "en": "🎉 {user} wins! ({me} vs {you})"},
    "games.rps.tie": {"mn": "🤝 Тэнцэж байна! ({me} vs {you})", "en": "🤝 It's a tie! ({me} vs {you})"},
    "games.rps.lose": {"mn": "😢 {user} ялагдсан... ({me} vs {you})", "en": "😢 {user} lost... ({me} vs {you})"},

    # ============ MARRIAGE ============
    "marriage.propose.title": {"mn": "💍 Гэрлэлтийн санал", "en": "💍 Marriage proposal"},
    "marriage.propose.ask": {"mn": "{author} нь {target}-д гэрлэлтийн санал тавьж байна!", "en": "{author} is proposing to {target}!"},
    "marriage.marry.success": {"mn": "💑 {a} ба {b} гэрлэлээ! Хайртай байгаарай!", "en": "💑 {a} and {b} are married! Love each other!"},
    "marriage.divorce.success": {"mn": "💔 Салалт амжилттай боллоо.", "en": "💔 Divorce successful."},
    "marriage.spouse.none": {"mn": "💔 Танд хань байхгүй. `A!propose @хүн` ашиглаарай!", "en": "💔 You have no spouse. Use `A!propose @user`!"},
    "marriage.spouse.info": {"mn": "💑 Таны хань: **{spouse}**", "en": "💑 Your spouse: **{spouse}**"},

    # ============ MODERATION ============
    "mod.ban.success": {"mn": "🔨 {target} серверээс банлагдлаа. Шалтгаан: {reason}", "en": "🔨 {target} was banned. Reason: {reason}"},
    "mod.kick.success": {"mn": "👢 {target} серверээс гаргагдлаа. Шалтгаан: {reason}", "en": "👢 {target} was kicked. Reason: {reason}"},
    "mod.warn.success": {"mn": "⚠️ {target}-д анхааруулга өглөө. Одоо нийт: **{count}**", "en": "⚠️ Warned {target}. Total warns: **{count}**"},
    "mod.timeout.success": {"mn": "⏱️ {target}-г {duration} хориглосон.", "en": "⏱️ {target} was timed out for {duration}."},
    "mod.timeout.no_perm": {"mn": "❌ Энэ хүнийг хориглох боломжгүй (дээд зэрэглэлийн гишүүн).", "en": "❌ Can't timeout that user (higher role)."},

    # ============ LEVELING ============
    "leveling.rank.title": {"mn": "🏅 Таны түвшин", "en": "🏅 Your rank"},
    "leveling.rank.info": {"mn": "Түвшин **{level}** · XP: **{xp:,}/{req:,}**\nServer-ийн жагсаалтад **#{pos}**", "en": "Level **{level}** · XP: **{xp:,}/{req:,}**\nServer rank **#{pos}**"},
    "leveling.levelup": {"mn": "🎉 Баяр хүргэе {user}! Түвшин **{level}** боллоо!", "en": "🎉 Congrats {user}! You reached level **{level}**!"},

    # ============ HELP ============
    "help.title": {"mn": "📜 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Тусламж", "en": "📜 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Help"},
    "help.footer": {"mn": "Дэлгэрэнгүй: A!help <команд>", "en": "More info: A!help <command>"},

    "common.jail.title": {"mn": '🚔 Шорон', "en": '🚔 Jail'},
    "common.jail.desc": {"mn": 'Та шоронд байна.', "en": 'You are in jail.'},
    "common.jail.cant_act": {"mn": '❌ Шоронд байхдаа энэ үйлдэл боломжгүй.', "en": "❌ You can't do that while in jail."},
    "common.jail.no_crime": {"mn": '❌ Шоронд гэмт хэрэг үйлдэх боломжгүй.', "en": "❌ You can't commit crimes in jail."},
    "common.jail.no_work": {"mn": '❌ Шоронгоос урамшуулал авах боломжгүй.', "en": "❌ You can't earn rewards from jail."},
    "common.jail.no_food": {"mn": '❌ Шоронд хоол захиалах боломжгүй.', "en": "❌ You can't order food in jail."},
    "common.jail.no_gift": {"mn": '❌ Шоронд бэлэг өгөх боломжгүй.', "en": "❌ You can't send gifts in jail."},
    "common.jail.no_play": {"mn": '❌ Шоронд тоглох боломжгүй.', "en": "❌ You can't play while in jail."},
    "common.hungry.title": {"mn": '🍔 Өлсөж байна!', "en": "🍔 You're hungry!"},
    "common.hungry.desc": {"mn": '`A!eat` командаар хоол идээрэй.', "en": 'Eat with `A!eat`.'},
    "common.angry.title": {"mn": '😡 Ууртай байна!', "en": "😡 You're angry!"},
    "common.angry.desc": {"mn": '`A!relax` командаар амраарай.', "en": 'Calm down with `A!relax`.'},
    "common.angry.no_play": {"mn": '😡 Ууртай үед тоглох боломжгүй! `A!relax` командаар амраарай.', "en": "😡 You can't play while angry! Use `A!relax` first."},
    "common.rest.title": {"mn": '⏳ АМРАЛТ', "en": '⏳ COOLDOWN'},
    "common.rest.desc": {"mn": '**{m}м {s}с** хүлээ.', "en": 'Wait **{m}m {s}s**.'},
    "common.missing_args": {"mn": '❌ Аргумент дутуу байна: `{usage}`', "en": '❌ Missing arguments: `{usage}`'},
    "common.bad_amount": {"mn": '❌ Мөнгөн дүн буруу байна. Эерэг тоо оруулна уу.', "en": '❌ Invalid amount. Enter a positive number.'},
    "common.not_found": {"mn": '❌ Олдсонгүй.', "en": '❌ Not found.'},
    "common.need_mention": {"mn": '❌ Хэрэглэгч дурдана уу (жишээ нь: `A!{cmd} @хүн`).', "en": '❌ Mention a user (e.g. `A!{cmd} @user`).'},
    "common.no_perm": {"mn": '❌ Энэ коммандыг ашиглах эрх байхгүй.', "en": "❌ You don't have permission to use this command."},
    "common.only_slash": {"mn": '❌ Энэ комманд зөвхөн `/` slash командаар ажиллана.', "en": '❌ This command only works as a slash `/` command.'},
    "common.cooldown": {"mn": '⏳ {time} хүлээгээрэй.', "en": '⏳ Please wait {time}.'},
    "common.success": {"mn": '✅ Амжилттай боллоо!', "en": '✅ Success!'},
    "help.not_found": {"mn": '❌ Тушаал олдсонгүй', "en": '❌ Command not found'},
    "help.not_found_desc": {"mn": '`{key}` нэртэй тушаал байхгүй байна.{hint}', "en": 'No command named `{key}`.{hint}'},

    # ============ STATUS ============
    "status.online": {"mn": "🟢 Online", "en": "🟢 Online"},
    "status.offline": {"mn": "🔴 Offline", "en": "🔴 Offline"},
    "status.title": {"mn": "Ботын төлөв", "en": "Bot status"},
}

# ── API ───────────────────────────────────────────────────

def t(guild_id: Any, key: str, mn: str = None, en: str = None, **kwargs: Any) -> str:
    """Хэлний сангаас үг авах (синхрон in-memory cache ашиглана).

    - DICT доторх түгээмэл текстүүд: t(ctx.guild.id, "economy.daily.success", amount=1000)
    - Нэг удаагийн inline текст: t(ctx.guild.id, "", mn="Монгол текст", en="English text")
      (ключ нь "" буюу байхгүй үед mn/en kwargs ашиглана)
    Хэл байхгүй бол DEFAULT_LANG (mn) рүү буцна, алдаа гарахгүй.
    Анхны Supabase уншилт async хийгдэх учир embed эхний удаад mn-ээр харагдаж,
    дараагийн дуудлаганд зөв хэлээр ирнэ (cache шинэчлэгдсэнээр).
    """
    lang = _guild_lang_cache.get(str(guild_id)) or DEFAULT_LANG if guild_id is not None else DEFAULT_LANG
    entry = DICT.get(key)
    if entry is None:
        # Inline backup: ключ байхгүй бол mn/en kwargs ашигла
        text = mn if lang == "mn" else (en or mn)
        if text is None:
            return key
    else:
        text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    try:
        if kwargs:
            text = text.format(**kwargs)
    except KeyError:
        pass
    return text


async def t_async(guild_id: Any, key: str, mn: str = None, en: str = None, **kwargs: Any) -> str:
    """Async хувилбар — Supabase-аас шинэ хэлийг уншиж аваад орчуулна (бүрэн зөв).
    Embed бичих газарт энэ нь илүү найдвартай."""
    lang = await get_guild_lang(guild_id)
    return _resolve(lang, key, mn, en, kwargs)


def _resolve(lang: str, key: str, mn: str, en: str, kwargs: dict) -> str:
    entry = DICT.get(key)
    if entry is None:
        text = mn if lang == "mn" else (en or mn)
        if text is None:
            return key
    else:
        text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    try:
        if kwargs:
            text = text.format(**kwargs)
    except KeyError:
        pass
    return text


def t_direct(lang: str, key: str, **kwargs: Any) -> str:
    """Заавал өгсөн хэлээр авах (хэрэглэгчийн хувийн хэл гэх мэт)."""
    entry = DICT.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    try:
        if kwargs:
            text = text.format(**kwargs)
    except KeyError:
        pass
    return text


async def get_guild_lang(guild_id: Any) -> str:
    """Supabase-аас серверийн хэлийг авах (in-memory cache-аар түрүүчилнэ)."""
    if guild_id is None:
        return DEFAULT_LANG
    gid = str(guild_id)
    if gid in _guild_lang_cache:
        return _guild_lang_cache[gid]
    try:
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(None, lambda: _sb_get_lang(gid))
        lang = row or DEFAULT_LANG
        _guild_lang_cache[gid] = lang
        return lang
    except Exception:  # network/schema алдаа → default
        return DEFAULT_LANG


async def set_guild_lang(guild_id: Any, lang: str) -> bool:
    """Серверийн хэлийг солих (guild_config.lang)."""
    if lang not in SUPPORTED_LANGS:
        return False
    gid = str(guild_id)
    _guild_lang_cache[gid] = lang
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _sb_set_lang(gid, lang))
        return True
    except Exception:
        logger.exception("i18n: guild_config.lang бичихэд алдаа (in-memory л хадгалагдав)")
        return True  # bot ажиллаж байхад cache-аар үргэлжлүүлнэ


# ── Supabase холболт (анон key, bot_status-тэй ижил горим) ─

def _sb_headers():
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _sb_get_lang(gid: str) -> Optional[str]:
    """guild_config хүснэгтийн lang баганыг унших. Багана байхгүй бол None."""
    try:
        import requests
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/guild_config?guild_id=eq.{gid}&select=lang",
            headers=_sb_headers(),
            timeout=8,
        )
        if r.status_code == 200:
            rows = r.json()
            if rows:
                return rows[0].get("lang")
        # Багана байхгүй (400/404) → хэвийн: анхны тохируулга хараахан хийгдээгүй
        return None
    except Exception:
        return None


def _sb_set_lang(gid: str, lang: str):
    """guild_config дээр lang багана шинэчлэх/нэмэх (upsert)."""
    try:
        import requests
        # Эхлээд мөр байгаа эсэхийг шалгах
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/guild_config?guild_id=eq.{gid}&select=guild_id",
            headers=_sb_headers(),
            timeout=8,
        )
        has_row = r.status_code == 200 and bool(r.json())
        if has_row:
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/guild_config?guild_id=eq.{gid}",
                headers=_sb_headers(),
                json={"lang": lang},
                timeout=8,
            )
        else:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/guild_config",
                headers=_sb_headers(),
                json={"guild_id": gid, "lang": lang},
                timeout=8,
            )
    except Exception:
        raise
