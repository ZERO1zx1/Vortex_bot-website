"""Exercise the real navigation and modal payloads without Discord traffic."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from src.cogs.admin.admin import (
    AdminAnnounceModal,
    AdminPanelView,
    build_admin_panel_embed,
)
from src.cogs.community.confessions import (
    ConfessionModal,
    ConfessionStartView,
    CooldownModal,
    SetupView,
    build_confession_start_embed,
)
from src.cogs.community.giveaway import ColorModal, GiveawaySetupView, RoleModal
from src.cogs.community.marriage import MarriageSetupView
from src.cogs.economy.government import EconomyConfigView, GovernmentMainView
from src.cogs.games.counting import CountingSetupView
from src.cogs.system.help import COMMAND_INFO, HelpView
from src.cogs.system.menu import (
    CMDS_PER_PAGE,
    MenuView,
    _cmd_list,
    _get_categories,
    _total_pages,
)
from src.ui.setup import ConfirmActionView, SetupPanel, SetupState


def context():
    author = SimpleNamespace(id=7, display_avatar=SimpleNamespace(url="https://example.com/a.png"))
    return SimpleNamespace(author=author, guild=None, bot=SimpleNamespace(user=None), send=AsyncMock())


def assert_embed_limits(embed):
    assert len(embed) <= 6000
    assert len(embed.title or "") <= 256
    assert len(embed.description or "") <= 4096
    assert len(embed.fields) <= 25
    assert all(len(f.name) <= 256 and len(f.value) <= 1024 for f in embed.fields)


def test_shared_setup_panel_has_status_first_layout_and_valid_payload():
    embed = (
        SetupPanel(
            "Тест систем",
            "Тохиргооны товч тайлбар.",
            icon="⚙️",
            state=SetupState.INCOMPLETE,
        )
        .section("Заавал тохируулах", ["📍 Суваг  ⚠️ Тохируулаагүй"], icon="📌")
        .finish("Самбар 10 минут идэвхтэй")
    )

    assert embed.author.name == "🛡️ Aether Admin Console"
    assert embed.description.startswith("> ⚠️ **Тохиргоо дутуу**")
    assert "Удирдах эрх шаардлагатай" in embed.description
    assert embed.fields[0].name == "📌 Заавал тохируулах"
    assert embed.footer.text.startswith("🔐 Самбар 10 минут идэвхтэй")
    assert_embed_limits(embed)


def test_setup_confirmation_is_short_lived_and_actor_bound():
    view = ConfirmActionView(author_id=7, guild_id=5)

    assert view.timeout == 30
    assert [child.style for child in view.children] == [
        discord.ButtonStyle.danger,
        discord.ButtonStyle.secondary,
    ]
    view.stop()


def test_giveaway_setup_only_enables_create_when_required_values_are_valid():
    ctx = SimpleNamespace(author=SimpleNamespace(id=7), guild=SimpleNamespace(id=5))
    view = GiveawaySetupView(SimpleNamespace(), ctx)

    draft = view.build_embed()
    assert view.create_button.disabled
    assert "0/3" in draft.description

    view.channel = SimpleNamespace(mention="#giveaway", guild=ctx.guild)
    view.prize = "Discord Nitro"
    view.duration_str = "1h"
    ready = view.build_embed()

    assert not view.create_button.disabled
    assert "Үүсгэхэд бэлэн" in ready.description
    assert_embed_limits(ready)
    view.stop()


def test_counting_and_marriage_setup_buttons_describe_the_next_action():
    guild = SimpleNamespace(
        get_channel=lambda _id: SimpleNamespace(mention="#updates"),
        get_role=lambda role_id: SimpleNamespace(mention=f"<@&{role_id}>") if role_id else None,
    )
    counting = CountingSetupView(SimpleNamespace(), guild_id=5, author_id=7)
    counting_embed = counting.build_embed(
        {
            "channel_id": 10,
            "enabled": True,
            "math_mode": False,
            "delete_messages": True,
            "failed_role_id": 20,
            "reliable_role_id": 21,
            "level_5_role_id": 22,
            "level_20_role_id": 23,
            "level_50_role_id": 24,
            "high_score": 500,
            "best_streak": 40,
        },
        guild,
    )
    marriage = MarriageSetupView(SimpleNamespace(), guild_id=5, author_id=7)
    marriage_embed = marriage.build_embed(
        {
            "enabled": True,
            "polygamy": False,
            "max_spouses": 1,
            "announce_channel": 10,
            "marriage_role": 20,
        },
        guild,
    )

    assert counting.toggle_enabled.label == "Тооллого унтраах"
    assert marriage.toggle_enabled.label == "Систем унтраах"
    assert marriage.toggle_polygamy.label == "Полигами зөвшөөрөх"
    assert_embed_limits(counting_embed)
    assert_embed_limits(marriage_embed)
    counting.stop()
    marriage.stop()


@pytest.mark.asyncio
async def test_government_root_panels_follow_shared_setup_layout():
    guild = SimpleNamespace(id=5)
    user = SimpleNamespace(id=7, display_name="Hotaru")
    interaction = SimpleNamespace(guild=guild, user=user)
    cog = SimpleNamespace(
        get_settings=AsyncMock(
            return_value={
                "government_enabled": True,
                "tax_enabled": True,
                "tax_rate": 10,
            }
        ),
        get_government_roles=AsyncMock(
            return_value={
                "government_admin": 11,
                "president": None,
                "finance": 12,
                "tax_collector": None,
            }
        ),
        get_co_owner_ids=AsyncMock(return_value=[20]),
        get_recipients=AsyncMock(
            return_value=[{"recipient_type": "treasury", "percentage": 100}]
        ),
        get_custom_jobs=AsyncMock(return_value=[{"id": 1}]),
        get_role_incomes=AsyncMock(return_value=[]),
    )

    government_view = GovernmentMainView(cog, interaction)
    economy_view = EconomyConfigView(cog, interaction)
    government = await government_view.build_embed()
    economy = await economy_view.build_embed()

    assert government.description.startswith("> ✅ **Систем идэвхтэй**")
    assert government.fields[0].name == "📌 Ерөнхий төлөв"
    assert economy.description.startswith("> ✅ **Татвар идэвхтэй**")
    assert economy.fields[-1].name == "→ Дараагийн алхам"
    assert_embed_limits(government)
    assert_embed_limits(economy)
    government_view.stop()
    economy_view.stop()


def test_admin_panel_has_clear_status_and_semantic_action_order():
    permissions = SimpleNamespace(
        embed_links=True,
        manage_channels=True,
        manage_messages=True,
        read_message_history=True,
        send_messages=True,
    )
    default_role = SimpleNamespace(id=1)
    channel = SimpleNamespace(
        mention="#general",
        overwrites_for=lambda _role: SimpleNamespace(send_messages=None),
        permissions_for=lambda _role: permissions,
    )
    guild = SimpleNamespace(
        name="Aether Test",
        member_count=1250,
        members=[
            SimpleNamespace(status="online"),
            SimpleNamespace(status="offline"),
        ],
        channels=[object(), object(), object()],
        default_role=default_role,
        me=SimpleNamespace(guild_permissions=permissions),
        icon=SimpleNamespace(url="https://example.com/guild.png"),
    )
    user = SimpleNamespace(
        display_name="Hotaru",
        display_avatar=SimpleNamespace(url="https://example.com/admin.png"),
    )

    embed = build_admin_panel_embed(guild, channel, user, 42)
    view = AdminPanelView(SimpleNamespace(latency=0.042), guild.id if hasattr(guild, "id") else 5)

    assert "Админ удирдлагын самбар" in embed.title
    assert "1,250" in embed.fields[0].value
    assert "42 ms" in embed.fields[1].value
    assert "#general" in embed.fields[2].value
    assert [child.label for child in view.children] == [
        "Суваг түгжих",
        "10 мессеж цэвэрлэх",
        "Зарлал бичих",
        "Шинэчлэх",
        "Хаах",
    ]
    assert_embed_limits(embed)
    view.stop()


def test_admin_panel_modal_payload_fits_discord_limits():
    modal = AdminAnnounceModal()

    assert len(modal.title) <= 45
    labels = modal.to_dict()["components"]
    assert all(label["type"] == 18 for label in labels)
    assert all(len(label["label"]) <= 45 for label in labels)
    assert all(len(label.get("description", "")) <= 100 for label in labels)
    assert all(len(label["component"].get("placeholder", "")) <= 100 for label in labels)


@pytest.mark.asyncio
async def test_admin_panel_rejects_cross_guild_and_non_admin_interactions():
    view = AdminPanelView(SimpleNamespace(), guild_id=5)
    response = SimpleNamespace(send_message=AsyncMock())
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=6),
        user=SimpleNamespace(guild_permissions=SimpleNamespace(administrator=True)),
        response=response,
    )

    assert not await view.interaction_check(interaction)
    assert response.send_message.call_args.kwargs["ephemeral"]

    interaction.guild.id = 5
    interaction.user.guild_permissions.administrator = False
    assert not await view.interaction_check(interaction)

    interaction.user.guild_permissions.administrator = True
    assert await view.interaction_check(interaction)
    view.stop()


@pytest.mark.asyncio
async def test_admin_panel_timeout_disables_every_action():
    view = AdminPanelView(SimpleNamespace(), guild_id=5)
    view.message = SimpleNamespace(edit=AsyncMock())

    await view.on_timeout()

    assert all(child.disabled for child in view.children)
    view.message.edit.assert_awaited_once_with(view=view)


@pytest.mark.asyncio
async def test_every_menu_page_has_valid_embed_and_working_navigation():
    for category in _get_categories():
        for page in range(_total_pages(category)):
            view = MenuView(context().author, 5, start_category=category, page=page)
            assert_embed_limits(await view._build_embed())
            assert view.prev_button.disabled == (page == 0)
            assert view.next_button.disabled == (page + 1 == _total_pages(category))
            assert not view.detail_button.disabled
            expected = _cmd_list(category)[page * CMDS_PER_PAGE:(page + 1) * CMDS_PER_PAGE]
            assert [o.value for o in view.command_select.options] == expected
            assert not view.command_select.disabled
            assert [o.value for o in view.category_select.options if o.default] == [category]
            view.stop()


@pytest.mark.asyncio
async def test_menu_detail_uses_selected_command_and_preserves_example_prefix():
    view = MenuView(context().author, 5, start_category="Тоглоом")
    interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))
    await view._send_detail(interaction, "animeclash")
    payload = interaction.response.send_message.call_args.kwargs
    assert payload["ephemeral"]
    embed = payload["embed"]
    assert "animeclash" in embed.title
    examples = next(f.value for f in embed.fields if "Жишээ" in f.name)
    assert "A!A!" not in examples
    assert f"`{COMMAND_INFO['animeclash']['examples'][0]}`" in examples
    assert_embed_limits(embed)


@pytest.mark.asyncio
async def test_menu_timeout_edits_the_sent_message():
    view = MenuView(context().author, 5)
    await view._build_embed()
    view.message = SimpleNamespace(edit=AsyncMock())
    await view.on_timeout()
    view.message.edit.assert_awaited_once()
    assert all(child.disabled for child in view.children)


@pytest.mark.asyncio
async def test_help_rejects_other_members_and_disables_visible_controls_on_timeout():
    view = HelpView(context())
    interaction = SimpleNamespace(user=SimpleNamespace(id=8), response=SimpleNamespace(send_message=AsyncMock()))
    assert not await view.interaction_check(interaction)
    assert interaction.response.send_message.call_args.kwargs["ephemeral"]
    interaction.user.id = 7
    assert await view.interaction_check(interaction)
    await view.send_initial()
    view.message = SimpleNamespace(edit=AsyncMock())
    await view.on_timeout()
    assert all(child.disabled for child in view.children)
    view.message.edit.assert_awaited_once_with(view=view)


@pytest.mark.asyncio
async def test_giveaway_modal_labels_fit_discord_payload_limits():
    for cls in (ColorModal, RoleModal):
        modal = cls(SimpleNamespace())
        assert len(modal.title) <= 45
        components = [row["components"][0] for row in modal.to_dict()["components"]]
        assert all(len(item["label"]) <= 45 for item in components)
        assert all(len(item.get("placeholder", "")) <= 100 for item in components)


def test_confession_member_panel_explains_the_active_privacy_policy():
    anonymous = build_confession_start_embed({"anonymity": True, "cooldown": 30})
    named = build_confession_start_embed({"anonymity": False, "cooldown": 0})

    assert "нэр нийтлэгдэхгүй" in anonymous.fields[0].value
    assert anonymous.fields[1].value == "30 секунд"
    assert "Discord нэр" in named.fields[0].value
    assert named.fields[1].value == "Хязгаарлалтгүй"
    assert_embed_limits(anonymous)
    assert_embed_limits(named)


def test_confession_setup_panel_shows_readiness_and_updates_control_labels():
    channels = {
        10: SimpleNamespace(mention="#confess"),
        20: SimpleNamespace(mention="#published"),
    }
    guild = SimpleNamespace(get_channel=lambda channel_id: channels.get(channel_id))
    view = SetupView(SimpleNamespace(), guild_id=5, author_id=7)

    incomplete = view.build_embed(None, guild)
    assert "тохиргоо дутуу" in incomplete.description

    ready = view.build_embed(
        {
            "confess_channel": 10,
            "output_channel": 20,
            "anonymity": False,
            "cooldown": 45,
        },
        guild,
    )
    assert "Ажиллахад бэлэн" in ready.description
    assert ready.fields[0].value == "📥 #confess"
    assert ready.fields[1].value == "📤 #published"
    assert view.toggle_anon.label == "Нууцлал: унтраалттай"
    assert view.cooldown_button.label == "Илгээх зай: 45 сек"
    assert_embed_limits(ready)


def test_confession_component_payloads_fit_discord_limits():
    compose = ConfessionStartView(SimpleNamespace(), author_id=7)
    setup = SetupView(SimpleNamespace(), guild_id=5, author_id=7)
    modal = ConfessionModal(SimpleNamespace())
    cooldown = CooldownModal(setup, current_value=120)

    assert all(
        len(getattr(child, "label", "") or "") <= 80
        for child in compose.children + setup.children
    )
    for item in (modal, cooldown):
        assert len(item.title) <= 45
        components = [row["components"][0] for row in item.to_dict()["components"]]
        assert all(len(component["label"]) <= 45 for component in components)
        assert all(len(component.get("placeholder", "")) <= 100 for component in components)
    assert cooldown.seconds.default == "120"
