"""Compatibility adapter for slash-only admin/moderation commands."""


class SlashContext:
    """Expose the small Context API used by legacy command bodies."""

    def __init__(self, interaction):
        self._interaction = interaction
        self.author = interaction.user
        self.guild = interaction.guild
        self.channel = interaction.channel

    async def defer(self, *, ephemeral=False):
        if not self._interaction.response.is_done():
            await self._interaction.response.defer(ephemeral=ephemeral)

    async def send(self, content=None, *, embed=None, ephemeral=False, **kwargs):
        if not self._interaction.response.is_done():
            return await self._interaction.response.send_message(
                content=content, embed=embed, ephemeral=ephemeral
            )
        return await self._interaction.followup.send(
            content=content, embed=embed, ephemeral=ephemeral, wait=True
        )


def adapt_interaction(interaction):
    return SlashContext(interaction)


__all__ = ["SlashContext", "adapt_interaction"]
