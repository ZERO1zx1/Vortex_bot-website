from __future__ import annotations

import discord

from ui.embeds import base_embed, progress_bar


def test_progress_bar_boundaries() -> None:
    assert progress_bar(0, 10, length=10) == "░" * 10
    assert progress_bar(10, 10, length=10) == "█" * 10
    assert progress_bar(5, 10, length=10) == "█" * 5 + "░" * 5
    assert progress_bar(20, 10, length=4) == "█" * 4


def test_progress_bar_invalid_total() -> None:
    assert progress_bar(5, 0, length=3) == "░" * 3
    assert progress_bar(5, 10, length=0) == ""


def test_base_embed_has_brand_author() -> None:
    embed = base_embed("Title", "Description")
    assert isinstance(embed, discord.Embed)
    assert embed.title == "Title"
    assert embed.description == "Description"
    assert embed.author.name is not None
