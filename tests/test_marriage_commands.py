"""Regression coverage for the streamlined /marriage command surface."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.cogs.community.marriage import (
    FAMILY_RELATIONS,
    Marriage,
    MarriageHubView,
    family_relation_label,
)
from src.cogs.system.help import COMMAND_INFO

EXPECTED_COMMANDS = {
    "guide", "propose", "divorce", "adopt", "request-parent",
    "leave-family", "family", "tree", "relationship", "disown",
    "love", "gift", "profile", "privacy", "setup",
}


def run_immediate(coroutine):
    """Drive mocked async code without opening a Windows networking event loop."""
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("Test coroutine unexpectedly required a live event loop")


def test_marriage_command_surface_is_small_and_documented():
    actual = {command.name for command in Marriage.marriage_group.commands}
    assert actual == EXPECTED_COMMANDS
    assert all(f"marriage {name}" in COMMAND_INFO for name in actual)
    retired = {
        "marriage marry", "marriage makeparent", "marriage runaway",
        "marriage partners", "marriage parent", "marriage children",
        "marriage fulltree", "marriage familysize", "marriage autoaccept",
        "propose", "spouse", "familytree", "marriagepro",
    }
    assert retired.isdisjoint(COMMAND_INFO)


def test_marriage_guide_and_requested_family_relations_are_available():
    assert "AETHER BONDS" in MarriageHubView.build_embed().title
    assert set(FAMILY_RELATIONS) == {
        "grandfather", "grandmother", "father", "mother", "older_brother",
        "older_sister", "younger_brother", "younger_sister", "child",
    }
    assert family_relation_label("grandfather") == "👴 Өвөө"
    assert family_relation_label("younger_sister") == "👧 Эмэгтэй дүү"


def test_family_overview_combines_every_relationship_type():
    cog = object.__new__(Marriage)
    cog.get_spouses = AsyncMock(return_value=[2])
    cog.get_parents = AsyncMock(return_value=[3])
    cog.get_children = AsyncMock(return_value=[4, 5])
    cog.get_family_relations = AsyncMock(return_value=[])
    cog._reply = AsyncMock()
    members = {
        uid: SimpleNamespace(id=uid, mention=f"<@{uid}>", display_name=f"user{uid}")
        for uid in range(1, 6)
    }
    guild = SimpleNamespace(id=10, get_member=members.get)
    interaction = SimpleNamespace(guild=guild, user=members[1])

    run_immediate(cog._family_overview(interaction, is_slash=True))

    embed = cog._reply.await_args.kwargs["embed"]
    assert "Нийт **5**" in embed.description
    assert [field.name for field in embed.fields] == [
        "💑 Хань · 1", "👪 Эцэг эх · 1", "👶 Хүүхэд · 2",
    ]
    assert cog._reply.await_args.kwargs["is_slash"] is True


def test_family_relation_is_saved_in_both_directions():
    cog = object.__new__(Marriage)
    database = SimpleNamespace(upsert=AsyncMock())
    cog.bot = SimpleNamespace(db_manager=database)

    run_immediate(cog.add_family_relation(10, 1, 2, "grandmother"))

    assert database.upsert.await_count == 2
    first = database.upsert.await_args_list[0].args[1]
    reverse = database.upsert.await_args_list[1].args[1]
    assert first["relation_type"] == "grandmother"
    assert reverse["relation_type"] == "grandchild"
    assert (first["user_id"], first["relative_id"]) == ("1", "2")
    assert (reverse["user_id"], reverse["relative_id"]) == ("2", "1")
