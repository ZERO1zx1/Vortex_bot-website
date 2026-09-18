"""Smoke test for the UI-based A!trade flow (TradeBuilderView + modal + TradeView).

Loads cogs.shop, then drives the builder select/modal/send and the recipient
accept flow with fake ctx/interaction objects. No network, no login.
"""
import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import discord
from discord.ext import commands


class FakeMember:
    def __init__(self, uid):
        self.id = uid
        self.bot = False
        self.mention = f"<@{uid}>"
        self.display_name = "Tester"


class FakeGuild:
    id = 1


class FakeMsg:
    def __init__(self, id):
        self.id = id
        self.edited = {}
        self.view = None
        self.embed = None

    async def edit(self, **kw):
        self.edited = kw
        self.embed = kw.get("embed")
        self.view = kw.get("view")


class FakeResponse:
    def __init__(self):
        self.edited = None
        self.sent = None
        self.modal = None
        self.deferred = False

    async def defer(self, **kw):
        self.deferred = True

    async def edit_message(self, **kw):
        self.edited = kw

    async def send_message(self, *a, **kw):
        self.sent = (a, kw)

    async def send_modal(self, modal):
        self.modal = modal


class FakeFollowup:
    async def send(self, *a, **k):
        return None


class FakeInteraction:
    def __init__(self, user_id):
        self.user = FakeMember(user_id)
        self.guild_id = 1
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeCtx:
    def __init__(self, author_id):
        self.author = FakeMember(author_id)
        self.guild = FakeGuild()
        self.sent_msgs = []

    async def send(self, *a, **k):
        msg = FakeMsg(len(self.sent_msgs))
        self.sent_msgs.append((a, k))
        return msg


async def build_shop_cog(bot):
    """Construct ShopCog.__new__ with real sync helpers + stubbed db calls."""
    from src.cogs.shop import ShopCog
    cog = ShopCog.__new__(ShopCog)
    cog.bot = bot
    cog.pending_trades = {}
    cog._trade_counter = 0
    cog.max_inventory_slots = 50

    async def fake_inv(uid, guild_id):
        return {5: 2, 7: 10}

    async def fake_transfer(guild_id, from_id, to_id, item_id, quantity):
        return True

    cog.get_user_inventory = fake_inv
    cog.transfer_items = fake_transfer
    return cog


async def main():
    bot = commands.Bot(command_prefix="A!", intents=discord.Intents.default(), help_command=None)
    bot.loop = asyncio.get_running_loop()
    await bot.load_extension("src.cogs.shop")
    shop = bot.get_cog("ShopCog")

    async def _inv(uid, gid=None):
        return {5: 2, 7: 10}

    async def _transfer(guild_id, from_id, to_id, item_id, quantity):
        return True

    shop.get_user_inventory = _inv
    shop.transfer_items = _transfer
    shop.pending_trades = {}
    shop._trade_counter = 0

    auth = FakeInteraction(1)
    recip = FakeInteraction(2)
    ctx = FakeCtx(1)

    builder = shop.TradeBuilderView if hasattr(shop, "TradeBuilderView") else None
    root = __import__("src.cogs.shop", fromlist=["TradeBuilderView"])
    from src.cogs.shop import TradeBuilderView, TradeQuantityModal

    view = TradeBuilderView(shop, ctx, ctx.author, recip.user, {5: 2, 7: 10})
    assert view.send_btn.disabled is True, "send must start disabled"
    assert len(view.item_select.options) == 2

    # ---- select item 5 ----
    view.item_select._values = ["5"]
    await view.on_item_select(auth)
    assert view.item_id == 5 and view.item["name"], "item not selected"
    assert view.send_btn.disabled is True, "qty missing -> send disabled"

    # ---- select qty 2 ----
    view.qty_select._values = ["2"]
    await view.on_qty_select(auth)
    assert view.quantity == 2
    assert view.send_btn.disabled is False, "send must enable after item+qty"

    # ---- qty too high (owned only 2) ----
    view.qty_select._values = ["10"]
    await view.on_qty_select(auth)
    assert view.quantity == 2, "invalid qty must not override previous choice"

    # ---- custom qty via modal ----
    view.qty_select._values = ["custom"]
    await view.on_qty_select(auth)
    assert auth.response.modal is not None, "custom qty must open a modal"
    modal = auth.response.modal
    modal.qty_input._value = "1"
    await modal.on_submit(auth)
    assert view.quantity == 1, "modal qty not applied"
    assert view.send_btn.disabled is False

    # ---- send ----
    await view.on_send(auth)
    assert len(ctx.sent_msgs) == 1, "trade offer message not sent"
    assert auth.response.edited is not None, "builder msg not finalized"
    trade_id = shop.pending_trades.keys()
    assert list(trade_id), "trade not registered"
    tw = shop.pending_trades[1]
    assert tw.item_id == 5 and tw.quantity == 1 and tw.message is not None

    # ---- recipient accepts ----
    acc = FakeInteraction(2)
    await tw.accept.callback(acc)
    assert acc.response.edited is not None and "АМЖИЛТТАЙ" in acc.response.edited["embed"].title
    assert 1 not in shop.pending_trades, "accepted trade must be cleaned up"

    print("TRADE UI SMOKE TEST: ALL OK")
    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())