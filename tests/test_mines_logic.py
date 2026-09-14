import asyncio
from types import SimpleNamespace

import pytest

from cogs.mines import GRID_COLS, GRID_SIZE, SAFE_COUNT, MinesGame, MinesView


class FakeResponse:
    def __init__(self, async_calls: list):
        self.messages = []
        self.edits = []
        self._calls = async_calls

    async def send_message(self, content, **kwargs):
        self.messages.append(content)
        if "msg" in self._calls:
            self._calls.remove("msg")
            await asyncio.sleep(0.01)

    async def edit_message(self, **kwargs):
        self.edits.append(kwargs)


class FakeInteraction:
    def __init__(self, user_id, calls):
        self.user = SimpleNamespace(id=user_id)
        self.response = FakeResponse(calls)


class FakeBank:
    def __init__(self):
        self.calls = 0
        self.total = 0

    async def update_balance(self, uid, gid, amount):
        self.calls += 1
        self.total += amount
        await asyncio.sleep(0.02)  # widen the double-click race window


def make_fakes(user_id=7, guild_id=5, bet=100):
    bank = FakeBank()

    class _BotFake:
        user = SimpleNamespace(display_avatar=SimpleNamespace(
            url="https://cdn.discordapp.com/avatars/0/0.png"))

        def get_cog(self, name):
            return bank if name == "Economy" else None

    ctx = SimpleNamespace(
        author=SimpleNamespace(id=user_id, mention=f"<@{user_id}>"),
        guild=SimpleNamespace(id=guild_id),
    )
    game = MinesGame(user_id, bet)
    view = MinesView(_BotFake(), ctx, game)
    return bank, view, game


def _safe_cell(game):
    for col in range(GRID_COLS):
        for row in range(1, GRID_SIZE + 1):
            if (col, row) not in game.bombs:
                return col, row
    raise AssertionError("no safe cell found")


def test_game_reveal_lifecycle():
    game = MinesGame(7, 100)
    col, row = _safe_cell(game)

    assert game.reveal(col, row) == "safe"
    assert game.current_win == 150          # 1.5x
    assert game.multiplier == 1.5

    assert game.reveal(col, row) == "already"

    bomb = next(iter(game.bombs))
    assert game.reveal(*bomb) == "bomb"
    assert game.finished is True


def test_game_all_safe_wins_jackpot():
    game = MinesGame(7, 100)
    # Reveal every non-bomb cell; the final one should report all_safe.
    last_result = None
    for col in range(GRID_COLS):
        for row in range(1, GRID_SIZE + 1):
            if (col, row) in game.bombs:
                continue
            last_result = game.reveal(col, row)
    assert last_result == "all_safe"
    assert game.finished is True
    assert len(game.revealed) == SAFE_COUNT


@pytest.mark.asyncio
async def test_double_cashout_pays_once():
    """Two concurrent Cashout clicks must credit the bank exactly once."""
    bank, view, game = make_fakes()

    i1 = FakeInteraction(game.user_id, calls=["msg", "msg"])
    i2 = FakeInteraction(game.user_id, calls=["msg", "msg"])

    await asyncio.gather(
        view.cashout_callback(i1),
        view.cashout_callback(i2),
    )

    assert bank.calls == 1
    assert bank.total == game.bet  # first click cashes the current win (= bet before any reveal)


@pytest.mark.asyncio
async def test_cashout_then_timeout_does_not_refund_again():
    bank, view, game = make_fakes()

    interaction = FakeInteraction(game.user_id, calls=[])
    await view.cashout_callback(interaction)
    assert bank.calls == 1

    await view.on_timeout()
    # game.finished is now True: the timeout must neither pay nor refund.
    assert bank.calls == 1
    assert bank.total == game.bet


@pytest.mark.asyncio
async def test_bomb_and_cashout_are_mutually_exclusive():
    bank, view, game = make_fakes()
    # mimic reveal path on a bomb
    bomb = next(iter(game.bombs))
    col, row = bomb
    button_number = 0
    view.game.reveal(col, row)
    assert view.game.finished is True
    button = list(view.buttons.values())[button_number]

    interaction = FakeInteraction(game.user_id, calls=[])
    # finished game: cashout must refuse and pay nothing
    await view.cashout_callback(interaction)
    assert bank.calls == 0


@pytest.mark.asyncio
async def test_timeout_refunds_bet_exactly_once():
    """A never-finished game must refund the original bet on timeout, once."""
    bank, view, game = make_fakes()

    await view.on_timeout()
    assert bank.calls == 1
    assert bank.total == game.bet

    # Second timeout (view.stop() would normally run, but simulate retry):
    await view.on_timeout()
    assert bank.calls == 1
    assert bank.total == game.bet


@pytest.mark.asyncio
async def test_timeout_after_reveal_still_refunds_only_bet():
    """Revealed cells earn no win on timeout: only the bet is returned."""
    bank, view, game = make_fakes()
    col, row = _safe_cell(game)
    assert game.reveal(col, row) == "safe"
    assert game.current_win > game.bet  # unrealized win exists

    await view.on_timeout()
    assert bank.calls == 1
    assert bank.total == game.bet  # win was never cashed out


@pytest.mark.asyncio
async def test_bomb_then_timeout_pays_nothing():
    """A finished (bomb) game must not refund on timeout."""
    bank, view, game = make_fakes()
    bomb = next(iter(game.bombs))
    view.game.reveal(*bomb)
    assert view.game.finished is True

    await view.on_timeout()
    assert bank.calls == 0
    assert bank.total == 0


@pytest.mark.asyncio
async def test_grid_callback_rejects_non_owner():
    """A non-owner pressing a grid cell is refused and the cell stays hidden."""
    bank, view, game = make_fakes()
    col, row = _safe_cell(game)
    intruder = FakeInteraction(9999, calls=["msg"])

    await view.buttons[(col, row)].callback(intruder)

    assert intruder.response.messages  # refusal message sent
    assert bank.calls == 0
    assert (col, row) not in game.revealed


@pytest.mark.asyncio
async def test_grid_callback_safe_reveal_updates_view():
    """An owner pressing a safe cell reveals it and edits the embed."""
    bank, view, game = make_fakes()
    viewer = FakeInteraction(game.user_id, calls=[])
    col, row = _safe_cell(game)

    await view.buttons[(col, row)].callback(viewer)

    assert (col, row) in game.revealed
    assert view.buttons[(col, row)].disabled is True
    assert viewer.response.edits  # embed updated


@pytest.mark.asyncio
async def test_all_safe_callback_pays_jackpot_once():
    """Revealing every safe cell via buttons pays the jackpot exactly once."""
    bank, view, game = make_fakes()
    viewer = FakeInteraction(game.user_id, calls=[])

    safe_cells = [(c, r) for c in range(GRID_COLS)
                  for r in range(1, GRID_SIZE + 1)
                  if (c, r) not in game.bombs]
    assert len(safe_cells) == SAFE_COUNT
    last = safe_cells[-1]

    for col, row in safe_cells[:-1]:
        await view.buttons[(col, row)].callback(viewer)
    assert bank.calls == 0  # no payout before the final cell

    await view.buttons[last].callback(viewer)
    assert bank.calls == 1
    assert bank.total == game.current_win  # bet * 1.5 ** SAFE_COUNT
    assert game.finished is True