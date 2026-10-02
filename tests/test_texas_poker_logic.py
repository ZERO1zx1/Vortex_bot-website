import asyncio
import gc
import random
import weakref
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.cogs.texas_poker import (
    TexasHoldemGame,
    TexasPoker,
    TexasPokerView,
    best_hand,
    evaluate_five,
)


def member(user_id):
    return SimpleNamespace(id=user_id, mention=f"<@{user_id}>", display_name=f"P{user_id}")


def test_asyncio_lock_supports_weak_references():
    lock = asyncio.Lock()
    reference = weakref.ref(lock)
    assert reference() is lock
    del lock
    gc.collect()
    assert reference() is None


def test_poker_migration_pins_atomic_money_contract():
    migration = Path(
        "src/database/migrations/002_poker_pending_payouts.sql"
    ).read_text(encoding="utf-8")

    assert "intent TEXT NOT NULL DEFAULT 'settlement'" in migration
    assert "CHECK (intent IN ('refund', 'settlement'))" in migration
    assert "WHERE settled_at IS NULL" in migration
    assert "ON CONFLICT (channel_id, user_id) DO NOTHING" in migration
    assert "RETURNING amount INTO v_marker" in migration
    assert migration.count("pg_advisory_xact_lock") == 4
    assert "Poker settlement already prepared" in migration
    assert "COALESCE(item->>'amount', '') !~ '^[0-9]+$'" in migration
    assert "NULLIF(BTRIM(item->>'user_id'), '') IS NULL" in migration
    assert "p_expected_total <= 0" in migration
    assert "COUNT(DISTINCT item->>'user_id')" in migration
    assert "v_refund_total <> p_expected_total" in migration
    assert "SET settled_at = NOW()" in migration
    assert "AND settled_at IS NULL" in migration
    assert "RETURNING amount, guild_id INTO v_amount, v_row_guild_id" in migration
    assert "guild_id = v_row_guild_id" in migration
    assert "SECURITY DEFINER" in migration
    assert "REVOKE ALL ON FUNCTION settle_poker_payout" in migration


def test_royal_flush_beats_four_of_a_kind():
    royal = [(14, "♠"), (13, "♠"), (12, "♠"), (11, "♠"), (10, "♠")]
    quads = [(9, "♠"), (9, "♥"), (9, "♦"), (9, "♣"), (14, "♥")]

    assert evaluate_five(royal)[0] == 8
    assert evaluate_five(quads)[0] == 7
    assert evaluate_five(royal) > evaluate_five(quads)


def test_wheel_straight_is_recognized():
    wheel = [(14, "♠"), (5, "♥"), (4, "♦"), (3, "♣"), (2, "♠")]

    assert evaluate_five(wheel) == (4, 5)


def test_best_hand_chooses_full_house_from_seven_cards():
    cards = [
        (13, "♠"), (13, "♥"), (13, "♦"),
        (8, "♠"), (8, "♥"), (2, "♣"), (3, "♣"),
    ]

    score, name = best_hand(cards)

    assert score[:3] == (6, 13, 8)
    assert name == "Full House"


def test_two_player_preflop_advances_after_call_and_check():
    game = TexasHoldemGame(member(1), 1_000)
    game.add_player(member(2))

    assert game.start() is True
    assert game.stage == "preflop"
    assert game.current_player.id == 2
    assert game.pot == 30
    assert sum(player.chips for player in game.players) + game.pot == 2_000

    assert game.act(2, "call")["status"] == "continue"
    result = game.act(1, "call")

    assert result["status"] == "next_stage"
    assert game.stage == "flop"
    assert len(game.community) == 3


def test_fold_ends_heads_up_hand():
    game = TexasHoldemGame(member(1), 500)
    game.add_player(member(2))
    game.start()

    result = game.act(game.current_player.id, "fold")
    winners, hand_name = game.winners()

    assert result == {"status": "finished", "reason": "fold"}
    assert [player.id for player in winners] == [1]
    assert hand_name is None
    assert game.payout_plan() == {1: 505, 2: 495}
    assert sum(game.payout_plan().values()) == 1_000


def test_showdown_tie_returns_both_winners():
    game = TexasHoldemGame(member(1), 500)
    game.add_player(member(2))
    game.start()
    game.community = [(14, "♠"), (13, "♠"), (12, "♠"), (11, "♠"), (10, "♠")]
    game.players[0].cards = [(2, "♥"), (3, "♦")]
    game.players[1].cards = [(4, "♥"), (5, "♦")]

    winners, hand_name = game.winners()

    assert {player.id for player in winners} == {1, 2}
    assert hand_name == "Straight Flush"


def test_short_call_becomes_all_in_and_runs_board():
    game = TexasHoldemGame(member(1), 1_000)
    game.add_player(member(2))
    game.start()
    current = game.current_player
    current.chips = 5

    result = game.act(current.id, "call")

    assert result == {"status": "finished", "reason": "all_in"}
    assert current.all_in is True
    assert current.chips == 0
    assert len(game.community) == 5


def test_side_pots_and_remaining_stacks_conserve_money():
    game = TexasHoldemGame(member(1), 200)
    game.add_player(member(2))
    game.add_player(member(3))
    game.start()
    game.community = [(2, "♠"), (7, "♥"), (9, "♦"), (11, "♣"), (12, "♠")]
    game.players[0].cards = [(14, "♥"), (14, "♦")]
    game.players[1].cards = [(13, "♥"), (13, "♦")]
    game.players[2].cards = [(3, "♥"), (4, "♦")]
    commitments = (100, 200, 200)
    for player, committed in zip(game.players, commitments):
        player.committed = committed
        player.chips = game.buy_in - committed
        player.round_bet = 0
    game.players[2].folded = True
    game.complete_board()

    payouts = game.payout_plan()

    assert payouts == {1: 400, 2: 200, 3: 0}
    assert sum(payouts.values()) == game.buy_in * len(game.players)


def test_randomized_payout_plans_always_conserve_money():
    rng = random.Random(20261002)
    for _ in range(1_000):
        player_count = rng.randint(2, 6)
        buy_in = rng.randint(100, 10_000)
        game = TexasHoldemGame(member(1), buy_in)
        for user_id in range(2, player_count + 1):
            game.add_player(member(user_id))
        game.start()
        game.complete_board()
        active_index = rng.randrange(player_count)
        for index, player in enumerate(game.players):
            committed = rng.randint(0, buy_in)
            player.committed = committed
            player.chips = buy_in - committed
            player.round_bet = 0
            player.folded = index != active_index and rng.choice((True, False))

        payouts = game.payout_plan()

        assert sum(payouts.values()) == buy_in * player_count
        assert all(amount >= 0 for amount in payouts.values())


@pytest.mark.asyncio
async def test_partial_payout_retry_does_not_double_pay_successes():
    class FakeDB:
        def __init__(self):
            self.fail_user_2 = True
            self.fail_prepare_once = True
            self.credits = {1: 0, 2: 0}
            self.rows = {}

        async def fetch_all(self, table, filters=None):
            rows = list(self.rows.values())
            if filters:
                rows = [row for row in rows if all(row[k] == str(v) for k, v in filters.items())]
            return rows

        async def upsert(self, table, data, on_conflict=None):
            self.rows[(data["channel_id"], data["user_id"])] = dict(data)
            return [data]

        async def rpc(self, name, params):
            if name == "prepare_poker_settlement":
                if self.fail_prepare_once:
                    self.fail_prepare_once = False
                    raise RuntimeError("temporary prepare failure")
                self.rows = {
                    (params["p_channel_id"], payout["user_id"]): {
                        "channel_id": params["p_channel_id"],
                        "guild_id": params["p_guild_id"],
                        "user_id": payout["user_id"],
                        "host_id": params["p_host_id"],
                        "amount": payout["amount"],
                        "intent": "settlement",
                        "settled_at": None,
                    }
                    for payout in params["p_payouts"]
                }
                return len(self.rows)
            user_id = int(params["p_user_id"])
            if user_id == 2 and self.fail_user_2:
                raise RuntimeError("temporary write failure")
            key = (params["p_channel_id"], params["p_user_id"])
            row = self.rows.get(key)
            if row and row.get("settled_at") is None:
                self.credits[user_id] += int(row["amount"])
                row["settled_at"] = "now"
                return int(row["amount"])
            return 0

    db = FakeDB()
    db.rows = {
        ("99", "1"): {
            "channel_id": "99", "guild_id": "5", "user_id": "1",
            "host_id": "1", "amount": 1_000, "intent": "refund",
            "settled_at": None,
        },
        ("99", "2"): {
            "channel_id": "99", "guild_id": "5", "user_id": "2",
            "host_id": "1", "amount": 1_000, "intent": "refund",
            "settled_at": None,
        },
    }
    bot = SimpleNamespace(db_manager=db, get_cog=lambda name: None)
    cog = TexasPoker(bot)
    ctx = SimpleNamespace(guild=SimpleNamespace(id=5), channel=SimpleNamespace(id=99))
    game = TexasHoldemGame(member(1), 1_000)
    game.add_player(member(2))
    game.start()
    game.players[1].folded = True
    game.finished = True
    game.stage = "showdown"
    view = TexasPokerView(cog, ctx, game)
    cog.active_channels[99] = view

    # A failed prepare must leave refund markers intact; retry must prepare the
    # winner plan rather than paying those refunds as if they were settlement.
    assert await view._settle() is False
    assert db.credits == {1: 0, 2: 0}
    assert {row["intent"] for row in db.rows.values()} == {"refund"}

    assert await view._settle() is False
    assert db.credits == {1: 1_010, 2: 0}
    assert cog.pending_payouts[99] == [(2, 990)]
    assert game.settled is False

    # Simulate a process restart: only the durable DB row survives.
    restarted_cog = TexasPoker(bot)
    await restarted_cog.cog_load()
    assert restarted_cog.pending_payouts[99] == [(2, 990)]

    db.fail_user_2 = False
    assert await restarted_cog.process_payouts(
        channel_id=99,
        guild_id=5,
        host_id=1,
        plan=None,
        prefer_pending=True,
    ) is True
    assert db.credits == {1: 1_010, 2: 990}
    assert 99 not in restarted_cog.pending_payouts
    assert all(row["settled_at"] is not None for row in db.rows.values())
