from typing import Any, Union, List, cast, Callable

import asyncio
import os
import time
import re
from collections import defaultdict

from discord import Embed, Color
from discord import DMChannel, TextChannel
import discord
from discord.ext import commands

from src.database.database import Database
from src.core.base_types import Resource, resource_to_emoji, Event, BaseResources, RegionCategory
from src.core.exceptions import CreatureNotFound, RegionNotFound
from src.definitions.regions import region_categories


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


def get_relative_timestamp(seconds: Union[int | float]) -> str:
    return f"<t:{int(seconds)}:R>"


def get_absolute_timestamp(seconds: Union[int | float]) -> str:
    return f"<t:{int(seconds)}:F>"


async def delete_message(message: discord.Message, seconds: int) -> None:
    await asyncio.sleep(seconds)
    await message.delete()


def player_embed(
    member: discord.Member, player_db: Database.Player, private: bool = True
) -> discord.Embed:
    guild_config = player_db.guild.get_config()
    max_orders = int(guild_config["max_orders"])
    max_magic = int(guild_config["max_magic"])
    max_cards = int(guild_config["max_cards"])

    resources = player_db.get_resources()
    recharges = player_db.get_recharges()

    resources_text = {
        r: f"{r.name.lower()} {resource_to_emoji(r)}: {v}" for r, v in resources.items()
    }

    resources_text[Resource.ORDERS] += f"/{max_orders}"
    if resources[Resource.ORDERS] < max_orders:
        resources_text[
            Resource.ORDERS
        ] += f" (+1 in {get_relative_timestamp(recharges[Database.Player.PlayerOrderRechargeEvent.event_type].timestamp)})"

    resources_text[Resource.MAGIC] += f"/{max_magic}"
    if resources[Resource.MAGIC] < max_magic:
        resources_text[
            Resource.MAGIC
        ] += f" (+1 in {get_relative_timestamp(recharges[Database.Player.PlayerMagicRechargeEvent.event_type].timestamp)})"

    resources_text_joined = "\n".join([resources_text[r] for r in BaseResources])

    hand = player_db.get_hand()

    hand_recharge_text = ""
    if len(hand) < guild_config["max_cards"]:
        hand_recharge_text = f" (+1 in {get_relative_timestamp(recharges[Database.Player.PlayerCardRechargeEvent.event_type].timestamp)})"

    deck = player_db.get_deck()

    hand_text = f"{len(player_db.get_hand())}/{max_cards} cards"
    deck_text = f"{len(player_db.get_deck())} cards"
    if private:
        hand_text += " 👁️"
        deck_text += " 👁️"
    else:
        hand_text += "\n" + "\n".join([h.text() for h in hand])
        deck_text += "\n" + "\n".join([d.text() for d in deck])

    if hand_recharge_text != "":
        hand_text += f"\n {hand_recharge_text}"

    discard_text = "\n".join([d.text() for d in player_db.get_discard()])
    played_text = "\n".join(
        [
            f"{c.text()} (goes to discard in {get_relative_timestamp(timestamp)})"
            for c, timestamp in player_db.get_played()
        ]
    )

    campaign = sorted(player_db.get_campaign(), key=lambda x: x[1], reverse=True)
    campaign_total = sum([x for _, x in campaign])

    campaign_text = (
        f"{campaign_total} {resource_to_emoji(Resource.STRENGTH)} {Resource.STRENGTH.name}"
    )
    campaign_text += "\n" + "\n".join(
        [
            f"{c.text()}: {i} {resource_to_emoji(Resource.STRENGTH)}" if i > 0 else c.text()
            for c, i in campaign
        ]
    )

    embed = standard_embed("Player Info: " + member.display_name, resources_text_joined)

    embed.add_field(name="Hand", value=hand_text)
    embed.add_field(name="Deck", value=deck_text)
    if discard_text:
        embed.add_field(name="Discard", value=discard_text)
    if played_text:
        embed.add_field(name="Played", value=played_text)
    if campaign_text:
        embed.add_field(name="Campaign", value=campaign_text)

    return embed


def regions_embed(guild_db: Database.Guild) -> discord.Embed:

    regions = sorted(guild_db.get_regions(), key=lambda x: x.id)
    regions_cache = {r.id: r for r in regions}
    regions_occupied = {r.id: r.occupied() for r in regions}

    region_categories: defaultdict[RegionCategory, List[int]] = defaultdict(lambda: [])
    for r in regions:
        assert r.region.category is not None
        region_categories[r.region.category].append(r.id)

    embed = standard_embed("Map", "All locations")

    for rc, sub_regions in region_categories.items():
        rc_text = ""
        for rid in sub_regions:
            creature, timestamp = regions_occupied[rid]
            r_text = f"{regions_cache[rid].region.name}:  **{regions_cache[rid].region.quest_effect_short_text()}**"

            if creature is not None and timestamp is not None:
                r_text = f"~~{r_text}~~"
                r_text += f" ({get_relative_timestamp(timestamp)})"

            rc_text += f"{r_text}\n\n"

        embed.add_field(name=str(rc.name).capitalize(), value=rc_text)

    return embed


def creature_embed(creature: Database.BaseCreature) -> discord.Embed:

    creature_title = creature.text()
    creature_text = f"**When played**: {creature.quest_ability_effect_full_text() if creature.quest_ability_effect_full_text() else '*no special ability*'}\n"
    creature_text += f"**When sent to campaign**: {creature.campaign_ability_effect_full_text() if creature.campaign_ability_effect_full_text() else '*no special ability*'}\n"

    return standard_embed(creature_title, creature_text)


def conflict_embed(guild_db: Database.Guild) -> discord.Embed:

    conflict_text = ""

    end_events = guild_db.get_events(
        time.time(), time.time() * 2, Database.Guild.ConflictEndEvent, also_resolved=False
    )
    if end_events != []:
        end_event = end_events[0]
        conflict_text += f"Ends in {get_relative_timestamp(end_event.timestamp)}\n"

    player_scores: dict[int, int] = {}
    players = guild_db.get_players()
    player_cache = {p.id: p for p in players}

    if len(players) > 0:
        for player_db in guild_db.get_players():
            player_strength = 0
            for c, s in player_db.get_campaign():
                player_strength += s

            player_scores[player_db.id] = player_strength

        sorted_scores = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (p_id, strength) in enumerate(sorted_scores, 1):
            conflict_text += (
                f"#{i} <player:{p_id}>: {strength} {resource_to_emoji(Resource.STRENGTH)}\n"
            )

    else:
        conflict_text = "No players currently playing"

    embed = standard_embed("Conflict", conflict_text)

    return embed


def format_player(id: int, guild: discord.Guild, guild_db: Database.Guild) -> str:
    return f"<@{id}>"


def format_creature(id: int, guild: discord.Guild, guild_db: Database.Guild) -> str:
    try:
        return guild_db.get_creature(id).text()
    except CreatureNotFound:
        return f"<creature:{id}>"


def format_region(id: int, guild: discord.Guild, guild_db: Database.Guild) -> str:
    try:
        return guild_db.get_region(id).text()
    except RegionNotFound:
        return f"<region:{id}>"


format_lookup: dict[str, Callable[[int, discord.Guild, Database.Guild], str]] = {
    "player": format_player,
    "creature": format_creature,
    "region": format_region,
}


def format_str(s: str, guild: discord.Guild, guild_db: Database.Guild) -> str:
    matches = re.findall(r"<(.+?):(\d+)>", s)

    new_s = s

    for t, id in matches:
        old = f"<{t}:{id}>"

        formatter = format_lookup.get(t)
        if formatter is not None:
            new_s = new_s.replace(old, formatter(id, guild, guild_db))

    return new_s


def format_embed(
    embed: discord.Embed, guild: discord.Guild, guild_db: Database.Guild
) -> discord.Embed:

    assert embed.title is not None
    assert embed.description is not None

    embed.title = format_str(embed.title, guild, guild_db)
    embed.description = format_str(embed.description, guild, guild_db)

    try:
        for f in embed._fields:
            f["name"] = format_str(str(f["name"]), guild, guild_db)
            f["value"] = format_str(str(f["value"]), guild, guild_db)

        return embed
    except AttributeError:
        return embed
