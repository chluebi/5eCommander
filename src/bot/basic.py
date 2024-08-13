from typing import Optional, Any, List, cast, TYPE_CHECKING

import os
import time
import sys
import logging
import traceback

import sqlalchemy
import sqlalchemy.exc
import discord
from discord import app_commands
from discord.ext import commands

from src.bot.setup_logging import logger, setup_logging
from src.bot.util import (
    DEVELOPMENT_GUILD,
    standard_embed,
    success_embed,
    error_embed,
    player_embed,
    regions_embed,
)
from src.bot.checks import guild_exists, player_exists, always_fails
from src.database.postgres import PostgresDatabase
from src.core.exceptions import GuildNotFound, PlayerNotFound
from src.definitions.start_condition import start_condition


if TYPE_CHECKING:
    from src.bot.main import Bot


class GuildAdmin(commands.Cog):

    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.hybrid_command()  # type: ignore
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def init_guild(self, ctxt: commands.Context["Bot"]) -> None:
        """Initialises the guild to play 5eCommander. Needs administator permissions."""

        assert ctxt.guild is not None

        try:
            with self.bot.db.transaction() as con:
                guild_db = self.bot.db.add_guild(ctxt.guild.id, con=con)
                config = guild_db.get_config(con=con)
                config["channel_id"] = ctxt.channel.id
                guild_db.set_config(config, con=con)

        except sqlalchemy.exc.IntegrityError as e:
            raise commands.UserInputError("Guild already exists")

        await ctxt.send(
            embed=success_embed("Guild initialised", f"Config loaded: {guild_db.get_config()}")
        )

    @commands.hybrid_command()  # type: ignore
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.check(guild_exists)
    async def delete_guild(
        self, ctxt: commands.Context["Bot"], confirm: Optional[str] = "no"
    ) -> None:
        """Initialises the guild to play 5eCommander. Needs administator permissions."""

        assert ctxt.guild is not None

        if confirm != "Yes I confirm that I understand that all data will be deleted":
            await ctxt.send(
                embed=error_embed(
                    "Confirm",
                    f"The confirmation must be exactly 'Yes I confirm that I understand that all data will be deleted'.",
                )
            )
            return

        guild_db = self.bot.db.get_guild(ctxt.guild.id)
        self.bot.db.remove_guild(guild_db)

        await ctxt.send(
            embed=success_embed("Guild Removed", f"All data relating to this guild removed")
        )

    @commands.hybrid_command()  # type: ignore
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.check(guild_exists)
    async def guild_info(self, ctxt: commands.Context["Bot"]) -> None:
        """Gives you the guild configuration"""

        assert ctxt.guild is not None

        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        await ctxt.send(
            embed=success_embed(
                "Guild initialised",
                f"Server config: ``{guild_db.get_config()}``\n Events: ``{guild_db.get_events(0, time.time())}``",
            )
        )


class PlayerAdmin(commands.Cog):

    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(guild_exists)
    async def join(self, ctxt: commands.Context["Bot"]) -> None:
        """Join the game"""

        if ctxt.guild is None:
            await ctxt.send(embed=error_embed("User Error", f"You are not currently in a guild."))
            return

        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        try:
            player_db = guild_db.add_player(ctxt.author.id)
        except sqlalchemy.exc.IntegrityError as e:
            await ctxt.send(embed=error_embed("User Error", f"You already joined"))
            return

        await ctxt.send(embed=success_embed("Success", f"You have joined the game!"))

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def player_info(self, ctxt: commands.Context["Bot"], *, member: discord.Member) -> None:
        """Gives you the info about a player"""

        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        try:
            player_db = guild_db.get_player(member.id)
        except PlayerNotFound as e:
            await ctxt.send(embed=error_embed("User Error", f"No player of this name found"))
            return

        await ctxt.send(embed=player_embed(member, player_db, private=True))

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def me(self, ctxt: commands.Context["Bot"]) -> None:
        """Gives you the info about yourself, privately"""

        if ctxt.interaction is None:
            raise commands.CheckFailure("This command can only be called as a slash command")

        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)
        player_db = guild_db.get_player(ctxt.author.id)

        assert isinstance(ctxt.author, discord.Member)

        await ctxt.send(embed=player_embed(ctxt.author, player_db, private=False), ephemeral=True)

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def map(self, ctxt: commands.Context["Bot"]) -> None:
        """Gives you info about the locations in the game"""

        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        await ctxt.send(embed=regions_embed(guild_db))

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def play(self, ctxt: commands.Context["Bot"], card: int, region: int) -> None:
        """Uses a order to play a card to a region"""

        assert ctxt.guild is not None

        with self.bot.db.transaction() as con:
            guild_db = self.bot.db.get_guild(ctxt.guild.id, con=con)
            player_db = guild_db.get_player(ctxt.author.id, con=con)

            creatures = player_db.get_hand(con=con)
            creature_db = [c for c in creatures if c.id == card][0]

            regions = guild_db.get_regions(con=con)
            region_db = [r for r in regions if r.id == region][0]

            player_db.play_creature_to_region(creature_db, region_db, con=con)

            await ctxt.send(
                embed=success_embed(
                    "Creature Played",
                    f"Successfully played {creature_db.text()} to {region_db.text()}",
                )
            )

    @play.autocomplete("card")
    async def card_in_hand_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None
        guild_db = self.bot.db.get_guild(interaction.guild.id)
        player_db = guild_db.get_player(interaction.user.id)
        creatures = player_db.get_hand()

        return [
            discord.app_commands.Choice(
                name=(
                    f"{c.text()}: {c.creature.quest_ability_effect_full_text()}"
                    if c.creature.quest_ability_effect_full_text()
                    else c.text()
                ),
                value=c.id,
            )
            for c in creatures
            if c.text().startswith(current)
        ]

    @play.autocomplete("region")
    async def region_to_play_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None

        guild_db = self.bot.db.get_guild(interaction.guild.id)
        regions = guild_db.get_regions()
        regions = [r for r in regions if r.occupied() == (None, None)]

        creature_id = cast(int, interaction.namespace["card"])
        if creature_id != 0:
            player_db = guild_db.get_player(interaction.user.id)
            creatures = player_db.get_hand()
            creatures_filtered = [c for c in creatures if c.id == creature_id]
            if len(creatures_filtered) < 1:
                filtered_regions = regions
            else:
                creature = creatures_filtered[0]
                filtered_regions = [
                    r
                    for r in regions
                    if r.region.category in creature.creature.quest_region_categories
                ]
        else:
            filtered_regions = regions

        return [
            discord.app_commands.Choice(
                name=f"{r.text()}: {r.region.quest_effect_full_text()}", value=r.id
            )
            for r in filtered_regions
            if r.text().startswith(current)
        ]


async def setup(bot: "Bot") -> None:
    await bot.add_cog(GuildAdmin(bot))
    await bot.add_cog(PlayerAdmin(bot))
