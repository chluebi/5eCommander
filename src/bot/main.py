from typing import Optional, Any, List, cast

import os
import sys
import logging
import traceback

import sqlalchemy
import sqlalchemy.exc
import discord
from discord.ext import commands

from src.bot.setup_logging import logger, setup_logging
from src.bot.util import DEVELOPMENT_GUILD, standard_embed, success_embed, error_embed
from src.database.postgres import PostgresDatabase
from src.core.exceptions import GuildNotFound, PlayerNotFound
from src.definitions.start_condition import start_condition


# initial setup taken from https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py


def connect_to_db() -> PostgresDatabase:
    url = sqlalchemy.engine.url.URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=str(os.environ["POSTGRES_HOST"]),
        port=5432,
        database=os.environ["POSTGRES_DB"],
    )

    engine = sqlalchemy.create_engine(url)
    return PostgresDatabase(start_condition, engine)


class Bot(commands.Bot):

    def __init__(self, initial_extensions: List[str]) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned_or("com "), intents=intents)

        self.initial_extensions = initial_extensions
        self.db = cast(PostgresDatabase, None)
        self.logger = cast(logging.Logger, None)

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            await self.load_extension(extension)


bot = Bot([])


@bot.event
async def on_ready() -> None:
    assert bot.user is not None

    bot.logger = logger
    bot.db = connect_to_db()

    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("------")
    logger.info(f"connected to database with {len(bot.db.get_guilds())} guilds")


@bot.event
async def on_error(event: str) -> None:
    error_type, error, _ = sys.exc_info()

    if error is None:
        return

    error_message = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    logging.error(error_message)


@bot.event
async def on_command_error(ctx: commands.Context[Bot], error: Exception) -> None:
    error_message = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    logging.error(error_message)

    m = f"""```{error}```"""
    await ctx.send(embed=error_embed("Internal Error", m))


@bot.tree.command()
@commands.has_permissions(administrator=True)
async def init_guild(interaction: discord.Interaction) -> None:
    """Initialises the guild to play 5eCommander. Needs administator permissions."""

    if interaction.guild is None:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"You are not currently in a guild.")
        )
        return

    try:
        guild_db = bot.db.add_guild(interaction.guild.id)
    except sqlalchemy.exc.IntegrityError as e:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"Guild already exists")
        )

    await interaction.response.send_message(
        embed=success_embed("Guild initialised", f"Config loaded: {guild_db.get_config()}")
    )


@bot.tree.command()
@commands.has_permissions(administrator=True)
async def guild_info(interaction: discord.Interaction) -> None:
    """Gives you the guild configuration"""

    if interaction.guild is None:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"You are not currently in a guild.")
        )
        return

    try:
        guild_db = bot.db.get_guild(interaction.guild.id)
    except GuildNotFound as e:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"The guild on this server has not been initialised")
        )
        return

    await interaction.response.send_message(
        embed=success_embed("Guild initialised", f"Server config: ``{guild_db.get_config()}``")
    )


@bot.tree.command()
async def join(interaction: discord.Interaction) -> None:
    """Join the game"""

    if interaction.guild is None:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"You are not currently in a guild.")
        )
        return

    try:
        guild_db = bot.db.get_guild(interaction.guild.id)
    except GuildNotFound as e:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"The guild on this server has not been initialised")
        )
        return

    try:
        player_db = guild_db.add_player(interaction.user.id)
    except sqlalchemy.exc.IntegrityError as e:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"You already joined")
        )
        return

    await interaction.response.send_message(
        embed=success_embed("Success", f"You have joined the game!")
    )


@bot.tree.command()
async def player_info(interaction: discord.Interaction, member: discord.Member) -> None:
    """Gives you the info about a user"""

    if interaction.guild is None:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"You are not currently in a guild.")
        )
        return

    try:
        guild_db = bot.db.get_guild(interaction.guild.id)
    except GuildNotFound as e:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"The guild on this server has not been initialised")
        )
        return

    try:
        player_db = guild_db.get_player(member.id)
    except PlayerNotFound as e:
        await interaction.response.send_message(
            embed=error_embed("User Error", f"No player of this name found")
        )
        return

    await interaction.response.send_message(
        embed=success_embed("User info", f"Resources: ``{player_db.get_resources()}``")
    )


@bot.command()
@commands.is_owner()
async def global_sync(ctxt: commands.Context[Bot]) -> None:
    """Sync commands"""
    synced = await bot.tree.sync()
    await ctxt.send(embed=success_embed("Sync", f"Synced {len(synced)} global commands"))


@bot.command()
@commands.is_owner()
async def test_sync(ctxt: commands.Context[Bot]) -> None:
    """Sync commands to test guild"""
    bot.tree.clear_commands(guild=DEVELOPMENT_GUILD)
    bot.tree.copy_global_to(guild=DEVELOPMENT_GUILD)
    synced = await bot.tree.sync(guild=DEVELOPMENT_GUILD)
    await ctxt.send(embed=success_embed("Sync", f"Synced {len(synced)} commands to test guild"))


bot.run(os.environ["DISCORD_TOKEN"])
