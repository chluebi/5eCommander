from typing import Optional, Any, List, cast, Callable, Union, Coroutine, TYPE_CHECKING

import sqlalchemy
import sqlalchemy.exc
import discord
from discord.ext import commands
from discord.app_commands.commands import T

from src.database.postgres import PostgresDatabase
from src.core.exceptions import GuildNotFound, PlayerNotFound


if TYPE_CHECKING:
    from src.bot.main import Bot


class GuildNotInitialised(commands.CheckFailure):
    pass


class PlayerNotJoined(commands.CheckFailure):
    pass


async def is_admin_or_owner(ctxt: commands.Context["Bot"]) -> bool:
    if isinstance(ctxt.author, discord.User):
        return False
    return ctxt.author.id == ctxt.bot.owner_id or ctxt.author.guild_permissions.administrator


async def guild_exists(ctxt: commands.Context["Bot"]) -> bool:
    db = ctxt.bot.db

    assert ctxt.guild is not None

    try:
        db.get_guild(ctxt.guild.id)
    except GuildNotFound as e:
        raise GuildNotInitialised(
            "Guild has not been initialised. Ask an administrator to initialise the guild."
        )

    ctxt.bot.channel_cache[ctxt.channel.id] = cast(discord.PartialMessageable, ctxt.channel)

    return True


async def player_exists(ctxt: commands.Context["Bot"]) -> bool:
    db = ctxt.bot.db

    assert ctxt.guild is not None

    try:
        guild_db = db.get_guild(ctxt.guild.id)
    except GuildNotFound as e:
        raise GuildNotInitialised(
            "Guild has not been initialised. Ask an administrator to initialise the guild."
        )

    try:
        guild_db.get_player(ctxt.author.id)
    except PlayerNotFound as e:
        raise PlayerNotJoined(
            "Command can only be used by people who have joined the game. Use the join command."
        )

    return True


async def always_fails(ctxt: commands.Context["Bot"]) -> bool:
    return False
