from typing import Any

import asyncio
import os

from discord import Embed, Color
from discord import DMChannel, TextChannel
import discord
from discord.ext import commands


DEVELOPMENT_GUILD = discord.Object(id=int(os.environ["DEVELOPMENT_GUILD_ID"]))


blue = Color.blue()
red = Color.red()
green = Color.green()
teal = Color.teal()
brown = Color.from_str("#FA9A69")


def standard_embed(title: str, description: str, color: Color = brown) -> discord.Embed:
    embed = Embed(title=title, description=description, color=color)
    return embed


def success_embed(title: str, description: str) -> discord.Embed:
    return standard_embed(title, description, color=green)


def info_embed(description: str) -> discord.Embed:
    return standard_embed("Info", description, color=brown)


def error_embed(title: str, description: str) -> discord.Embed:
    return standard_embed(title, description, color=red)


def is_dm(channel: discord.PartialMessageable) -> bool:
    return isinstance(channel, DMChannel)


def get_relative_timestamp(seconds: int) -> str:
    return f"<t:{seconds}:R>"


def get_absolute_timestamp(seconds: int) -> str:
    return f"<t:{seconds}:F>"


async def delete_message(message: discord.Message, seconds: int) -> None:
    await asyncio.sleep(seconds)
    await message.delete()
