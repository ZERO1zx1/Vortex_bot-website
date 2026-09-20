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

from src.cogs.help import COMMAND_INFO, CATEGORY_EMOJIS, CATEGORY_COLORS
from src.utils.branding import ACCENT_COLOR, BOT_NAME, BOT_FOOTER, PRIMARY_COLOR, timestamp_now

# EN нэрийн харгалзаа (command-д харуулахын тулд)
log = logging.getLogger("cogs.menu")

# Нэг хуудасанд харуулах командын тоо
CMDS_PER_PAGE = 10
# View-ийн timeout (секунд)
MENU_TIMEOUT = 300


# ─────────────────────────────────────────────────────────────────────
# Туслах функцүүд
# ─────────────────────────────────────────────────────────────────────

def _get_categories() -> List[str]:
    """Бүх command агуулсан Монгол ангиллуудыг жагсаах."""
    return [c for c in CATEGORY_EMOJIS if any(i.get("category") == c for i in COMMAND_INFO.values())]


def _mn_category(cat: str) -> str:
    return cat


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
        start_category: Optional[str] = None,
        page: int = 0,
        timeout: float = MENU_TIMEOUT,
        persistent: bool = False,
    ) -> None:
        # Persistent (bootstrap) view: timeout=None бөгөөд бүх item нь custom_id-тэй
        # байх ёстой (discord.py add_view() шаардлага). Хэрэглэгчийн самбарын
        # timeout нь эцсийн embed/interaction-д хэрэглэгдэхгүй — view-г дахин
        # илгээх бүрд шинэ MenuView үүсгэгднэ.
        super().__init__(timeout=None if persistent else timeout)
        self.original = original
        self.guild_id = guild_id
        self.category = start_category  # MN нэр (COMMAND_INFO-той ижил)
        self.page = page
        self._embed: Optional[discord.Embed] = None
        self.category_select.options = self._build_select_options()

    # ── interaction check ─────────────────────────────────────────────

    def _build_select_options(self) -> List[discord.SelectOption]:
        options = []
        for cat in _get_categories():
            emoji = CATEGORY_EMOJIS.get(cat, "📁")
            options.append(discord.SelectOption(label=cat, emoji=emoji, value=cat))
        return options

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Persistent bootstrap view нь хэн ч "дарж" чадахгүй — энэ нь зөвхөн
        # reconnection үед Discord-оос ирэх үлдэгдэл даралтыг дамжуулах
        # handler болгон add_view() руу бүсэлэгдсэн view юм.
        if self.original is None:
            await interaction.response.defer()
            return False
        if interaction.user.id != self.original.id:
            await interaction.response.send_message("⚠️ Энэ самбар зөвхөн танд зориулагдсан.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        """Timeout дуусахад бүх button-ыг идэвхгүй болгох (persistent view-д хэрэглэгдэхгүй)."""
        try:
            for child in self.children:
                if isinstance(child, (ui.Button, ui.Select)):
                    child.disabled = True
            if self._embed is not None:
                self._embed.set_footer(text="Хугацаа дууссан — самбарыг дахин нээх: A!menu")
        except Exception:  # noqa: BLE001 — message аль хэдийн устсан байж болно
            log.debug("menu view timeout cleanup skipped", exc_info=True)

    # ── Embed ─────────────────────────────────────────────────────────

    async def _build_embed(self) -> discord.Embed:
        if self.category is None:
            # Анхны харагдац — ангилалын хураангуй
            desc_lines = []
            desc_lines.append(f"✦ **{BOT_NAME}** anime guild-ийн command archive-д тавтай морил.\n\nДоорх цэснээс ангиллаа сонгоод, адал явдлынхаа командыг нээгээрэй.")
            keys = _get_categories()
            emoji_map = CATEGORY_EMOJIS
            line = " ".join(f"{emoji_map.get(_mn_category(k), '📁')} {k}" for k in keys[:12])
            desc_lines.append(line)
            desc_lines.append(f"🌸 Нийт **{len(COMMAND_INFO)}** команд · **{len(keys)}** guild хэсэг")
            embed = discord.Embed(
                title=f"✦ {BOT_NAME} Command Archive",
                description="\n\n".join(desc_lines),
                color=PRIMARY_COLOR,
                timestamp=timestamp_now(),
            )
            embed.set_footer(text=f"{BOT_FOOTER} • Choose your path")
            self._embed = embed
            return embed

        emoji = CATEGORY_EMOJIS.get(self.category, "📁")
        color = CATEGORY_COLORS.get(self.category, 0x1E1E2F)
        cmds = _cmd_list(self.category)
        page_cmds = cmds[self.page * CMDS_PER_PAGE:(self.page + 1) * CMDS_PER_PAGE]
        title_key = "menu.cat_title"
        cat_label = self.category

        embed = discord.Embed(
            title=f"✦ {emoji} {cat_label} archive",
            color=color,
            timestamp=timestamp_now(),
        )
        if not page_cmds:
            embed.description = "📭 Энэ ангилалд команд байхгүй."
        else:
            field_name = f"📖 Хуудас {self.page + 1}/{_total_pages(self.category)}"
            lines = []
            for cmd in page_cmds:
                info = COMMAND_INFO[cmd]
                desc = (info.get("description_mn")
                        or info.get("description_en")
                        or "—")
                lines.append(f"{emoji} **`{cmd}`** — {desc[:90]}")
            embed.add_field(name=field_name, value="\n".join(lines) or "—", inline=False)

        stats = f"📊 {cat_label} ангилал · {len(cmds)} команд · хуудас {self.page + 1}/{_total_pages(self.category)}"
        embed.set_footer(text=f"{BOT_FOOTER} • {stats}")
        self._embed = embed
        return embed

    # ── Select menu (row 0) ───────────────────────────────────────────

    @ui.select(
        cls=ui.Select,
        custom_id="menu_cat_select",
        row=0,
        placeholder="🌸 Ангиллаа сонгоно уу / Choose your path",
        min_values=1,
        max_values=1,
    )
    async def category_select(self, interaction: discord.Interaction, sel: ui.Select) -> None:
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

    @ui.button(label="📖 Grimoire / Details", custom_id="menu_detail",
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
        desc = (info.get("description_mn")
                or info.get("description_en")
                or "—")
        examples = info.get("examples") or []
        usage = info.get("usage") or f"A!{cmd}"
        embed = discord.Embed(
            title=f"✦ {cmd} — Command Grimoire",
            description=desc,
            color=CATEGORY_COLORS.get(self.category, ACCENT_COLOR),
            timestamp=timestamp_now(),
        )
        embed.add_field(name="📌 Хэрэглээ",
                        value=f"`{usage}`", inline=False)
        if examples:
            embed.add_field(name="💡 Жишээ",
                            value="\n".join(f"`A!{e}`" for e in examples[:4]),
                            inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Close (row 1) ─────────────────────────────────────────────────

    @ui.button(label="🌙 Хаах / Close", custom_id="menu_close",
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
        self.persistent_view: Optional[MenuView] = None

    async def cog_load(self) -> None:
        """Persistent view — бот restart/reconnect-д ч view handler сэргэнэ.

        add_view() шаардлага: view timeout=None байх бөгөөд бүх item нь
        custom_id-тэй байх ёстой (MenuView-ийн бүх button/select custom_id-тэй).
        """
        self.persistent_view = MenuView(original=None, guild_id=0, persistent=True)
        self.bot.add_view(self.persistent_view)
        log.info("menu: persistent view registered")

    async def cog_unload(self) -> None:
        """Cog унтрахад view-г зогсоох (docs: extension teardown)."""
        if self.persistent_view is not None:
            self.persistent_view.stop()
            self.persistent_view = None
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
                    "❌ Тухайн ангилалд команд байхгүй.",
                )
                return
        view = MenuView(original=ctx.author, guild_id=guild_id,
                        start_category=category, timeout=MENU_TIMEOUT)
        embed = await view._build_embed()
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Menu(bot))
