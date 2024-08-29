from typing import Optional, Any, List, cast, TYPE_CHECKING, Sequence

import os
import time
import copy
import asyncio
import sys
import logging
import traceback

import sqlalchemy
import sqlalchemy.exc
import discord
from discord import app_commands
from discord.ext import commands

from src.bot.setup_logging import logger, setup_logging
from src.bot.util import (
    DEVELOPMENT_GUILD,
    get_pending_choice,
    add_pending_choice,
    clear_pending_choice,
    get_relative_timestamp,
    standard_embed,
    success_embed,
    error_embed,
    player_embed,
    regions_embed,
    conflict_embed,
    creature_embed,
    free_creature_embed,
    free_creature_protected_embed,
    format_embed,
)
from src.bot.checks import guild_exists, player_exists, always_fails
from src.database.postgres import PostgresDatabase
from src.core.exceptions import GuildNotFound, PlayerNotFound, CreatureNotFound
from src.core.base_types import Resource, Price, Selected
from src.definitions.start_condition import start_condition
from src.definitions.creatures import creatures
from src.definitions.extra_data import (
    ExtraDataCategory,
    MissingExtraData,
    BadExtraData,
    Choice,
    EXTRA_DATA,
)


if TYPE_CHECKING:
    from src.bot.main import Bot


class GuildAdmin(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.hybrid_command()  # type: ignore
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def init_guild(self, ctxt: commands.Context["Bot"]) -> None:
        """Initialises the guild to play 5eCommander. Needs administator permissions."""
        assert ctxt.guild is not None

        try:
            with self.bot.db.transaction() as con:
                guild_db = self.bot.db.add_guild(ctxt.guild.id, con=con)
                config = guild_db.get_config(con=con)
                config["channel_id"] = ctxt.channel.id
                guild_db.set_config(config, con=con)

        except sqlalchemy.exc.IntegrityError as e:
            raise commands.UserInputError("Guild already exists")

        await ctxt.send(
            embed=success_embed("Guild initialised", f"Config loaded: {guild_db.get_config()}")
        )

    @commands.hybrid_command()  # type: ignore
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.check(guild_exists)
    async def delete_guild(
        self, ctxt: commands.Context["Bot"], confirm: Optional[str] = "no"
    ) -> None:
        """Initialises the guild to play 5eCommander. Needs administator permissions."""
        assert ctxt.guild is not None

        if confirm != "Yes I confirm that I understand that all data will be deleted":
            await ctxt.send(
                embed=error_embed(
                    "Confirm",
                    "The confirmation must be exactly 'Yes I confirm that I understand that all data will be deleted'.",
                )
            )
            return

        guild_db = self.bot.db.get_guild(ctxt.guild.id)
        self.bot.db.remove_guild(guild_db)

        await ctxt.send(
            embed=success_embed("Guild Removed", "All data relating to this guild removed")
        )

    @commands.hybrid_command()  # type: ignore
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.check(guild_exists)
    async def guild_info(self, ctxt: commands.Context["Bot"]) -> None:
        """Gives you the guild configuration"""
        assert ctxt.guild is not None

        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        await ctxt.send(
            embed=success_embed(
                "Guild initialised",
                f"Server config: ``{guild_db.get_config()}``\n Events: ``{guild_db.get_events(0, time.time())}``",
            )
        )

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(guild_exists)
    async def map(self, ctxt: commands.Context["Bot"]) -> None:
        """Gives you info about the locations in the game"""
        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        await ctxt.send(embed=regions_embed(guild_db))

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(guild_exists)
    async def conflict(self, ctxt: commands.Context["Bot"]) -> None:
        """Gives you info about the current conflict in the guild"""
        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        await ctxt.send(embed=conflict_embed(ctxt.guild, guild_db))


class PlayerAdmin(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(guild_exists)
    async def join(self, ctxt: commands.Context["Bot"]) -> None:
        """Join the game"""
        if ctxt.guild is None:
            await ctxt.send(embed=error_embed("User Error", "You are not currently in a guild."))
            return

        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        try:
            player_db = guild_db.add_player(ctxt.author.id)
        except sqlalchemy.exc.IntegrityError as e:
            await ctxt.send(embed=error_embed("User Error", "You already joined"))
            return

        await ctxt.send(embed=success_embed("Success", "You have joined the game!"))

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def player_info(self, ctxt: commands.Context["Bot"], *, member: discord.Member) -> None:
        """Gives you the info about a player"""
        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        try:
            player_db = guild_db.get_player(member.id)
        except PlayerNotFound as e:
            await ctxt.send(embed=error_embed("User Error", "No player of this name found"))
            return

        await ctxt.send(embed=player_embed(member, player_db, private=True))

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def me(self, ctxt: commands.Context["Bot"]) -> None:
        """Gives you the info about yourself, privately"""
        if ctxt.interaction is None:
            raise commands.CheckFailure("This command can only be called as a slash command")

        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)
        player_db = guild_db.get_player(ctxt.author.id)

        assert isinstance(ctxt.author, discord.Member)

        await ctxt.send(embed=player_embed(ctxt.author, player_db, private=False), ephemeral=True)

    async def _play(
        self, ctxt: commands.Context["Bot"], card: int, region: int, extra_data: EXTRA_DATA
    ) -> None:
        assert ctxt.guild is not None

        try:
            with self.bot.db.transaction() as con:
                guild_db = self.bot.db.get_guild(ctxt.guild.id, con=con)
                player_db = guild_db.get_player(ctxt.author.id, con=con)

                creatures = player_db.get_hand(con=con)
                creature_db = [c for c in creatures if c.id == card][0]

                regions = guild_db.get_regions(con=con)
                region_db = [r for r in regions if r.id == region][0]

                player_db.play_creature_to_region(
                    creature_db, region_db, con=con, extra_data=extra_data
                )

                clear_pending_choice(ctxt.guild.id, ctxt.author.id, self.bot.pending_choices)

                await ctxt.send(
                    embed=success_embed(
                        "Creature Played",
                        f"Successfully played {creature_db.text()} to {region_db.text()}",
                    )
                )

        except MissingExtraData as e:

            async def callback(ctxt: commands.Context["Bot"], extra_data: EXTRA_DATA) -> None:
                await self._play(ctxt, card, region, extra_data)

            add_pending_choice(
                ctxt.guild.id,
                ctxt.author.id,
                e.choice,
                callback,
                extra_data,
                self.bot.pending_choices,
            )

            await ctxt.send(
                embed=standard_embed(
                    "Choice needed",
                    f"{e.choice.text}\n\nUse ``/choose`` to make your choice.",
                )
            )

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def play(self, ctxt: commands.Context["Bot"], card: int, region: int) -> None:
        """Uses a order to play a card to a region"""
        await self._play(ctxt, card, region, [])

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def play_to(self, ctxt: commands.Context["Bot"], region: int, card: int) -> None:
        """Uses a order to play a card to a region, but region is chosen first"""
        await self._play(ctxt, card, region, [])

    @play.autocomplete("card")
    @play_to.autocomplete("card")
    async def play_card_in_hand_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None
        guild_db = self.bot.db.get_guild(interaction.guild.id)
        player_db = guild_db.get_player(interaction.user.id)
        creatures = player_db.get_hand()

        print("namespace", interaction.namespace)

        if "region" in interaction.namespace and cast(int, interaction.namespace["region"]) != 0:
            region_id = cast(int, interaction.namespace["region"])
            region = guild_db.get_region(region_id)
            filtered_creatures = [
                c for c in creatures if region.region.category in c.creature.quest_region_categories
            ]
        else:
            filtered_creatures = creatures

        return [
            discord.app_commands.Choice(
                name=(
                    f"{c.text()}: {c.creature.quest_ability_effect_full_text()}"
                    if c.creature.quest_ability_effect_full_text()
                    else c.text()
                ),
                value=c.id,
            )
            for c in filtered_creatures
            if current in f"{c.text()}: {c.creature.quest_ability_effect_full_text()}"
        ]

    @play.autocomplete("region")
    @play_to.autocomplete("region")
    async def region_to_play_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None

        guild_db = self.bot.db.get_guild(interaction.guild.id)
        regions = guild_db.get_regions()
        regions = [r for r in regions if r.occupied() == (None, None)]

        if "card" in interaction.namespace and cast(int, interaction.namespace["card"]) != 0:
            creature_id = cast(int, interaction.namespace["card"])
            player_db = guild_db.get_player(interaction.user.id)
            creatures = player_db.get_hand()
            creatures_filtered = [c for c in creatures if c.id == creature_id]
            if len(creatures_filtered) < 1:
                filtered_regions = regions
            else:
                creature = creatures_filtered[0]
                filtered_regions = [
                    r
                    for r in regions
                    if r.region.category in creature.creature.quest_region_categories
                ]
        else:
            filtered_regions = regions

        return [
            discord.app_commands.Choice(
                name=f"{r.text()}: {r.region.quest_effect_full_text()}", value=r.id
            )
            for r in filtered_regions
            if current in f"{r.text()}: {r.region.quest_effect_full_text()}"
        ]

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def campaign(self, ctxt: commands.Context["Bot"], card: int) -> None:
        """Play a creature to the campaign. Creature is out of deck until campaign ends."""
        assert ctxt.guild is not None

        with self.bot.db.transaction() as con:
            guild_db = self.bot.db.get_guild(ctxt.guild.id, con=con)
            player_db = guild_db.get_player(ctxt.author.id, con=con)

            creatures = player_db.get_hand(con=con)
            creature_db = [c for c in creatures if c.id == card][0]

            player_db.play_creature_to_campaign(creature_db, con=con)

            await ctxt.send(
                embed=success_embed(
                    "Creature Campaigned",
                    f"Successfully sent {creature_db.text()} to campaign",
                )
            )

    @campaign.autocomplete("card")
    async def campaign_card_in_hand_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None
        guild_db = self.bot.db.get_guild(interaction.guild.id)
        player_db = guild_db.get_player(interaction.user.id)
        creatures = player_db.get_hand()

        return [
            discord.app_commands.Choice(
                name=(
                    f"{c.text()}: {c.creature.campaign_ability_effect_full_text()}"
                    if c.creature.campaign_ability_effect_full_text()
                    else c.text()
                ),
                value=c.id,
            )
            for c in creatures
            if c.text().startswith(current)
        ]

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def choose(self, ctxt: commands.Context["Bot"], choice: int) -> None:
        """Make a choice depending on previous commands."""
        assert ctxt.guild is not None

        pending = get_pending_choice(ctxt.guild.id, ctxt.author.id, self.bot.pending_choices)
        if pending is None:
            await ctxt.send(
                embed=error_embed(
                    "No choice to be made",
                    "You do not have a current command open you can make a choice about",
                ),
                ephemeral=True,
            )
            return

        with self.bot.db.transaction() as con:
            guild_db = self.bot.db.get_guild(ctxt.guild.id, con=con)
            player_db = guild_db.get_player(ctxt.author.id, con=con)

            choice_obj, callback, extra_data = pending
            if extra_data:
                extra_data = copy.deepcopy(extra_data)
            else:
                extra_data = []

            new_selected = choice_obj.select_option(player_db, choice_obj, choice, con)
            extra_data.append(new_selected)

            await callback(ctxt, extra_data)

    @choose.autocomplete("choice")
    async def choice_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None

        pending = get_pending_choice(
            interaction.guild.id, interaction.user.id, self.bot.pending_choices
        )
        if pending is None:
            return []

        choice, _, _ = pending

        guild_db = self.bot.db.get_guild(interaction.guild.id)
        player_db = guild_db.get_player(interaction.user.id)

        options = choice.get_options(player_db, None)

        return [
            discord.app_commands.Choice(
                name=(o.text()),
                value=o.value(),
            )
            for o in options
            if current in o.text()
        ][:20]

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(guild_exists)
    async def card(self, ctxt: commands.Context["Bot"], card: int) -> None:
        """Shows the info about a card"""
        assert ctxt.guild is not None
        guild_db = self.bot.db.get_guild(ctxt.guild.id)

        with self.bot.db.transaction() as con:
            basecreature = creatures.get(card)
            if basecreature is None or basecreature not in guild_db.get_all_obtainable_basecreatures(con=con):
                raise CreatureNotFound(message="Creature not found")

            await ctxt.send(embed=creature_embed(basecreature))

    @card.autocomplete("card")
    async def card_in_guild_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[int]]:
        assert interaction.guild is not None
        guild_db = self.bot.db.get_guild(interaction.guild.id)
        basecreatures = guild_db.get_all_obtainable_basecreatures()

        return [
            discord.app_commands.Choice(
                name=(f"{c.text()}"),
                value=c.id,
            )
            for c in basecreatures
            if c.text().startswith(current)
        ]

    @commands.hybrid_command()  # type: ignore
    @commands.guild_only()
    @commands.check(player_exists)
    async def roll(self, ctxt: commands.Context["Bot"], amount: int = 1) -> None:
        """Roll for new creatures"""
        assert ctxt.guild is not None

        with self.bot.db.transaction() as con:
            guild_db = self.bot.db.get_guild(ctxt.guild.id, con=con)
            player_db = guild_db.get_player(ctxt.author.id, con=con)
            creatures = [guild_db.roll_creature(con=con) for i in range(amount)]

        for c in creatures:
            with self.bot.db.transaction() as con:
                player_db.pay_price([Price(resource=Resource.MAGIC, amount=1)], con=con)

                embed = free_creature_embed(c, cast(discord.Member, ctxt.author))
                message = await ctxt.send(embed=embed)
                free_creature = guild_db.add_free_creature(
                    c, ctxt.channel.id, message.id, player_db, con=con
                )
                free_creature.create_events(con=con)

                embed, view = free_creature_protected_embed(
                    free_creature,
                    cast(discord.Member, ctxt.author),
                    free_creature.get_protected_timestamp(con=con),
                )

                await message.edit(embed=embed, view=view)

            await asyncio.sleep(0.5)


async def setup(bot: "Bot") -> None:
    await bot.add_cog(GuildAdmin(bot))
    await bot.add_cog(PlayerAdmin(bot))
