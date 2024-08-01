class GuildNotFound(Exception):
    pass


class PlayerNotFound(Exception):
    pass


class CreatureNotFound(Exception):
    pass


class RegionNotFound(Exception):
    pass


class NotEnoughResourcesException(Exception):
    pass


class EmptyDeckException(Exception):
    pass


class MissingExtraData(Exception):

    def __init__(self, message="", extra_data=None):
        super().__init__(message)
        self.extra_data = extra_data if extra_data is not None else {}

    def __str__(self):
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()


class BadExtraData(Exception):

    def __init__(self, message="", extra_data=None):
        super().__init__(message)
        self.extra_data = extra_data if extra_data is not None else {}

    def __str__(self):
        if self.extra_data:
            return f"{super().__str__()} (Extra data: {self.extra_data})"
        return super().__str__()


class CreatureCannotQuestHere(Exception):
    pass


class ProtectedFreeCreature(Exception):
    pass


class ExpiredFreeCreature(Exception):
    pass


class CreatureCannotCampaign(Exception):
    pass
