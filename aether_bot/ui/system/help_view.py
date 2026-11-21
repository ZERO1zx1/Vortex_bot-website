"""Help view — StringSelect категорий."""

from __future__ import annotations

from typing import Any

import discord

from ui.common.base import AetherView, refresh_panel
from ui.embeds import base_embed

CATEGORY_ORDER: tuple[str, ...] = (
    "economy",
    "rpg",
    "casino",
    "games",
    "system",
)

CATEGORY_TITLES: dict[str, str] = {
    "economy": "💠 Economy",
    "rpg": "🌌 RPG",
    "casino": "🎰 Casino",
    "games": "🎮 Games",
    "system": "🔧 System",
}

CATEGORY_COMMANDS: dict[str, list[tuple[str, str]]] = {
    "economy": [
        ("a!balance", "Wallet/Bank/Level олон горийг шинжлэх"),
        ("a!deposit", "Bank руу мөнгө шилжүүлэх"),
        ("a!withdraw", "Wallet руу буцаана"),
        ("a!transfer @user <Огтвор>", "Гаднаас мөнгө илгээнэ"),
        ("a!daily", "24цүүсийн хишиглах"),
        ("a!work", "Ажил хийлт"),
        ("a!crime <id>", "Гэмт хэрэг хийлт"),
        ("a!rob @user", "Хулгайлалт (Shield-ээр хамгаалагдвал)"),
        ("a!jail", "Шоронгийн статус"),
        ("a!bail", "Батлан даалтаар гарах"),
    ],
    "rpg": [
        ("a!profile [member]", "Профайл"),
        ("a!rank", "Түвшингийн хүлээлт"),
        ("a!leaderboard", "Ашгийн хүрсэн дээрх"),
        ("a!skills", "Skill tree"),
        ("a!upgrade <skill_id>", "SP ашиглан сайжруулах"),
        ("a!activate <skill_id>", "Active skill идэвхжүүлэх"),
        ("a!shop", "Домогт эд зүйлс"),
        ("a!buy <item_id> [тоо]", "Худалдаж авах"),
        ("a!inventory", "Inventory"),
        ("a!use <item_id>", "Item ашиглах"),
        ("a!equip <title_id>", "Title зүүх"),
    ],
    "casino": [
        ("a!slots [Бооцоо]", "Slots — 5 шугам"),
        ("a!blackjack [Бооцоо]", "Blackjack Hit/Stand/Double"),
        ("a!roulette [Бооцоо]", "Roulette — Red/Black/Even/Odd/Number"),
        ("a!minefield [Бооцоо]", "Minefield — 4×4 бөмбөг"),
        ("a!coinflip [Бооцоо] heads/tails", "Төлрүүлэх"),
        ("a!crash [Бооцоо]", "Crash — үржүүлэгч өсөх гүн"),
        ("a!lottery", "Сугалааны тасалбар"),
    ],
    "games": [
        ("a!duel @user <Бооцоо>", "1v1 паксал"),
        ("a!adventure", "Dungeon ажиллах"),
        ("a!hunt", "Мингян амжилттай"),
        ("a!fish", "Загас барьтай"),
        ("a!boss", "World Boss ажиллах"),
    ],
    "system": [
        ("a!help [category]", "Энэ мэдээлэл"),
        ("a!ping", "Ботын latency-г шалгана"),
        ("a!settings", "Guild тохиргоо (Нууцлалхүүдэд)"),
    ],
}


class HelpView(AetherView):
    def __init__(self, author_id: int, category: str = "economy") -> None:
        super().__init__(author_id, timeout=300.0)
        self.category = category
        self.category_select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="🗂️ Категори сонгох...",
            options=self._options(),
            custom_id="help_category",
        )
        self.category_select.callback = self._select  # type: ignore[method-assign]
        self.add_item(self.category_select)
        self._sync()

    def _options(self) -> list[discord.SelectOption]:
        return [
            discord.SelectOption(
                label=CATEGORY_TITLES[key],
                value=key,
                default=key == self.category,
            )
            for key in CATEGORY_ORDER
        ]

    def _sync(self) -> None:
        self.category_select.options = self._options()

    async def _select(self, interaction: discord.Interaction) -> None:
        self.category = self.category_select.values[0]
        self._sync()
        embed = help_embed(self.category)
        await refresh_panel(interaction, embed=embed, view=self)

    def select(self, category: str) -> None:
        self.category = category
        self._sync()


def help_embed(category: str) -> discord.Embed:
    title = CATEGORY_TITLES[category]
    lines = "\n".join(f"{cmd} — {desc}" for cmd, desc in CATEGORY_COMMANDS[category])
    embed = base_embed(
        f"{title} — Aether Commands",
        lines or "Команд нээгдээгүй.",
        color=0x8A2BE2,
    )
    return embed
