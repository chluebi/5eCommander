from typing import Optional, Any, List, cast

import os
import sys
import logging

import sqlalchemy
import discord
from discord.ext import commands

from src.database.postgres import PostgresDatabase
from src.definitions.start_condition import start_condition


# initial setup taken from https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py

DEVELOPMENT_GUILD = discord.Object(id=int(os.environ["DEVELOPMENT_GUILD_ID"]))


dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
color_formatter = logging.Formatter(
    "\033[34m[{asctime}] \033[1;34m[{levelname:<8}]\033[0m {name}: {message}", dt_fmt, style="{"
)

print_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler(
    filename="/var/log/5eCommander/bot.log", encoding="utf-8", mode="a"
)

print_handler.setFormatter(color_formatter)
file_handler.setFormatter(formatter)


logger = logging.getLogger("discord")
logger.addHandler(print_handler)
logger.addHandler(file_handler)


def connect_to_db() -> PostgresDatabase:
    url = sqlalchemy.engine.url.URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host="db",
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

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            await self.load_extension(extension)

        self.tree.clear_commands(guild=DEVELOPMENT_GUILD)
        self.tree.copy_global_to(guild=DEVELOPMENT_GUILD)
        await self.tree.sync(guild=DEVELOPMENT_GUILD)


bot = Bot([])


@bot.event
async def on_ready() -> None:
    assert bot.user is not None

    bot.db = connect_to_db()

    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("------")
    logger.info(f"connected to database with {len(bot.db.get_guilds())} guilds")


@bot.tree.command()
async def hello(interaction: discord.Interaction) -> None:
    """Says hello!"""
    logger.info("info command called")
    await interaction.response.send_message(f"Hi, {interaction.user.mention}")


@bot.tree.command()
@commands.is_owner()
async def sync(interaction: discord.Interaction) -> None:
    """Sync commands"""
    synced = await bot.tree.sync()
    await interaction.response.send_message(f"Synced {len(synced)} commands globally")


bot.run(os.environ["DISCORD_TOKEN"], log_handler=None)
