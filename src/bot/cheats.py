from typing import Optional, Any, List, cast, TYPE_CHECKING, Sequence

import os
import time
import copy
import asyncio
import sys
import logging
import traceback

import sqlalchemy
import sqlalchemy.exc
import discord
from discord import app_commands
from discord.ext import commands

from src.bot.util import (
    DEVELOPMENT_GUILD,
    get_relative_timestamp,
    standard_embed,
    success_embed,
    error_embed,
    player_embed,
    format_embed,
)
from src.bot.checks import guild_exists, player_exists
from src.core.exceptions import GuildNotFound, PlayerNotFound, CreatureNotFound
from src.core.base_types import Resource, Price, Selected
from src.definitions.start_condition import start_condition
from src.definitions.creatures import creatures


if TYPE_CHECKING:
    from src.bot.main import Bot


class Cheats(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.hybrid_command()  # type: ignore
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def cheat_give_card(self, ctxt: commands.Context["Bot"], *, member: discord.Member, card: int) -> None:
        """Administrator Cheat command to add a card to a player's hand."""
        assert ctxt.guild is not None

        guild_db = self.bot.db.get_guild(ctxt.guild.id)
        player_db = guild_db.get_player(member.id)

        with self.bot.db.transaction() as con:
            basecreature = creatures.get(card)
            if basecreature is None or basecreature not in guild_db.get_all_obtainable_basecreatures(con=con):
                raise CreatureNotFound(message="Creature not found")

            player_db.creature_creature_in_hand(basecreature, con=con)

            await ctxt.send(embed=success_embed("Cheat successful", f"Gave {basecreature.text()} to {member.mention}"), ephemeral=True)

    @cheat_give_card.autocomplete("card")
    async def card_in_guild_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None
        guild_db = self.bot.db.get_guild(interaction.guild.id)
        basecreatures = guild_db.get_all_obtainable_basecreatures()

        print('basecreatures', basecreatures)

        return [
            discord.app_commands.Choice(
                name=(f"{c.text()}"),
                value=c.id,
            )
            for c in basecreatures
            if current.lower() in c.text().lower()
        ]




async def setup(bot: "Bot") -> None:
    await bot.add_cog(Cheats(bot))
