"""Regression coverage for the economy admin panel authorisation.

The `admin-panel` and `workphrase` commands are admin-gated, but the panel
message is posted publicly and neither the view nor the modals it opens
re-checked who was acting. Any guild member who could see the panel could
rewrite the guild's economy configuration or delete its work phrases.
"""
import asyncio

from src.cogs.economy.economy import (
    AddPhraseModal,
    AdminPanelView,
    CooldownModal,
    CustomReplyModal,
    FailRateModal,
    FineModal,
    PayoutModal,
    RemovePhraseModal,
    WorkPhraseView,
    _admin_panel_allowed,
)

AUTHOR_ID = 111
GUILD_ID = 222


class FakeResponse:
    def __init__(self):
        self.messages = []

    async def send_message(self, content, **kwargs):
        self.messages.append(content)


class FakePermissions:
    def __init__(self, administrator):
        self.administrator = administrator


def make_member(user_id, administrator=True, guild_id=GUILD_ID):
    """A guild member stub exposing what the gate reads."""
    return type(
        "M",
        (),
        {
            "id": user_id,
            "guild_permissions": FakePermissions(administrator),
            "guild": type("G", (), {"id": guild_id})(),
        },
    )()


def make_interaction(user, guild_id=GUILD_ID):
    return type(
        "I",
        (),
        {
            "user": user,
            "guild": type("G", (), {"id": guild_id})(),
            "response": FakeResponse(),
        },
    )()


def test_non_author_is_rejected():
    member = make_member(AUTHOR_ID + 1)  # not the panel author
    ok = asyncio.run(_admin_panel_allowed(make_interaction(member), AUTHOR_ID, GUILD_ID))
    assert ok is False


def test_author_without_administrator_is_rejected():
    member = make_member(AUTHOR_ID, administrator=False)
    ok = asyncio.run(_admin_panel_allowed(make_interaction(member), AUTHOR_ID, GUILD_ID))
    assert ok is False


def test_author_from_another_guild_is_rejected():
    member = make_member(AUTHOR_ID)
    ok = asyncio.run(
        _admin_panel_allowed(make_interaction(member, guild_id=GUILD_ID + 1), AUTHOR_ID, GUILD_ID)
    )
    assert ok is False


def test_author_admin_is_allowed():
    member = make_member(AUTHOR_ID, administrator=True)
    ok = asyncio.run(_admin_panel_allowed(make_interaction(member), AUTHOR_ID, GUILD_ID))
    assert ok is True


def test_both_views_implement_interaction_check():
    assert hasattr(AdminPanelView, "interaction_check")
    assert hasattr(WorkPhraseView, "interaction_check")


def test_every_panel_modal_implements_interaction_check():
    for modal_cls in (
        CooldownModal,
        FineModal,
        PayoutModal,
        FailRateModal,
        CustomReplyModal,
        AddPhraseModal,
        RemovePhraseModal,
    ):
        assert hasattr(modal_cls, "interaction_check"), f"{modal_cls.__name__} has no interaction_check"


def test_config_modals_carry_the_opening_admin():
    modal = CooldownModal(AUTHOR_ID, GUILD_ID)
    assert modal.author_id == AUTHOR_ID
    assert modal.guild_id == GUILD_ID


def test_phrase_modals_carry_the_opening_admin():
    modal = AddPhraseModal(cog=None, guild_id=GUILD_ID, author_id=AUTHOR_ID)
    assert modal.author_id == AUTHOR_ID
    assert modal.guild_id == GUILD_ID
    modal = RemovePhraseModal(cog=None, guild_id=GUILD_ID, author_id=AUTHOR_ID)
    assert modal.author_id == AUTHOR_ID


def test_modal_interaction_check_rejects_a_non_author():
    modal = CooldownModal(AUTHOR_ID, GUILD_ID)
    intruder = make_member(AUTHOR_ID + 1)
    ok = asyncio.run(modal.interaction_check(make_interaction(intruder)))
    assert ok is False
