from typing import Any, Union

import asyncio
import os

from discord import Embed, Color
from discord import DMChannel, TextChannel
import discord
from discord.ext import commands

from src.database.database import Database
from src.core.base_types import Resource, resource_to_emoji, Event, BaseResources


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
            f"{c.text()}: {i} {resource_to_emoji(Resource.STRENGTH)}" if i > 0 else str(c)
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
