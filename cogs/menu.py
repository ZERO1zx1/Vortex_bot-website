"""📋 Interactive menu — Discord.py 2.x persistent view + UI components.

`A!menu` (text) болон `/menu` (slash) — анхны интерактив самбар илгээнэ.
Components:
  - Select menu: ангилал сонгох (1 мөр)
  - Prev / Next кноп: нэг ангилал доторх хуудас хооронд навигаци
  - "Тайлбар үзэх" кноп: сонгосон командыг дэлгэрэнгүй харна
  - "Хаах" кноп: самбарыг устгана
Persistent: cog_load-д add_view() хийснээр бот restart-д ч view handler
сэргэнэ (reconnect үед Discord өөрөө үлдэгдэл button даралтыг дамжуулна).
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

import discord
from discord import app_commands, ui
from discord.ext import commands

from cogs.help import COMMAND_INFO, CATEGORY_EMOJIS, CATEGORY_COLORS
from utils.branding import BOT_NAME, BOT_FOOTER
from utils.i18n import t_async, DEFAULT_LANG

# EN нэрийн харгалзаа (command-д харуулахын тулд)
CAT_EN = {
    "Эдийн засаг": "Economy", "Тоглоом": "Games", "Казино": "Casino",
    "Хөгжилтэй": "Fun", "Модераци": "Moderation", "Түвшин": "Levels",
    "Гэр бүл": "Family", "Админ": "Admin", "Хэрэгсэл": "Utility",
    "Хоол": "Food", "Дэлгүүр": "Shop", "Нууц": "Secret", "Даалгавар": "Quests",
}
CAT_MN = {v: k for k, v in CAT_EN.items()}

log = logging.getLogger("cogs.menu")

# Нэг хуудасанд харуулах командын тоо
CMDS_PER_PAGE = 10
# View-ийн timeout (секунд)
MENU_TIMEOUT = 300


# ─────────────────────────────────────────────────────────────────────
# Туслах функцүүд
# ─────────────────────────────────────────────────────────────────────

def _get_categories(lang: str) -> List[str]:
    """Бүх команд агуулсан ангилалуудыг хэлээр жагсаах."""
    keys = [c for c in CATEGORY_EMOJIS
            if any(i.get("category") == c for i in COMMAND_INFO.values())]
    if lang == "en":
        keys = [CAT_EN.get(k, k) for k in keys]
    return keys


def _mn_category(cat: str) -> str:
    """EN хэл дээрх нэрийг MN руу буцаах (COMMAND_INFO нь MN-ээр хадгална)."""
    return CAT_MN.get(cat, cat)


def _cmd_list(category_mn: str) -> List[str]:
    """Нэг ангиллын командуудыг COMMAND_INFO-оос цуглуулна."""
    return sorted(cmd for cmd, info in COMMAND_INFO.items()
                  if info.get("category") == category_mn)


def _total_pages(category_mn: str) -> int:
    n = len(_cmd_list(category_mn))
    return max(1, (n + CMDS_PER_PAGE - 1) // CMDS_PER_PAGE)


# ─────────────────────────────────────────────────────────────────────
# Interactive view (persistent — custom_id-тэй)
# ─────────────────────────────────────────────────────────────────────

class MenuView(ui.View):
    def __init__(
        self,
        original: discord.abc.User,
        guild_id: int,
        lang: str = DEFAULT_LANG,
        start_category: Optional[str] = None,
        page: int = 0,
        timeout: float = MENU_TIMEOUT,
    ) -> None:
        super().__init__(timeout=timeout)
        self.original = original
        self.guild_id = guild_id
        self.lang = lang
        self.category = start_category  # MN нэр (COMMAND_INFO-той ижил)
        self.page = page
        self._embed: Optional[discord.Embed] = None

    # ── interaction check ─────────────────────────────────────────────

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.original.id:
            await interaction.response.send_message(
                await t_async(self.guild_id, "", mn="⚠️ Энэ самбар зөвхөн танд зориулагдсан.",
                              en="⚠️ This panel belongs to someone else."),
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        """Timeout дуусахад бүх button-ыг идэвхгүй болгох."""
        try:
            for child in self.children:
                if isinstance(child, (ui.Button, ui.Select)):
                    child.disabled = True
            if self._embed is not None:
                footer_text = await t_async(
                    self.guild_id, "",
                    mn="Хугацаа дууссан — самбарыг дахин нээх: A!menu",
                    en="Timed out — reopen with: A!menu",
                )
                self._embed.set_footer(text=footer_text)
        except Exception:  # noqa: BLE001 — message аль хэдийн устсан байж болно
            log.debug("menu view timeout cleanup skipped", exc_info=True)

    # ── Embed ─────────────────────────────────────────────────────────

    async def _build_embed(self) -> discord.Embed:
        if self.category is None:
            # Анхны харагдац — ангилалын хураангуй
            title = await t_async(self.guild_id, "menu.title")
            desc_lines = []
            desc_lines.append(await t_async(
                self.guild_id, "menu.welcome",
                mn="Сайн байна уу! **{name}** ботын интерактив цэс рүү тавтай морил.\n\n"
                   "Доорх **Select menu**-аас ангилал сонгоод, командыг хуудсаар гүйлгэнэ үү.",
                en="Hi! Welcome to **{name}**'s interactive menu.\n\n"
                   "Pick a category from the **Select menu** below and page through its commands.",
                name=BOT_NAME,
            ))
            keys = _get_categories(self.lang)
            emoji_map = CATEGORY_EMOJIS
            line = " ".join(f"{emoji_map.get(_mn_category(k), '📁')} {k}" for k in keys[:12])
            desc_lines.append(line)
            desc_lines.append(await t_async(
                self.guild_id, "menu.total",
                mn="📊 Нийт **{count}** команд · **{cats}** ангилал",
                en="📊 **{count}** commands · **{cats}** categories",
                count=len(COMMAND_INFO),
                cats=len(keys),
            ))
            embed = discord.Embed(title=title, description="\n\n".join(desc_lines),
                                  color=0x89B4FA)
            embed.set_footer(text=BOT_FOOTER)
            self._embed = embed
            return embed

        emoji = CATEGORY_EMOJIS.get(self.category, "📁")
        color = CATEGORY_COLORS.get(self.category, 0x1E1E2F)
        cmds = _cmd_list(self.category)
        page_cmds = cmds[self.page * CMDS_PER_PAGE:(self.page + 1) * CMDS_PER_PAGE]
        title_key = "menu.cat_title"
        cat_label = self.category if self.lang == "mn" else CAT_EN.get(self.category, self.category)

        embed = discord.Embed(
            title=await t_async(self.guild_id, title_key,
                                mn="{emoji} {cat}", en="{emoji} {cat}",
                                emoji=emoji, cat=cat_label),
            color=color,
        )
        if not page_cmds:
            embed.description = await t_async(
                self.guild_id, "menu.no_commands",
                mn="📭 Энэ ангилалд команд байхгүй.",
                en="📭 No commands in this category.",
            )
        else:
            field_name = await t_async(
                self.guild_id, "menu.page",
                mn="📖 Хуудас {p}/{t}", en="📖 Page {p}/{t}",
                p=self.page + 1, t=_total_pages(self.category),
            )
            lines = []
            for cmd in page_cmds:
                info = COMMAND_INFO[cmd]
                desc = (info.get("description_" + self.lang)
                        or info.get("description_mn")
                        or info.get("description_en")
                        or "—")
                lines.append(f"{emoji} **`{cmd}`** — {desc[:90]}")
            embed.add_field(name=field_name, value="\n".join(lines) or "—", inline=False)

        stats = await t_async(
            self.guild_id, "menu.stats",
            mn="📊 {cat} ангилал · {n} команд · хуудас {p}/{t}",
            en="📊 {cat} · {n} cmds · page {p}/{t}",
            cat=cat_label, n=len(cmds), p=self.page + 1, t=_total_pages(self.category),
        )
        embed.set_footer(text=f"{BOT_FOOTER} · {stats}")
        self._embed = embed
        return embed

    # ── Select menu (row 0) ───────────────────────────────────────────

    @ui.select(
        cls=ui.Select,
        custom_id="menu_cat_select",
        row=0,
        placeholder="📂 Ангилал сонгоно уу / Choose a category",
        min_values=1,
        max_values=1,
    )
    async def category_select(self, interaction: discord.Interaction, sel: ui.StringSelect) -> None:
        chosen_mn = _mn_category(sel.values[0])
        self.category = chosen_mn
        self.page = 0
        await self._refresh(interaction)

    # ── Prev / Next (row 1) ───────────────────────────────────────────

    @ui.button(label="◀️", custom_id="menu_prev", style=discord.ButtonStyle.secondary,
               row=1, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, _btn: ui.Button) -> None:
        if self.category is None or self.page <= 0:
            return
        self.page -= 1
        await self._refresh(interaction)

    @ui.button(label="▶️", custom_id="menu_next", style=discord.ButtonStyle.secondary,
               row=1, disabled=True)
    async def next_button(self, interaction: discord.Interaction, _btn: ui.Button) -> None:
        if self.category is None:
            return
        if self.page + 1 >= _total_pages(self.category):
            return
        self.page += 1
        await self._refresh(interaction)

    # ── Detail (row 1) ────────────────────────────────────────────────

    @ui.button(label="📖 Тайлбар үзэх / Details", custom_id="menu_detail",
               style=discord.ButtonStyle.primary, row=1, disabled=True)
    async def detail_button(self, interaction: discord.Interaction, _btn: ui.Button) -> None:
        """Хуудасны эхний командыг дэлгэрэнгүй харуулна."""
        if self.category is None:
            return
        cmds = _cmd_list(self.category)
        if not cmds:
            return
        cmd = cmds[self.page * CMDS_PER_PAGE]
        info = COMMAND_INFO[cmd]
        desc = (info.get("description_" + self.lang)
                or info.get("description_mn")
                or info.get("description_en")
                or "—")
        examples = info.get("examples") or []
        usage = info.get("usage") or f"A!{cmd}"
        embed = discord.Embed(
            title=f"📖 {cmd}",
            description=desc,
            color=CATEGORY_COLORS.get(self.category, 0x1E1E2F),
        )
        embed.add_field(name=await t_async(self.guild_id, "menu.usage",
                                           mn="📌 Хэрэглээ", en="📌 Usage"),
                        value=f"`{usage}`", inline=False)
        if examples:
            embed.add_field(name=await t_async(self.guild_id, "menu.examples",
                                               mn="💡 Жишээ", en="💡 Examples"),
                            value="\n".join(f"`A!{e}`" for e in examples[:4]),
                            inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Close (row 1) ─────────────────────────────────────────────────

    @ui.button(label="🗑️ Хаах / Close", custom_id="menu_close",
               style=discord.ButtonStyle.danger, row=1)
    async def close_button(self, interaction: discord.Interaction, _btn: ui.Button) -> None:
        for child in self.children:
            if isinstance(child, (ui.Button, ui.Select)):
                child.disabled = True
        await interaction.response.edit_message(view=self)
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass

    # ── Refresh helper ────────────────────────────────────────────────

    async def _refresh(self, interaction: discord.Interaction) -> None:
        embed = await self._build_embed()
        has_pages = self.category is not None and _total_pages(self.category) > 1
        has_cmds = self.category is not None and bool(_cmd_list(self.category))
        at_end = (self.category is not None
                  and self.page + 1 >= _total_pages(self.category))
        for child in self.children:
            if isinstance(child, ui.Button):
                if child.custom_id == "menu_prev":
                    child.disabled = not has_pages or self.page <= 0
                elif child.custom_id == "menu_next":
                    child.disabled = not has_pages or at_end
                elif child.custom_id == "menu_detail":
                    child.disabled = not has_cmds
        await interaction.response.edit_message(embed=embed, view=self)


# ─────────────────────────────────────────────────────────────────────
# Cog
# ─────────────────────────────────────────────────────────────────────

class Menu(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        """Persistent view — бот restart/reconnect-д ч view handler сэргэнэ."""
        self.bot.add_view(MenuView(original=None, guild_id=0))  # type: ignore[arg-type]
        log.info("menu: persistent view registered")

    async def cog_unload(self) -> None:
        """Cog унтрахад view-г зогсоох (docs: extension teardown)."""
        self.bot.remove_view(MenuView(original=None, guild_id=0))  # type: ignore[arg-type]
        log.info("menu: persistent view unregistered")

    @commands.hybrid_command(name="menu", description="Интерактив цэс нээх")
    @app_commands.describe(category="Шууд нээх ангилал (хоосон бол хураангуй)")
    async def menu_command(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        category: Optional[str] = None,
    ) -> None:
        guild_id = ctx.guild.id if ctx.guild else 0
        if category is not None:
            category = _mn_category(category)
            if not _cmd_list(category):
                await ctx.send(
                    await t_async(guild_id, "", mn="❌ Тухайн ангилалд команд байхгүй.",
                                  en="❌ No commands in that category."),
                )
                return
        view = MenuView(original=ctx.author, guild_id=guild_id,
                        start_category=category)
        embed = await view._build_embed()
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Menu(bot))
