from typing import Optional, Any, List, cast, TYPE_CHECKING

import os
import time
import sys
import logging
import traceback

import sqlalchemy
import sqlalchemy.exc
import discord
from discord.ext import commands

from src.bot.setup_logging import logger, setup_logging
from src.bot.util import DEVELOPMENT_GUILD, standard_embed, success_embed, error_embed
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
            embed=success_embed("Guild initialised", f"Server config: ``{guild_db.get_config()}``\n Events: ``{guild_db.get_events(0, time.time())}``")
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

        try:
            guild_db = self.bot.db.get_guild(ctxt.guild.id)
        except GuildNotFound as e:
            await ctxt.send(
                embed=error_embed(
                    "User Error", f"The guild on this server has not been initialised"
                )
            )
            return

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

        if ctxt.guild is None:
            await ctxt.send(embed=error_embed("User Error", f"You are not currently in a guild."))
            return

        try:
            guild_db = self.bot.db.get_guild(ctxt.guild.id)
        except GuildNotFound as e:
            await ctxt.send(
                embed=error_embed(
                    "User Error", f"The guild on this server has not been initialised"
                )
            )
            return

        try:
            player_db = guild_db.get_player(member.id)
        except PlayerNotFound as e:
            await ctxt.send(embed=error_embed("User Error", f"No player of this name found"))
            return

        await ctxt.send(
            embed=success_embed("User info", f"Resources: ``{player_db.get_resources()}``")
        )


async def setup(bot: "Bot") -> None:
    await bot.add_cog(GuildAdmin(bot))
    await bot.add_cog(PlayerAdmin(bot))
