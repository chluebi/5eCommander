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


class MissingExtraData(commands.UserInputError):

    def __init__(self, message: str = "", extra_data: Optional[dict[Any, Any]] = None):
        super().__init__(message)
        self.extra_data = extra_data if extra_data is not None else {}

    def __str__(self) -> str:
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()


class BadExtraData(commands.UserInputError):

    def __init__(self, message: str = "", extra_data: Optional[dict[Any, Any]] = None):
        super().__init__(message)
        self.extra_data = extra_data if extra_data is not None else {}

    def __str__(self) -> str:
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()


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
