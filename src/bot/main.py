from typing import Optional

import os

import discord
from discord import app_commands


# initial setup taken from https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py

MY_GUILD = discord.Object(id=int(os.environ["DEVELOPMENT_GUILD_ID"]))


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


intents = discord.Intents.default()
client = MyClient(intents=intents)


@client.event
async def on_ready() -> None:
    assert client.user is not None
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')


@client.tree.command()
async def hello(interaction: discord.Interaction) -> None:
    """Says hello!"""
    await interaction.response.send_message(f'Hi, {interaction.user.mention}')


client.run(os.environ["DISCORD_TOKEN"])