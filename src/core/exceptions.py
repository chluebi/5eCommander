from __future__ import annotations
from typing import Any, Optional

from discord.ext import commands


class GuildNotFound(commands.UserInputError):
    pass


class PlayerNotFound(commands.UserInputError):
    pass


class CreatureNotFound(commands.UserInputError):
    pass


class RegionNotFound(commands.UserInputError):
    pass


class NotEnoughResourcesException(commands.UserInputError):
    pass


class EmptyDeckException(commands.UserInputError):
    pass


class CreatureCannotQuestHere(commands.UserInputError):
    pass


class ProtectedFreeCreature(commands.UserInputError):
    pass


class ExpiredFreeCreature(commands.UserInputError):
    pass


class CreatureCannotQuest(commands.UserInputError):
    def __init__(self) -> None:
        super().__init__("Creature cannot quest.")


class CreatureCannotCampaign(commands.UserInputError):
    def __init__(self) -> None:
        super().__init__("Creature cannot campaign.")
