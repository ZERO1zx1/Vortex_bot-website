"""Work view — ажлыг StringSelect-ээр сонгоно."""

from __future__ import annotations

from typing import Any

import discord

import config
from services.economy.income_service import IncomeService, JobDef
from ui.common.base import AetherView, refresh_panel
from ui.embeds import base_embed, format_number, work_embed
from utils.time_utils import humanize_seconds


class WorkView(AetherView):
    def __init__(
        self,
        author_id: int,
        income: IncomeService,
        jobs: list[JobDef],
        display_name: str,
    ) -> None:
        super().__init__(author_id)
        self.income = income
        self.display_name = display_name
        self.selected: str | None = None
        options = [
            discord.SelectOption(
                label=f"{job.icon} {job.name}"[:100],
                value=job.job_id,
                description=f"{format_number(job.min_pay)}–{format_number(job.max_pay)} ⛃ · +{job.xp} XP"[
                    :100
                ],
            )
            for job in jobs[:25]
        ]
        self.job_select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="💼 Ажил сонгох...",
            options=options,
            custom_id="work_job_select",
        )
        self.job_select.callback = self._select_job  # type: ignore[method-assign]
        self.add_item(self.job_select)

    async def _select_job(self, interaction: discord.Interaction) -> None:
        self.selected = self.job_select.values[0]
        result = await self.income.work(interaction.user.id, self.selected)
        self.job_select.disabled = True
        await refresh_panel(
            interaction,
            embed=work_embed(result, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="🎲 Санамсаргүй ажил",
        style=discord.ButtonStyle.primary,
        custom_id="work_random",
        row=1,
    )
    async def random_job(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        result = await self.income.work(interaction.user.id)
        self.job_select.disabled = True
        await refresh_panel(
            interaction,
            embed=work_embed(result, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="ℹ️ Мэдээлэл",
        style=discord.ButtonStyle.secondary,
        custom_id="work_info",
        row=1,
    )
    async def info(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        user = await self.income.users.get_or_create(interaction.user.id)
        jobs = self.income.jobs_for(user.level)
        lines = (
            "\n".join(
                f"{job.icon} **{job.name}** — {format_number(job.min_pay)}–"
                f"{format_number(job.max_pay)} ⛃ · `{job.job_id}`"
                for job in jobs
            )
            or "Танд тохирох ажил байхгүй."
        )
        embed = base_embed(
            "💼 Aether Jobs",
            "`a!work` — санамсаргүй, эсвэл доорх цэснээс сонгоно уу.",
            color=config.CYAN,
        )
        embed.add_field(name=f"Lv.{user.level} ажлууд", value=lines, inline=False)
        embed.set_footer(
            text=f"✦ Aether System • Cooldown {humanize_seconds(config.WORK_COOLDOWN_SEC)}"
        )
        await refresh_panel(interaction, embed=embed, view=self)
