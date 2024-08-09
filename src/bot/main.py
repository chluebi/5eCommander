from typing import Optional, Any, List

import os

import sqlalchemy
import discord
from discord.ext import commands

from src.database.postgres import PostgresDatabase
from src.definitions.start_condition import start_condition


# initial setup taken from https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py

DEVELOPMENT_GUILD = discord.Object(id=int(os.environ["DEVELOPMENT_GUILD_ID"]))


url = sqlalchemy.engine.url.URL.create(
    drivername="postgresql+psycopg2",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host="db",
    port=5432,
    database=os.environ["POSTGRES_DB"],
)


engine = sqlalchemy.create_engine(url)
db = PostgresDatabase(start_condition, engine)


class Bot(commands.Bot):

    def __init__(self, initial_extensions: List[str], db: PostgresDatabase) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned_or("com "), intents=intents)

        self.initial_extensions = initial_extensions
        self.db = db

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            await self.load_extension(extension)

        self.tree.clear_commands(guild=DEVELOPMENT_GUILD)
        self.tree.copy_global_to(guild=DEVELOPMENT_GUILD)
        await self.tree.sync(guild=DEVELOPMENT_GUILD)

    async def on_ready(self) -> None:
        assert self.user is not None
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")


bot = Bot([], db)


@bot.tree.command()
async def hello(interaction: discord.Interaction) -> None:
    """Says hello!"""
    await interaction.response.send_message(f"Hi, {interaction.user.mention}")


@bot.tree.command()
@commands.is_owner()
async def sync(interaction: discord.Interaction) -> None:
    """Sync commands"""
    synced = await bot.tree.sync()
    await interaction.response.send_message(f"Synced {len(synced)} commands globally")


bot.run(os.environ["DISCORD_TOKEN"])
