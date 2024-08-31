from typing import Optional, Any, List, cast, Tuple, Coroutine, Callable

import os
import sys
import logging
import traceback

from collections import defaultdict

import sqlalchemy
import sqlalchemy.exc
import discord
from discord.ext import commands

from src.bot.setup_logging import logger, setup_logging
from src.bot.util import (
    DEVELOPMENT_GUILD,
    PENDING_CHOICE,
    standard_embed,
    success_embed,
    error_embed,
)
from src.bot.checks import guild_exists, player_exists, always_fails
from src.database.postgres import PostgresDatabase
from src.core.exceptions import GuildNotFound, PlayerNotFound
from src.definitions.start_condition import start_condition
from src.definitions.extra_data import Choice, EXTRA_DATA


# initial setup taken from https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py


def connect_to_db() -> PostgresDatabase:
    url = sqlalchemy.engine.url.URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=str(os.environ["POSTGRES_HOST"]),
        port=45432,
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
        self.db = connect_to_db()
        self.logger = logger
        self.channel_cache: dict[int, discord.PartialMessageable] = {}

        self.pending_choices: dict[
            int,
            dict[int, Optional[PENDING_CHOICE]],
        ] = {}

    async def setup_hook(self) -> None:
        pass


bot = Bot(["src.bot.basic", "src.bot.cheats", "src.bot.event_handler"])


@bot.event
async def on_ready() -> None:
    assert bot.user is not None

    for extension in bot.initial_extensions:
        await bot.load_extension(extension)

    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("------")
    logger.info(f"connected to database with {len(bot.db.get_guilds())} guilds")


@bot.event
async def on_command_error(ctxt: commands.Context[Bot], error: Exception) -> None:
    error_message = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    m = f"""```{error}```"""

    await ctxt.send(embed=error_embed(type(error).__name__, m))

    if isinstance(error, commands.CheckFailure):
        return

    logging.error(error_message)


@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: Exception) -> None:
    error_message = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    m = f"""```{error}```"""

    if interaction.response.is_done():
        await interaction.followup.send(embed=error_embed(type(error).__name__, m))
    else:
        await interaction.response.send_message(embed=error_embed(type(error).__name__, m))

    if isinstance(error, commands.CheckFailure):
        return

    logging.error(error_message)


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
