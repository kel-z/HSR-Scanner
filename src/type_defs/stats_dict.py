from typing import TypedDict
from PIL.Image import Image


class RelicDict(TypedDict):
    """Intermediate dictionary for relic data."""

    name: Image | str
    level: Image | int
    discard: Image
    lock: Image
    rarity: Image | int
    equipped: Image
    equipped_avatar: Image
    equipped_avatar_trailblazer: Image
    mainstat: Image | str
    substat_names: Image | str
    substat_vals: Image | str


class LightConeDict(TypedDict):
    """Intermediate dictionary for light cone data."""

    name: Image | str
    level: Image | str
    rarity: int
    superimposition: Image | int
    equipped: Image
    equipped_avatar: Image
    equipped_avatar_trailblazer: Image
    lock: Image
