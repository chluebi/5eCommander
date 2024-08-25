from typing import Any, Union, List, cast, Callable, Tuple, Optional, Coroutine, TYPE_CHECKING

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
from src.core.base_types import (
    Resource,
    resource_to_emoji,
    Event,
    BaseResources,
    RegionCategory,
    region_categories,
)
from src.core.exceptions import CreatureNotFound, RegionNotFound

from src.definitions.extra_data import EXTRA_DATA, Choice


if TYPE_CHECKING:
    from src.bot.main import Bot


DEVELOPMENT_GUILD = discord.Object(id=int(os.environ["DEVELOPMENT_GUILD_ID"]))

CALLBACK = Callable[[commands.Context["Bot"], EXTRA_DATA], Coroutine[None, None, None]]
PENDING_CHOICE = Tuple[Choice, CALLBACK, EXTRA_DATA]


def get_pending_choice(
    guild_id: int,
    player_id: int,
    pending_choices: dict[int, dict[int, Optional[PENDING_CHOICE]]],
) -> Optional[PENDING_CHOICE]:
    guild_players = pending_choices.get(guild_id)
    if guild_players is None:
        return None
    player_choice = guild_players.get(player_id)
    return player_choice


def add_pending_choice(
    guild_id: int,
    player_id: int,
    choice: Choice,
    callback: CALLBACK,
    extra_data: EXTRA_DATA,
    pending_choices: dict[int, dict[int, Optional[PENDING_CHOICE]]],
) -> None:
    guild_players = pending_choices.get(guild_id)
    if guild_players is None:
        pending_choices[guild_id] = {}
    guild_players = pending_choices[guild_id]

    guild_players[player_id] = choice, callback, extra_data


def clear_pending_choice(
    guild_id: int,
    player_id: int,
    pending_choices: dict[int, dict[int, Optional[PENDING_CHOICE]]],
) -> None:
    guild_players = pending_choices.get(guild_id)
    if guild_players is None:
        pending_choices[guild_id] = {}
    guild_players = pending_choices[guild_id]

    guild_players[player_id] = None


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
        resources_text[Resource.ORDERS] += (
            f" (+1 in {get_relative_timestamp(recharges[Database.Player.PlayerOrderRechargeEvent.event_type].timestamp)})"
        )

    resources_text[Resource.MAGIC] += f"/{max_magic}"
    if resources[Resource.MAGIC] < max_magic:
        resources_text[Resource.MAGIC] += (
            f" (+1 in {get_relative_timestamp(recharges[Database.Player.PlayerMagicRechargeEvent.event_type].timestamp)})"
        )

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

    region_ids_by_region_categories: defaultdict[RegionCategory, List[int]] = defaultdict(
        lambda: []
    )
    for r in regions:
        assert r.region.category is not None
        region_ids_by_region_categories[r.region.category].append(r.id)

    embed = standard_embed("Map", "All locations")

    for rc, sub_regions in region_ids_by_region_categories.items():
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


class ClaimView(discord.ui.View):
    interaction: discord.Interaction | None = None
    message: discord.Message | None = None

    def __init__(self, free_creature: Database.FreeCreature):
        super().__init__(timeout=None)
        self.free_creature = free_creature


def free_creature_embed_text(
    creature: Database.BaseCreature, roller: discord.Member
) -> Tuple[str, str, str, Optional[str]]:
    creature_title = "Roll"
    creature_text: str = f"**{creature.text()}**\n\n"
    creature_text += f"**When played**: {creature.quest_ability_effect_full_text() if creature.quest_ability_effect_full_text() else '*no special ability*'}\n"
    creature_text += f"**When sent to campaign**: {creature.campaign_ability_effect_full_text() if creature.campaign_ability_effect_full_text() else '*no special ability*'}\n\n"

    creature_text += (
        f"Can be claimed for **{creature.claim_cost}** {resource_to_emoji(Resource.RALLY)}"
    )

    return (
        creature_title,
        creature_text,
        f"Rolled by {roller}",
        roller.avatar.url if roller.avatar else None,
    )


def creature_claim_callback_factory(free_creature: Database.FreeCreature) -> Any:
    async def callback(interaction: discord.Interaction) -> None:
        player_db = free_creature.guild.get_player(interaction.user.id)
        try:
            free_creature.claim(time.time(), player_db)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error when claiming", f"Failed to claim\n ```\n{e}```")
            )

        await interaction.response.send_message(
            embed=success_embed("Claimed", f"Successfully claimed {free_creature.creature.text()}")
        )
        return

    return callback


def free_creature_embed(creature: Database.BaseCreature, roller: discord.Member) -> discord.Embed:
    creature_title, creature_text, footer_text, footer_url = free_creature_embed_text(
        creature, roller
    )

    embed = standard_embed(creature_title, creature_text)
    embed.set_footer(
        text=footer_text,
        icon_url=footer_url,
    )

    return embed


def free_creature_protected_embed(
    free_creature: Database.FreeCreature, roller: discord.Member, timestamp: float
) -> Tuple[discord.Embed, discord.ui.View]:
    creature_title, creature_text, footer_text, footer_url = free_creature_embed_text(
        free_creature.creature, roller
    )

    creature_text += (
        f"\n\nCan only be claimed by {roller.mention} until {get_relative_timestamp(timestamp)}"
    )

    embed = standard_embed(creature_title, creature_text)
    embed.set_footer(
        text=footer_text,
        icon_url=footer_url,
    )

    view = ClaimView(free_creature)
    button: discord.ui.Button[Any] = discord.ui.Button(
        label="Claim", style=discord.ButtonStyle.blurple
    )
    button.callback = creature_claim_callback_factory(free_creature)  # type: ignore
    view.add_item(button)

    return embed, view


def free_creature_claimed_embed(
    free_creature: Database.FreeCreature, roller: discord.Member, claimer: discord.Member
) -> discord.Embed:
    creature_title, creature_text, footer_text, footer_url = free_creature_embed_text(
        free_creature.creature, roller
    )

    creature_text += f"\n\nClaimed by {claimer.mention}"

    embed = standard_embed(creature_title, creature_text)
    embed.set_footer(
        text=footer_text,
        icon_url=footer_url,
    )

    return embed


def free_creature_unprotected_embed(
    free_creature: Database.FreeCreature, roller: discord.Member, timestamp: float
) -> Tuple[discord.Embed, discord.ui.View]:
    creature_title, creature_text, footer_text, footer_url = free_creature_embed_text(
        free_creature.creature, roller
    )

    creature_text += f"\n\nExpires {get_relative_timestamp(timestamp)}"

    embed = standard_embed(creature_title, creature_text)
    embed.set_footer(
        text=footer_text,
        icon_url=footer_url,
    )

    view = ClaimView(free_creature)
    button: discord.ui.Button[Any] = discord.ui.Button(
        label="Claim", style=discord.ButtonStyle.blurple
    )
    button.callback = creature_claim_callback_factory(free_creature)  # type: ignore
    view.add_item(button)

    return embed, view


def free_creature_expired_embed(
    free_creature: Database.FreeCreature, roller: discord.Member
) -> discord.Embed:
    creature_title, creature_text, footer_text, footer_url = free_creature_embed_text(
        free_creature.creature, roller
    )

    creature_text += "\n\n❌ Expired ❌"

    embed = standard_embed(creature_title, creature_text)
    embed.set_footer(
        text=footer_text,
        icon_url=footer_url,
    )

    return embed


def conflict_embed(guild: discord.Guild, guild_db: Database.Guild) -> discord.Embed:
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
    embed = format_embed(embed, guild, guild_db)

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


def format_free_creature(id: str, guild: discord.Guild, guild_db: Database.Guild) -> str:
    m = re.match(r"\((\d+),\s*(\d+)\)", id)

    if m:
        try:
            free_creature_db = guild_db.get_free_creature(int(m.group(1)), int(m.group(2)))
            return f"[{free_creature_db.creature.text()}](https://discord.com/channels/{guild.id}/{m.group(1)}/{m.group(2)})"
        except CreatureNotFound:
            return f"<free_creature:{id}>"
    else:
        return f"<free_creature:{id}>"


format_lookup: dict[str, Callable[[Any, discord.Guild, Database.Guild], str]] = {
    "player": format_player,
    "creature": format_creature,
    "region": format_region,
    "free_creature": format_free_creature,
}


def format_str(s: str, guild: discord.Guild, guild_db: Database.Guild) -> str:
    matches = list(re.findall(r"<([^:]+):(\d+)>", s)) + list(
        re.findall(r"<([^:]+):(\(\d+,\d+\))>", s)
    )

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
