"""Interactive Modals — зөвхөн товч дарахад нээгдэнэ.

Дүрэм: `interaction.response.send_modal(...)`-ийг `defer()`-гүйгээр шууд
дуудна. Бүх DB/баланс шалгалтыг `on_submit()` дотор service дуудаж хийнэ.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import discord

from core.exceptions import AetherError, ValidationError
from ui.common.base import respond_error

AmountCallback = Callable[[discord.Interaction, str], Awaitable[None]]
TransferCallback = Callable[[discord.Interaction, int, str], Awaitable[None]]
BioCallback = Callable[[discord.Interaction, str], Awaitable[None]]


class _CallbackModal(discord.ui.Modal):
    def __init__(self, *, title: str) -> None:
        super().__init__(title=title)

    async def on_error(  # type: ignore[override]
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[Any],
    ) -> None:
        await respond_error(interaction, error)

    async def _invoke(self, interaction: discord.Interaction, **kwargs: Any) -> None:
        callback = getattr(self, "_callback", None)
        if callback is None:  # pragma: no cover — хүүхэд класс бүр тохируулна
            await respond_error(interaction, ValidationError())
            return
        try:
            await callback(interaction, **kwargs)
        except AetherError as exc:
            await respond_error(interaction, exc)


def _parse_user_id(raw: str) -> int:
    text = raw.strip()
    if text.startswith("<@") and text.endswith(">"):
        text = text[2:-1].lstrip("!&")
    if not text.isdigit():
        raise ValidationError("✦ Хэрэглэгчийн ID эсвэл mention бичнэ үү.")
    return int(text)


class AmountModal(_CallbackModal):
    """Ерөнхий дүн оруулах modal (deposit / withdraw / grant)."""

    def __init__(
        self,
        *,
        title: str,
        label: str,
        callback: AmountCallback,
        placeholder: str = "1000, 10k, all",
        default: str | None = None,
    ) -> None:
        super().__init__(title=title)
        self._callback = callback
        self.amount: discord.ui.TextInput[Any] = discord.ui.TextInput(
            label=label,
            placeholder=placeholder,
            default=default,
            min_length=1,
            max_length=32,
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._invoke(interaction, value=str(self.amount.value))


class TransferModal(_CallbackModal):
    """Хүлээн авагч болон дүнг нэг дор асуух modal."""

    def __init__(
        self,
        *,
        callback: TransferCallback,
        recipient: str | None = None,
    ) -> None:
        super().__init__(title="💸 Aether Transfer")
        self._callback = callback
        self.recipient: discord.ui.TextInput[Any] = discord.ui.TextInput(
            label="Хүлээн авагч (mention эсвэл ID)",
            placeholder="@Wanderer эсвэл 123456789012345678",
            default=recipient,
            min_length=1,
            max_length=32,
        )
        self.amount: discord.ui.TextInput[Any] = discord.ui.TextInput(
            label="Дүн",
            placeholder="1000, 10k, all",
            min_length=1,
            max_length=32,
        )
        self.add_item(self.recipient)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            recipient_id = _parse_user_id(str(self.recipient.value))
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        await self._invoke(
            interaction,
            recipient_id=recipient_id,
            value=str(self.amount.value),
        )


class BetModal(_CallbackModal):
    """Казиногийн бооцоо оруулах modal."""

    def __init__(
        self,
        *,
        game: str,
        callback: AmountCallback,
        minimum: int = 50,
        maximum: int = 250_000,
    ) -> None:
        super().__init__(title=f"🎰 {game} — Бооцоо")
        self._callback = callback
        self.amount: discord.ui.TextInput[Any] = discord.ui.TextInput(
            label="Бооцоо",
            placeholder=f"{minimum:,} – {maximum:,} эсвэл all",
            min_length=1,
            max_length=32,
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._invoke(interaction, value=str(self.amount.value))


class BuyQuantityModal(_CallbackModal):
    """Shop-оос хэдэн ширхэг авахыг асуух modal."""

    def __init__(
        self,
        *,
        item_name: str,
        callback: AmountCallback,
        price: int,
    ) -> None:
        super().__init__(title="🛒 Aether Shop")
        self._callback = callback
        self.quantity: discord.ui.TextInput[Any] = discord.ui.TextInput(
            label=f"{item_name} — тоо ширхэг",
            placeholder=f"1 ширхэг = {price:,} ⛃",
            default="1",
            min_length=1,
            max_length=3,
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._invoke(interaction, value=str(self.quantity.value))


class BioModal(_CallbackModal):
    """Профайлын bio засах modal."""

    def __init__(
        self,
        *,
        callback: BioCallback,
        current: str = "",
    ) -> None:
        super().__init__(title="📜 Aether Bio")
        self._callback = callback
        self.bio: discord.ui.TextInput[Any] = discord.ui.TextInput(
            label="Таны тухай",
            style=discord.TextStyle.paragraph,
            placeholder="Aether ертөнц дэх өөрийн түүхээ бичнэ үү...",
            default=current or None,
            max_length=200,
            required=False,
        )
        self.add_item(self.bio)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._invoke(interaction, value=str(self.bio.value or ""))
