import asyncio
import itertools
import logging
import random
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone

import discord
from discord.ext import commands

from src.utils.constants import (
    GOLD_COLOR,
)

logger = logging.getLogger(__name__)

MIN_BUY_IN = 100
MAX_BUY_IN = 1_000_000
MIN_PLAYERS = 2
MAX_PLAYERS = 6
MAX_RAISES = 3
SUITS = ("♠", "♥", "♦", "♣")
RANK_LABELS = {11: "J", 12: "Q", 13: "K", 14: "A"}
HAND_NAMES = (
    "High Card", "One Pair", "Two Pair", "Three of a Kind", "Straight",
    "Flush", "Full House", "Four of a Kind", "Straight Flush",
)


def card_text(card):
    rank, suit = card
    return f"{RANK_LABELS.get(rank, rank)}{suit}"


def evaluate_five(cards):
    ranks = sorted((rank for rank, _ in cards), reverse=True)
    counts = {rank: ranks.count(rank) for rank in set(ranks)}
    groups = sorted(((count, rank) for rank, count in counts.items()), reverse=True)
    flush = len({suit for _, suit in cards}) == 1
    unique = sorted(set(ranks), reverse=True)
    if 14 in unique:
        unique.append(1)
    straight_high = next(
        (unique[i] for i in range(len(unique) - 4)
         if unique[i] - unique[i + 4] == 4),
        None,
    )
    if flush and straight_high:
        return (8, straight_high)
    if groups[0][0] == 4:
        four = groups[0][1]
        kicker = max(rank for rank in ranks if rank != four)
        return (7, four, kicker)
    if groups[0][0] == 3 and len(groups) > 1 and groups[1][0] >= 2:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *ranks)
    if straight_high:
        return (4, straight_high)
    if groups[0][0] == 3:
        triple = groups[0][1]
        kickers = sorted((rank for rank in ranks if rank != triple), reverse=True)
        return (3, triple, *kickers)
    pairs = sorted((rank for rank, count in counts.items() if count == 2), reverse=True)
    if len(pairs) >= 2:
        kicker = max(rank for rank in ranks if rank not in pairs[:2])
        return (2, pairs[0], pairs[1], kicker)
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = sorted((rank for rank in ranks if rank != pair), reverse=True)
        return (1, pair, *kickers)
    return (0, *ranks)


def best_hand(cards):
    if len(cards) < 5:
        raise ValueError("At least five cards are required")
    score = max(evaluate_five(combo) for combo in itertools.combinations(cards, 5))
    return score, HAND_NAMES[score[0]]


@dataclass
class PokerPlayer:
    member: object
    cards: list = field(default_factory=list)
    chips: int = 0
    round_bet: int = 0
    committed: int = 0
    folded: bool = False
    all_in: bool = False

    @property
    def id(self):
        return self.member.id


class TexasHoldemGame:
    def __init__(self, host, buy_in: int):
        self.host_id = host.id
        self.buy_in = buy_in
        self.small_blind = max(1, buy_in // 100)
        self.big_blind = max(2, buy_in // 50)
        self.raise_size = self.big_blind
        self.players = [PokerPlayer(host)]
        self.stage = "lobby"
        self.deck = []
        self.community = []
        self.dealer_index = 0
        self.turn_index = 0
        self.current_bet = 0
        self.raises = 0
        self.acted = set()
        self.finished = False
        self.settled = False
        self.funded = False

    @property
    def active_players(self):
        return [player for player in self.players if not player.folded]

    @property
    def betting_players(self):
        return [player for player in self.players if not player.folded and not player.all_in]

    @property
    def current_player(self):
        return self.players[self.turn_index] if self.stage != "lobby" else None

    @property
    def pot(self):
        return sum(player.committed for player in self.players)

    def add_player(self, member):
        if self.stage != "lobby" or len(self.players) >= MAX_PLAYERS:
            return False
        if any(player.id == member.id for player in self.players):
            return False
        self.players.append(PokerPlayer(member))
        return True

    def remove_player(self, user_id: int):
        if self.stage != "lobby" or user_id == self.host_id:
            return None
        player = next((p for p in self.players if p.id == user_id), None)
        if player:
            self.players.remove(player)
        return player

    def start(self):
        if self.stage != "lobby" or len(self.players) < MIN_PLAYERS:
            return False
        self.deck = [(rank, suit) for rank in range(2, 15) for suit in SUITS]
        random.shuffle(self.deck)
        for player in self.players:
            player.cards = [self.deck.pop(), self.deck.pop()]
            player.chips = self.buy_in
        self.stage = "preflop"
        small = (self.dealer_index + 1) % len(self.players)
        big = (self.dealer_index + 2) % len(self.players)
        self._commit(self.players[small], self.small_blind)
        self._commit(self.players[big], self.big_blind)
        self.current_bet = self.big_blind
        self.turn_index = (big + 1) % len(self.players)
        return True

    def _commit(self, player: PokerPlayer, amount: int):
        if amount < 0 or amount > player.chips:
            raise ValueError("Invalid chip commitment")
        player.chips -= amount
        player.round_bet += amount
        player.committed += amount
        if player.chips == 0:
            player.all_in = True

    def act(self, user_id: int, action: str):
        if self.finished or self.stage == "lobby":
            return {"error": "Тоглолт идэвхгүй байна."}
        player = self.current_player
        if player.id != user_id:
            return {"error": "Одоо таны ээлж биш байна."}
        need = self.current_bet - player.round_bet
        if action == "fold":
            player.folded = True
            self.acted.add(player.id)
        elif action == "call":
            # A short call is an all-in; side-pot settlement keeps it fair.
            self._commit(player, min(need, player.chips))
            self.acted.add(player.id)
        elif action == "raise":
            if self.raises >= MAX_RAISES:
                return {"error": "Энэ street-ийн raise хязгаарт хүрсэн."}
            amount = need + self.raise_size
            if amount > player.chips:
                return {"error": "Raise хийх chip хүрэлцэхгүй. CHECK/CALL дарж all-in хийнэ үү."}
            self._commit(player, amount)
            self.current_bet += self.raise_size
            self.raises += 1
            self.acted = {player.id}
        else:
            return {"error": "Буруу үйлдэл."}

        if len(self.active_players) == 1:
            self.finished = True
            self.stage = "showdown"
            return {"status": "finished", "reason": "fold"}
        if len(self.betting_players) <= 1 and any(p.all_in for p in self.active_players):
            self.complete_board()
            return {"status": "finished", "reason": "all_in"}
        if self._round_complete():
            self._advance_stage()
            if self.stage == "showdown":
                self.finished = True
                return {"status": "finished", "reason": "showdown"}
            return {"status": "next_stage"}
        self._advance_turn()
        return {"status": "continue"}

    def _round_complete(self):
        active = self.active_players
        return all(
            p.all_in or (p.id in self.acted and p.round_bet == self.current_bet)
            for p in active
        )

    def _advance_turn(self):
        for offset in range(1, len(self.players) + 1):
            index = (self.turn_index + offset) % len(self.players)
            if not self.players[index].folded and not self.players[index].all_in:
                self.turn_index = index
                return True
        return False

    def _advance_stage(self):
        order = ("preflop", "flop", "turn", "river", "showdown")
        self.stage = order[order.index(self.stage) + 1]
        if self.stage == "flop":
            self.community.extend((self.deck.pop(), self.deck.pop(), self.deck.pop()))
        elif self.stage in ("turn", "river"):
            self.community.append(self.deck.pop())
        for player in self.players:
            player.round_bet = 0
        self.current_bet = 0
        self.raises = 0
        self.acted.clear()
        if self.stage != "showdown":
            self.turn_index = self.dealer_index
            self._advance_turn()

    def complete_board(self):
        while len(self.community) < 5:
            self.community.append(self.deck.pop())
        self.stage = "showdown"
        self.finished = True

    def winners(self):
        active = self.active_players
        if len(active) == 1:
            return active, None
        scored = [(best_hand(player.cards + self.community)[0], player) for player in active]
        top = max(score for score, _ in scored)
        return [player for score, player in scored if score == top], HAND_NAMES[top[0]]

    def payout_plan(self):
        """Return conserved payouts: remaining stacks plus main/side pots."""
        payouts = {player.id: player.chips for player in self.players}
        active = self.active_players
        if len(active) == 1:
            payouts[active[0].id] += self.pot
            return payouts

        levels = sorted({player.committed for player in self.players if player.committed > 0})
        previous = 0
        for level in levels:
            contributors = [player for player in self.players if player.committed >= level]
            side_pot = (level - previous) * len(contributors)
            eligible = [player for player in contributors if not player.folded]
            if not eligible:
                share, remainder = divmod(side_pot, len(contributors))
                for index, contributor in enumerate(contributors):
                    payouts[contributor.id] += share + (remainder if index == 0 else 0)
                previous = level
                continue
            scores = [(best_hand(player.cards + self.community)[0], player) for player in eligible]
            top = max(score for score, _ in scores)
            winners = [player for score, player in scores if score == top]
            share, remainder = divmod(side_pot, len(winners))
            for index, winner in enumerate(winners):
                payouts[winner.id] += share + (remainder if index == 0 else 0)
            previous = level
        return payouts


class TexasPokerView(discord.ui.View):
    def __init__(self, cog, ctx, game: TexasHoldemGame):
        super().__init__(timeout=180)
        self.cog = cog
        self.bot = cog.bot
        self.ctx = ctx
        self.game = game
        self.message = None
        self._lock = asyncio.Lock()
        self._sync_buttons()

    def _sync_buttons(self):
        lobby = self.game.stage == "lobby"
        self.join.disabled = not lobby or len(self.game.players) >= MAX_PLAYERS
        self.leave.disabled = not lobby
        self.start_button.disabled = not lobby or len(self.game.players) < MIN_PLAYERS
        self.fold.disabled = lobby or self.game.finished
        self.call.disabled = lobby or self.game.finished
        self.raise_button.disabled = lobby or self.game.finished
        self.cards.disabled = lobby or self.game.finished
        self.retry_payout.disabled = lobby or not self.game.finished or self.game.settled
        if not lobby and not self.game.finished:
            need = self.game.current_bet - self.game.current_player.round_bet
            self.call.label = "CHECK" if need == 0 else f"CALL {need}"
        else:
            self.call.label = "CHECK / CALL"
        self.raise_button.label = f"RAISE +{self.game.raise_size:,}"

    def build_embed(self, note=""):
        title = "♠️ TEXAS HOLD'EM — AETHER TABLE"
        embed = discord.Embed(title=title, color=GOLD_COLOR, timestamp=datetime.now(timezone.utc))
        if self.game.stage == "lobby":
            names = "\n".join(f"{i + 1}. {p.member.mention}" for i, p in enumerate(self.game.players))
            embed.description = (
                f"**Buy-in:** {self.game.buy_in:,} мөнгө • **Players:** {len(self.game.players)}/{MAX_PLAYERS}\n"
                f"Host Start дарахад тоглолт эхэлнэ.\n\n{names}"
            )
        else:
            board = " ".join(card_text(card) for card in self.game.community) or "_Community card гараагүй_"
            player_lines = []
            for player in self.game.players:
                if player.folded:
                    state = f"❌ Fold • 🪙 {player.chips}"
                elif player.all_in:
                    state = "🔥 ALL-IN"
                else:
                    state = f"🪙 {player.chips}"
                pointer = "👉 " if self.game.current_player is player and not self.game.finished else ""
                player_lines.append(f"{pointer}{player.member.display_name}: {state}")
            embed.description = (
                f"**Stage:** {self.game.stage.upper()} • **Prize pot:** {self.game.pot:,}\n"
                f"**Current bet:** {self.game.current_bet:,} • Raises: {self.game.raises}/{MAX_RAISES}\n\n"
                f"**Board:** {board}\n\n" + "\n".join(player_lines)
            )
        if note:
            embed.add_field(name="📣 Table", value=note, inline=False)
        embed.set_footer(text="MY CARDS товчоор зөвхөн өөрийн картаа харна")
        return embed

    async def _edit(self, interaction, note=""):
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.build_embed(note), view=self)

    @discord.ui.button(label="JOIN", emoji="➕", style=discord.ButtonStyle.success, row=0)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._lock:
            if self.game.stage != "lobby":
                return await interaction.response.send_message("Тоглолт эхэлсэн.", ephemeral=True)
            if any(p.id == interaction.user.id for p in self.game.players):
                return await interaction.response.send_message("Та ширээнд аль хэдийн орсон.", ephemeral=True)
            if len(self.game.players) >= MAX_PLAYERS:
                return await interaction.response.send_message("Ширээ дүүрсэн.", ephemeral=True)
            restriction = await self.cog.player_restriction(interaction.user, interaction.guild_id)
            if restriction:
                return await interaction.response.send_message(restriction, ephemeral=True)
            economy = self.bot.get_cog("Economy")
            balance = await economy.get_balance(interaction.user.id, interaction.guild_id)
            if balance < self.game.buy_in:
                return await interaction.response.send_message("Buy-in хүрэлцэхгүй байна.", ephemeral=True)
            self.game.add_player(interaction.user)
            await self._edit(interaction, f"{interaction.user.mention} ширээнд орлоо.")

    @discord.ui.button(label="LEAVE", emoji="↩️", style=discord.ButtonStyle.secondary, row=0)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._lock:
            player = self.game.remove_player(interaction.user.id)
            if player is None:
                return await interaction.response.send_message("Host гарах боломжгүй эсвэл та ширээнд алга.", ephemeral=True)
            await self._edit(interaction, f"{interaction.user.mention} ширээнээс гарлаа.")

    @discord.ui.button(label="START", emoji="▶️", style=discord.ButtonStyle.primary, row=0)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._lock:
            if interaction.user.id != self.game.host_id:
                return await interaction.response.send_message("Зөвхөн host эхлүүлнэ.", ephemeral=True)
            if self.game.stage != "lobby" or self.game.funded:
                return await interaction.response.send_message("Тоглолт аль хэдийн эхэлсэн.", ephemeral=True)
            if len(self.game.players) < MIN_PLAYERS:
                return await interaction.response.send_message("Хамгийн багадаа 2 тоглогч хэрэгтэй.", ephemeral=True)
            channel_lock = self.cog.channel_locks.setdefault(
                self.ctx.channel.id, asyncio.Lock()
            )
            try:
                async with channel_lock:
                    pending = await self.cog._pending_rows(
                        self.ctx.channel.id, interaction.guild_id
                    )
            except Exception:
                logger.exception("texas start pending-payout check failed")
                return await interaction.response.send_message(
                    "Pending payout шалгаж чадсангүй. Migration 002 болон DB холболтыг шалгана уу.",
                    ephemeral=True,
                )
            if pending:
                self.cog._set_channel_cache(self.ctx.channel.id, pending)
                return await interaction.response.send_message(
                    "Энэ сувагт өмнөх pending payout байна. Host `A!pokerclaim` ашиглана уу.",
                    ephemeral=True,
                )
            economy = self.bot.get_cog("Economy")
            for player in self.game.players:
                restriction = await self.cog.player_restriction(player.member, interaction.guild_id)
                if restriction:
                    return await interaction.response.send_message(
                        f"{player.member.mention}: {restriction}", ephemeral=True
                    )
                balance = await economy.get_balance(player.id, interaction.guild_id)
                if balance < self.game.buy_in:
                    return await interaction.response.send_message(
                        f"{player.member.mention}-ийн buy-in хүрэлцэхгүй байна.", ephemeral=True
                    )
            try:
                await self.bot.db_manager.rpc(
                    "begin_poker_table",
                    {
                        "p_channel_id": str(self.ctx.channel.id),
                        "p_guild_id": str(interaction.guild_id),
                    },
                )
                for player in self.game.players:
                    await self.bot.db_manager.rpc(
                        "charge_poker_buyin",
                        {
                            "p_channel_id": str(self.ctx.channel.id),
                            "p_guild_id": str(interaction.guild_id),
                            "p_user_id": str(player.id),
                            "p_host_id": str(self.game.host_id),
                            "p_amount": int(self.game.buy_in),
                        },
                    )
            except Exception:
                logger.exception("texas poker buy-in collection failed")
                try:
                    refund_rows = await self.cog._pending_rows(
                        self.ctx.channel.id, interaction.guild_id
                    )
                except Exception:
                    logger.exception("Operation failed in start_button")
                    refund_rows = None
                refunded = not refund_rows
                if refund_rows:
                    refunded = await self.cog.process_payouts(
                        channel_id=self.ctx.channel.id,
                        guild_id=interaction.guild_id,
                        host_id=self.game.host_id,
                        plan=None,
                        prefer_pending=True,
                    )
                self.cog.active_channels.pop(self.ctx.channel.id, None)
                self.stop()
                for child in self.children:
                    child.disabled = True
                message = "⚠️ Buy-in цуглуулахад алдаа гарлаа. Тоглолт эхлээгүй."
                if refund_rows is None or not refunded:
                    message += " Pending refund байна; host `A!pokerclaim` ашиглана уу."
                return await interaction.response.send_message(
                    message, ephemeral=True
                )
            self.game.funded = True
            self.game.start()
            await self._edit(interaction, f"Карт тараалаа. {self.game.current_player.member.mention}-ийн ээлж.")

    @discord.ui.button(label="MY CARDS", emoji="🃏", style=discord.ButtonStyle.secondary, row=1)
    async def cards(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = next((p for p in self.game.players if p.id == interaction.user.id), None)
        if player is None or self.game.stage == "lobby":
            return await interaction.response.send_message("Та энэ тоглолтод байхгүй.", ephemeral=True)
        cards = " ".join(card_text(card) for card in player.cards)
        await interaction.response.send_message(f"Таны карт: **{cards}**", ephemeral=True)

    @discord.ui.button(label="FOLD", emoji="🏳️", style=discord.ButtonStyle.danger, row=1)
    async def fold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._action(interaction, "fold")

    @discord.ui.button(label="CHECK / CALL", emoji="✅", style=discord.ButtonStyle.success, row=1)
    async def call(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._action(interaction, "call")

    @discord.ui.button(label="RAISE", emoji="📈", style=discord.ButtonStyle.primary, row=1)
    async def raise_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._action(interaction, "raise")

    @discord.ui.button(label="RETRY PAYOUT", emoji="🔄", style=discord.ButtonStyle.secondary, row=2)
    async def retry_payout(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._lock:
            if interaction.user.id != self.game.host_id:
                return await interaction.response.send_message("Зөвхөн host payout retry хийнэ.", ephemeral=True)
            complete = await self._settle()
            note = self._result_text()
            if not complete:
                note += "\n⚠️ Зарим payout амжилтгүй хэвээр байна."
            await self._edit(interaction, note)

    async def _action(self, interaction, action):
        async with self._lock:
            result = self.game.act(interaction.user.id, action)
            if "error" in result:
                return await interaction.response.send_message(result["error"], ephemeral=True)
            if result["status"] == "finished":
                complete = await self._settle()
                note = self._result_text()
                if not complete:
                    note += "\n⚠️ Зарим payout түр амжилтгүй боллоо. Host RETRY PAYOUT дарна уу."
                return await self._edit(interaction, note)
            note = f"{interaction.user.display_name}: **{action.upper()}**"
            if result["status"] == "next_stage":
                note += f" • {self.game.stage.upper()} эхэллээ"
            note += f" • {self.game.current_player.member.mention}-ийн ээлж"
            await self._edit(interaction, note)

    def _result_text(self):
        winners, hand_name = self.game.winners()
        payout_by_id = self.game.payout_plan()
        top_paid = max(payout_by_id.values())
        top_earners = [
            player for player in self.game.players
            if payout_by_id.get(player.id, 0) == top_paid
        ]
        names = ", ".join(player.member.mention for player in top_earners)
        cards = " ".join(card_text(card) for card in self.game.community)
        result = f"🏆 Biggest cash-out: {names} • Committed pot: **{self.game.pot:,}**"
        if hand_name:
            hand_winners = ", ".join(player.member.display_name for player in winners)
            result += f"\nBest hand: **{hand_name}** — {hand_winners}"
        if cards:
            result += f"\nBoard: {cards}"
        if len(self.game.community) == 5:
            reveals = []
            for player in self.game.active_players:
                hole = " ".join(card_text(card) for card in player.cards)
                _, player_hand = best_hand(player.cards + self.game.community)
                reveals.append(f"{player.member.display_name}: {hole} — {player_hand}")
            result += "\n" + "\n".join(reveals)
        cashouts = [
            f"{player.member.display_name}: **{payout_by_id.get(player.id, 0):,}**"
            for player in self.game.players
            if payout_by_id.get(player.id, 0) > 0
        ]
        result += "\n💰 Cash-out: " + " • ".join(cashouts)
        return result

    async def _settle(self):
        if self.game.settled:
            return True
        plan = list(self.game.payout_plan().items())
        if not await self.cog.process_payouts(
            channel_id=self.ctx.channel.id,
            guild_id=self.ctx.guild.id,
            host_id=self.game.host_id,
            plan=plan,
            prefer_pending=True,
            replace_pending=True,
        ):
            return False
        self.game.settled = True
        for child in self.children:
            child.disabled = True
        self.cog.active_channels.pop(self.ctx.channel.id, None)
        self.stop()
        return True

    async def _process_payouts(self, plan, *, prefer_pending):
        return await self.cog.process_payouts(
            channel_id=self.ctx.channel.id,
            guild_id=self.ctx.guild.id,
            host_id=self.game.host_id,
            plan=plan,
            prefer_pending=prefer_pending,
        )

    async def _refund_all(self):
        if self.game.settled:
            return True
        if self.game.funded:
            plan = [(player.id, self.game.buy_in) for player in self.game.players]
            if not await self._process_payouts(plan, prefer_pending=False):
                return False
        self.game.settled = True
        self.cog.active_channels.pop(self.ctx.channel.id, None)
        return True

    async def on_timeout(self):
        async with self._lock:
            if self.game.settled:
                return
            if self.game.stage == "lobby":
                complete = await self._refund_all()
                note = "⏰ Lobby timeout — ширээ хаагдлаа. Buy-in суутгагдаагүй."
                if not complete:
                    note += " Pending refund байна; `A!pokerclaim` ашиглана уу."
            elif self.game.finished:
                complete = await self._settle()
                note = self._result_text()
                if not complete:
                    note += "\n⚠️ Pending payout байна; host `A!pokerclaim` ашиглана уу."
            else:
                self.game.current_player.folded = True
                if not self.game.active_players:
                    self.game.current_player.folded = False
                self.game.complete_board()
                complete = await self._settle()
                note = "⏰ Ээлжээ алдсан тоглогч fold хийлээ. " + self._result_text()
                if not complete:
                    note += "\n⚠️ Pending payout байна; host `A!pokerclaim` ашиглана уу."
            for child in self.children:
                child.disabled = True
            if self.message:
                try:
                    await self.message.edit(embed=self.build_embed(note), view=self)
                except discord.HTTPException as exc:
                    logger.warning("texas poker timeout edit failed: %s", exc, exc_info=True)


class TexasPoker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}
        self.pending_payouts = {}
        self.channel_locks = weakref.WeakValueDictionary()

    async def cog_load(self):
        try:
            rows = await self.bot.db_manager.fetch_all("poker_pending_payouts")
        except Exception as exc:
            logger.critical(
                "could not load durable poker payouts; apply migration 002: %s", exc,
                exc_info=True,
            )
            return
        self._cache_pending(rows)

    def _cache_pending(self, rows):
        self.pending_payouts.clear()
        for row in rows:
            if row.get("settled_at") is not None:
                continue
            channel_id = int(row["channel_id"])
            self.pending_payouts.setdefault(channel_id, []).append(
                (int(row["user_id"]), int(row["amount"]))
            )

    def _set_channel_cache(self, channel_id, rows):
        self.pending_payouts.pop(int(channel_id), None)
        for row in rows:
            if row.get("settled_at") is not None:
                continue
            self.pending_payouts.setdefault(int(channel_id), []).append(
                (int(row["user_id"]), int(row["amount"]))
            )

    async def _payout_rows(self, channel_id, guild_id):
        return await self.bot.db_manager.fetch_all(
            "poker_pending_payouts",
            {"channel_id": str(channel_id), "guild_id": str(guild_id)},
        )

    async def _pending_rows(self, channel_id, guild_id):
        rows = await self._payout_rows(channel_id, guild_id)
        return [row for row in rows if row.get("settled_at") is None]

    async def process_payouts(
        self, *, channel_id, guild_id, host_id, plan=None, prefer_pending=True,
        replace_pending=False,
    ):
        """Persist first, then atomically credit+delete each payout via RPC."""
        try:
            rows = await self._payout_rows(channel_id, guild_id)
            host_ids = {int(row["host_id"]) for row in rows}
            intents = {row.get("intent") or "settlement" for row in rows}
            if len(host_ids) > 1 or (host_ids and host_ids != {int(host_id)}):
                logger.critical(
                    "refusing mixed-host poker payouts in channel %s: %s",
                    channel_id, host_ids,
                )
                self._set_channel_cache(channel_id, rows)
                return False
            if len(intents) > 1:
                logger.critical(
                    "refusing mixed-intent poker payouts in channel %s: %s",
                    channel_id, intents,
                )
                self._set_channel_cache(channel_id, rows)
                return False
            if replace_pending and plan and not rows:
                logger.critical(
                    "refusing poker settlement without durable buy-in markers in channel %s",
                    channel_id,
                )
                return False
            if replace_pending and plan and intents != {"settlement"}:
                await self.bot.db_manager.rpc(
                    "prepare_poker_settlement",
                    {
                        "p_channel_id": str(channel_id),
                        "p_guild_id": str(guild_id),
                        "p_host_id": str(host_id),
                        "p_expected_total": sum(int(amount) for _, amount in plan),
                        "p_payouts": [
                            {"user_id": str(user_id), "amount": int(amount)}
                            for user_id, amount in (plan or []) if amount > 0
                        ],
                    },
                )
                rows = await self._payout_rows(channel_id, guild_id)
            pending = [row for row in rows if row.get("settled_at") is None]
            if pending and not prefer_pending:
                logger.critical(
                    "refusing new poker refund over existing pending payout in channel %s",
                    channel_id,
                )
                self._set_channel_cache(channel_id, pending)
                return False
            if rows and not pending:
                if plan:
                    expected = {
                        str(user_id): int(amount)
                        for user_id, amount in plan if amount > 0
                    }
                    durable = {
                        str(row["user_id"]): int(row["amount"])
                        for row in rows
                        if (row.get("intent") or "settlement") == "settlement"
                    }
                    if durable != expected:
                        logger.critical(
                            "settled poker rows do not match retry plan in channel %s",
                            channel_id,
                        )
                        return False
                self._set_channel_cache(channel_id, [])
                return True
            if not pending:
                logger.critical("no durable poker payout rows in channel %s", channel_id)
                return False

            for row in pending:
                try:
                    await self.bot.db_manager.rpc(
                        "settle_poker_payout",
                        {
                            "p_channel_id": str(channel_id),
                            "p_guild_id": str(guild_id),
                            "p_user_id": str(row["user_id"]),
                        },
                    )
                except Exception:
                    logger.exception(
                        "atomic texas payout failed for user %s",
                        row["user_id"],
                    )

            remaining = await self._pending_rows(channel_id, guild_id)
            self._set_channel_cache(channel_id, remaining)
            if remaining:
                logger.critical(
                    "durable texas payouts remain in channel %s: %s", channel_id, remaining
                )
                return False
            return True
        except Exception as exc:
            logger.critical(
                "texas payout persistence failed in channel %s: %s",
                channel_id, exc, exc_info=True,
            )
            try:
                self._set_channel_cache(
                    channel_id, await self._pending_rows(channel_id, guild_id)
                )
            except Exception:
                logger.critical("could not refresh poker payout cache", exc_info=True)
            return False

    async def player_restriction(self, member, guild_id):
        economy = self.bot.get_cog("Economy")
        if economy is None:
            return "❌ Economy систем ажиллахгүй байна."
        if await economy.is_in_prison(member.id, guild_id):
            return "🚔 Шоронд байхдаа тоглох боломжгүй."
        hunger, mood = await economy.get_hunger_mood(member.id, guild_id)
        if hunger >= 80:
            return "🍔 Та хэт өлсөж байна. `A!eat` ашиглана уу."
        if mood >= 80:
            return "😡 Та хэт ууртай байна. `A!relax` ашиглана уу."
        return None

    @commands.command(name="pokerclaim")
    async def pokerclaim(self, ctx):
        view = self.active_channels.get(ctx.channel.id)
        try:
            rows = await self._pending_rows(ctx.channel.id, ctx.guild.id)
        except Exception:
            logger.exception("pokerclaim lookup failed")
            return await ctx.send("⚠️ Pending payout мэдээлэл уншиж чадсангүй.")
        if not rows:
            return await ctx.send("Pending poker payout байхгүй байна.")
        host_ids = {int(row["host_id"]) for row in rows}
        if len(host_ids) != 1:
            logger.critical(
                "mixed-host pending poker rows in channel %s: %s", ctx.channel.id, host_ids
            )
            return await ctx.send(
                "🚨 Pending payout өгөгдөл зөрчилтэй байна. Admin шалгах хүртэл payout хийгдэхгүй."
            )
        host_id = next(iter(host_ids))
        if ctx.author.id != host_id:
            return await ctx.send("❌ Зөвхөн тухайн ширээний host payout retry хийнэ.")
        if view is not None:
            if not view.game.finished:
                return await ctx.send("❌ Идэвхтэй тоглолтын payout-ийг одоо claim хийх боломжгүй.")
            async with view._lock:
                complete = await view._settle()
        else:
            complete = await self.process_payouts(
                channel_id=ctx.channel.id,
                guild_id=ctx.guild.id,
                host_id=host_id,
                plan=None,
                prefer_pending=True,
            )
        if complete:
            await ctx.send("✅ Pending poker payout бүрэн олгогдлоо.")
        else:
            await ctx.send("⚠️ Зарим payout амжилтгүй хэвээр байна. Дараа дахин оролдоно уу.")

    @commands.command(name="pokerclaimadmin")
    @commands.has_permissions(manage_guild=True)
    async def pokerclaimadmin(self, ctx):
        """Let a guild moderator settle an orphaned payout in this channel."""
        if ctx.guild is None:
            return await ctx.send("❌ Зөвхөн серверт ашиглана уу.")
        try:
            rows = await self._pending_rows(ctx.channel.id, ctx.guild.id)
        except Exception:
            logger.exception("admin pokerclaim lookup failed")
            return await ctx.send("⚠️ Pending payout мэдээлэл уншиж чадсангүй.")
        if not rows:
            return await ctx.send("Pending poker payout байхгүй байна.")
        host_ids = {int(row["host_id"]) for row in rows}
        if len(host_ids) != 1:
            logger.critical(
                "admin refused mixed-host poker rows in channel %s: %s",
                ctx.channel.id, host_ids,
            )
            return await ctx.send(
                "🚨 Pending payout өгөгдөл зөрчилтэй тул автоматаар олгохгүй. DB admin шалгана уу."
            )
        intents = {row.get("intent") or "settlement" for row in rows}
        if len(intents) != 1:
            logger.critical(
                "admin refused mixed-intent poker rows in channel %s: %s",
                ctx.channel.id, intents,
            )
            return await ctx.send(
                "🚨 Pending payout intent зөрчилтэй байна. DB admin шалгана уу."
            )
        total = sum(int(row["amount"]) for row in rows)
        complete = await self.process_payouts(
            channel_id=ctx.channel.id,
            guild_id=ctx.guild.id,
            host_id=next(iter(host_ids)),
            plan=None,
            prefer_pending=True,
        )
        if complete:
            await ctx.send(f"✅ Admin recovery: {total:,} мөнгөний pending payout олгогдлоо.")
        else:
            await ctx.send("⚠️ Зарим payout амжилтгүй хэвээр байна. Дараа дахин оролдоно уу.")

    @commands.command(name="texas", aliases=["poker", "holdem"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def texas(self, ctx, buy_in: int | None = None):
        if ctx.guild is None:
            return await ctx.send("❌ Зөвхөн серверт ашиглана уу.")
        if buy_in is None:
            return await ctx.send(f"Хэрэглээ: `A!texas <buy-in>` ({MIN_BUY_IN:,}–{MAX_BUY_IN:,})")
        if not MIN_BUY_IN <= buy_in <= MAX_BUY_IN:
            return await ctx.send(f"❌ Buy-in {MIN_BUY_IN:,}–{MAX_BUY_IN:,} хооронд байна.")
        lock = self.channel_locks.setdefault(ctx.channel.id, asyncio.Lock())
        async with lock:
            if ctx.channel.id in self.active_channels:
                return await ctx.send("❌ Энэ сувагт Texas Poker ширээ аль хэдийн байна.")
            try:
                pending = await self._pending_rows(ctx.channel.id, ctx.guild.id)
            except Exception:
                logger.exception("texas pending-payout check failed")
                return await ctx.send(
                    "❌ Poker DB бэлэн биш байна. Admin migration 002 болон DB холболтыг шалгана уу."
                )
            if pending:
                self._set_channel_cache(ctx.channel.id, pending)
                return await ctx.send(
                    "❌ Энэ сувагт өмнөх pending payout байна. Host `A!pokerclaim` ашиглана уу."
                )
            economy = self.bot.get_cog("Economy")
            if economy is None:
                return await ctx.send("❌ Economy систем ажиллахгүй байна.")
            restriction = await self.player_restriction(ctx.author, ctx.guild.id)
            if restriction:
                return await ctx.send(restriction)
            balance = await economy.get_balance(ctx.author.id, ctx.guild.id)
            if balance < buy_in:
                return await ctx.send("❌ Buy-in хүрэлцэхгүй байна.")
            game = TexasHoldemGame(ctx.author, buy_in)
            view = TexasPokerView(self, ctx, game)
            self.active_channels[ctx.channel.id] = view
        view.message = await ctx.send(embed=view.build_embed(), view=view)


async def setup(bot):
    await bot.add_cog(TexasPoker(bot))
