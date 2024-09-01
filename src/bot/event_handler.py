from typing import Optional, Any, List, cast, TYPE_CHECKING, Tuple, Type

import os
import sys
import asyncio
import time
import logging
import random
import traceback

import sqlalchemy
import sqlalchemy.exc
import discord
from discord.ext import commands, tasks

from src.bot.util import (
    DEVELOPMENT_GUILD,
    standard_embed,
    success_embed,
    error_embed,
    free_creature_protected_embed,
    free_creature_unprotected_embed,
    free_creature_expired_embed,
    free_creature_claimed_embed,
    format_embed,
)
from src.database.postgres import PostgresDatabase
from src.core.base_types import Event
from src.core.exceptions import GuildNotFound, PlayerNotFound, CreatureNotFound
from src.definitions.start_condition import start_condition
from src.event_resolver.resolver import (
    KeepAlive,
    listen_to_notifications,
    add_notification_function,
)


if TYPE_CHECKING:
    from src.bot.main import Bot


handler_lock = asyncio.Lock()
waiting_lock = asyncio.Lock()


banned_events: List[Type[Event]] = [
    PostgresDatabase.Player.PlayerCardRechargeEvent,
    PostgresDatabase.Player.PlayerMagicRechargeEvent,
    PostgresDatabase.Player.PlayerOrderRechargeEvent,
    PostgresDatabase.Player.PlayerCardRechargedEvent,
    PostgresDatabase.Player.PlayerMagicRechargedEvent,
    PostgresDatabase.Player.PlayerOrderRechargedEvent,
    PostgresDatabase.Player.PlayerDrawEvent,
    PostgresDatabase.Player.PlayerGainEvent,
    PostgresDatabase.Player.PlayerPayEvent,
    PostgresDatabase.FreeCreature.FreeCreatureProtectedEvent,
    PostgresDatabase.FreeCreature.FreeCreatureExpiresEvent,
    PostgresDatabase.FreeCreature.FreeCreatureClaimedEvent,
    PostgresDatabase.Creature.CreatureRechargeEvent,
]


async def get_channel_exhaustively(
    bot: "Bot", guild: discord.Guild, channel_id: int
) -> Optional[discord.PartialMessageable]:
    channel = bot.channel_cache.get(channel_id)

    if channel is None:
        channel = cast(
            Optional[discord.PartialMessageable], guild.get_channel_or_thread(channel_id)
        )

    if channel is None:
        threads = (
            await guild.active_threads()
        )  # very inefficient but sometimes the only thing that works
        channel = cast(
            Optional[discord.PartialMessageable], discord.utils.get(threads, id=channel_id)
        )

    if channel is None:
        channels = (
            await guild.fetch_channels()
        )  # very inefficient but sometimes the only thing that works
        channel = cast(
            Optional[discord.PartialMessageable], discord.utils.get(channels, id=channel_id)
        )

    if channel is None:
        bot.logger.error("channel is none still")
        return None

    bot.channel_cache[channel_id] = channel
    return channel


class EventHandler(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot
        self.keep_alive = KeepAlive()
        self.event_handler_listener.start()
        self.event_handler_loop.start()
        self.refresh_free_creature_views.start()

    async def cog_unload(self) -> None:
        self.event_handler_loop.cancel()

    @tasks.loop(seconds=0, count=1)
    async def refresh_free_creature_views(self) -> None:
        for guild_db in self.bot.db.get_guilds():
            try:
                guild = await self.bot.fetch_guild(guild_db.id)
            except discord.NotFound:
                continue

            free_creatures = guild_db.get_free_creatures()

            for fc in free_creatures:
                if fc.is_expired(time.time()):
                    continue

                channel = await get_channel_exhaustively(self.bot, guild, fc.channel_id)
                if channel is None:
                    continue

                message = await channel.fetch_message(fc.message_id)

                with self.bot.db.transaction() as con:
                    if fc.is_expired(time.time(), con=con):
                        continue
                    if "Claimed by" in message.content:
                        continue

                    roller = await guild.fetch_member(fc.roller_id)

                    if fc.is_protected(time.time(), con=con):
                        embed, view = free_creature_protected_embed(
                            fc,
                            roller,
                            fc.get_protected_timestamp(),
                        )
                        await message.edit(embed=embed, view=view)
                    else:
                        embed, view = free_creature_unprotected_embed(
                            fc,
                            roller,
                            fc.get_expires_timestamp(),
                        )
                        await message.edit(embed=embed, view=view)

                await asyncio.sleep(4)

    async def event_handler(self, connection: Any, pid: Any, channel: Any, payload: str) -> None:
        embeds_to_send: List[Tuple[discord.Embed, discord.PartialMessageable]] = []

        if waiting_lock.locked():
            return

        async with waiting_lock:
            pass

        identifier = random.randint(1, 10000)

        async with handler_lock:
            for guild_db in self.bot.db.get_guilds():
                with self.bot.db.transaction() as con:
                    events = sorted(
                        guild_db.get_events(0, time.time(), also_resolved=False, con=con),
                        key=lambda x: x.id,
                    )

                    print("events", events)

                    if events == []:
                        continue

                    event_cache = {event.id: event for event in events}
                    event_children: dict[int, List[Event]] = {event.id: [] for event in events}
                    valid_events: List[Event] = []
                    root_events: List[Event] = []

                    for event in events:
                        if event.parent_event_id is not None:
                            if event.parent_event_id in event_children:
                                event_children[event.parent_event_id].append(event)
                                valid_events.append(event)

                            if event.timestamp + 5 < time.time():
                                # this is a sanity check where basically we count something as a root event if it should've happened 5 seconds ago
                                # we assume the parent isnt arriving
                                valid_events.append(event)
                                root_events.append(event)

                        else:
                            valid_events.append(event)
                            root_events.append(event)

                    def build_tree(
                        event: Event,
                        depth: int,
                        parent_tree: List[Tuple[Event, List[Any]]],
                        max_depth: int = 3,
                    ) -> None:
                        if depth > max_depth:
                            parent_tree.append((event, []))
                            return

                        for child in event_children[event.id]:
                            child_tree: List[Tuple[Event, List[Any]]] = []
                            parent_tree.append((child, child_tree))
                            build_tree(child, depth + 1, child_tree)

                    flat_event_tree: dict[int, List[Tuple[Event, Any]]] = {
                        event.id: [] for event in root_events
                    }
                    for root_event in root_events:
                        build_tree(root_event, 1, flat_event_tree[root_event.id])

                    channel_id = guild_db.get_config(con=con)["channel_id"]
                    assert channel_id != 0

                    try:
                        guild = await self.bot.fetch_guild(guild_db.id)
                    except discord.NotFound:
                        continue

                    t = time.time()
                    channel = await get_channel_exhaustively(self.bot, guild, channel_id)

                    for root_event_id, children in flat_event_tree.items():
                        root_event = event_cache[root_event_id]

                        allowed = True
                        for banned_event_type in banned_events:
                            if root_event.event_type == banned_event_type.event_type:
                                allowed = False
                                break

                        if not allowed:
                            continue

                        event_text = root_event.text() + "\n"

                        fields: List[Tuple[str, str]] = []
                        for child, grandchildren in children:
                            child_title = child.text()
                            child_text = ""
                            for grandchild, _ in grandchildren:
                                child_text += f"- {cast(Event, grandchild).text()}\n"

                            if child_text == "":
                                event_text += f"- {child.text()}\n"
                            else:
                                fields.append((child_title, child_text))

                        embed = standard_embed(f"Event Triggered #{root_event.id}", event_text)
                        for name, value in fields:
                            embed.add_field(name=name, value=value)

                        embeds_to_send.append((format_embed(embed, guild, guild_db), channel))

                    for event in valid_events:
                        try:
                            event.resolve(con=con)
                            cast(PostgresDatabase.Guild, event.guild).mark_event_as_resolved(
                                event, con=con
                            )

                        except Exception as error:
                            error_string = "".join(
                                traceback.format_exception(type(error), error, error.__traceback__)
                            )
                            self.bot.logger.error(error_string)

                for event in valid_events:
                    if isinstance(event, PostgresDatabase.FreeCreature.FreeCreatureEvent):
                        try:
                            free_creature = guild_db.get_free_creature(
                                event.channel_id, event.message_id
                            )
                            channel = await get_channel_exhaustively(
                                self.bot, guild, event.channel_id
                            )
                            roller = await guild.fetch_member(free_creature.roller_id)
                            if channel is not None:
                                message = await cast(
                                    discord.PartialMessageable, channel
                                ).fetch_message(event.message_id)

                                if isinstance(
                                    event,
                                    PostgresDatabase.FreeCreature.FreeCreatureProtectedEvent,
                                ):
                                    embed, view = free_creature_unprotected_embed(
                                        free_creature,
                                        roller,
                                        free_creature.get_expires_timestamp(),
                                    )
                                    await message.edit(embed=embed, view=view)
                                elif isinstance(
                                    event,
                                    PostgresDatabase.FreeCreature.FreeCreatureClaimedEvent,
                                ):
                                    claimer = await guild.fetch_member(event.player_id)
                                    if claimer is not None:
                                        await message.edit(
                                            embed=free_creature_claimed_embed(
                                                free_creature, roller, claimer
                                            ),
                                            view=None,
                                        )
                                elif isinstance(
                                    event,
                                    PostgresDatabase.FreeCreature.FreeCreatureExpiresEvent,
                                ):
                                    if any(
                                        e.description and "Claimed by" in e.description
                                        for e in message.embeds
                                    ):
                                        continue
                                    await message.edit(
                                        embed=free_creature_expired_embed(free_creature, roller),
                                        view=None,
                                    )

                            await asyncio.sleep(4)

                        except CreatureNotFound:
                            pass

            for embed, channel in embeds_to_send:
                cast_channel = cast(discord.PartialMessageable, channel)

                await cast_channel.send(embed=embed)
                await asyncio.sleep(4)  # rate limit

    @tasks.loop(seconds=0, count=1, reconnect=True)
    async def event_handler_listener(self) -> None:
        await self.bot.wait_until_ready()

        await self.event_handler(None, None, None, "0")

        try:
            add_notification_function(self.bot.db)
        except sqlalchemy.exc.ProgrammingError:
            pass

        listener_task = asyncio.create_task(
            listen_to_notifications(self.bot.db, self.event_handler, keep_alive=self.keep_alive)
        )
        await listener_task

    @tasks.loop(seconds=3, reconnect=True)
    async def event_handler_loop(self) -> None:
        await self.bot.wait_until_ready()
        await self.event_handler(None, None, None, "0")


async def setup(bot: "Bot") -> None:
    await bot.add_cog(EventHandler(bot))
