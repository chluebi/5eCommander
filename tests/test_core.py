from typing import Optional
import time

from src.definitions.creatures import *
from src.definitions.regions import *


def test_text() -> None:
    commoner = Commoner()

    assert commoner.quest_ability_effect_full_text() == ""
    assert commoner.quest_ability_effect_short_text() == ""
    assert commoner.campaign_ability_effect_full_text() == "gain 1 🚩rally"
    assert commoner.campaign_ability_effect_short_text() == "+1🚩"

    village = Village()

    assert village.quest_effect_full_text() == "gain 1 🤫intel"
    assert village.quest_effect_short_text() == "+1🤫"

    small_mine = SmallMine()

    assert small_mine.quest_effect_full_text() == "pay 1 🤫intel. gain 5 🪙gold."
    assert small_mine.quest_effect_short_text() == "-1🤫 -> +5🪙"
