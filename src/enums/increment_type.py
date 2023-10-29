from enum import Enum


class IncrementType(Enum):
    """IncrementType enum for incrementing the counts"""

    LIGHT_CONE_ADD = 0
    LIGHT_CONE_SUCCESS = 100
    RELIC_ADD = 1
    RELIC_SUCCESS = 101
    CHARACTER_ADD = 2
    CHARACTER_SUCCESS = 102
