from typing import Callable

from models.const import (
    ABILITY_1,
    ABILITY_2,
    ABILITY_3,
    BASIC,
    CHAR_ASCENSION,
    CHAR_EIDOLON,
    CHAR_ID,
    CHAR_LEVEL,
    CHAR_SKILLS,
    CHAR_TRACES,
    LC_ASCENSION,
    LC_LEVEL,
    LC_LOCATION,
    LC_LOCK,
    LC_NAME,
    LC_SUPERIMPOSITION,
    RELIC_DISCARD,
    RELIC_LEVEL,
    RELIC_LOCATION,
    RELIC_LOCK,
    RELIC_MAINSTAT,
    RELIC_NAME,
    RELIC_RARITY,
    RELIC_SLOT,
    RELIC_SUBSTAT_NAME,
    RELIC_SUBSTAT_VALUE,
    RELIC_SUBSTATS,
    SKILL,
    STAT_1,
    STAT_10,
    STAT_2,
    STAT_3,
    STAT_4,
    STAT_5,
    STAT_6,
    STAT_7,
    STAT_8,
    STAT_9,
    TALENT,
    ULT,
)
from models.game_data import GameData

SRO_SLOT_MAP = {
    "Head": "head",
    "Hands": "hand",
    "Body": "body",
    "Feet": "feet",
    "Planar Sphere": "sphere",
    "Link Rope": "rope",
}

SRO_MAIN_STAT_MAP = {
    "SPD": "spd",
    "HP": "hp",
    "ATK": "atk",
    "DEF": "def",
    "Break Effect": "brEff",
    "Effect Hit Rate": "eff",
    "Energy Regeneration Rate": "enerRegen",
    "Outgoing Healing Boost": "heal",
    "Physical DMG Boost": "physical_dmg",
    "Fire DMG Boost": "fire_dmg",
    "Ice DMG Boost": "ice_dmg",
    "Wind DMG Boost": "wind_dmg",
    "Lightning DMG Boost": "lightning_dmg",
    "Quantum DMG Boost": "quantum_dmg",
    "Imaginary DMG Boost": "imaginary_dmg",
    "CRIT Rate": "crit",
    "CRIT DMG": "crit_dmg",
}

SRO_SUB_STAT_MAP = {
    "HP": "hp",
    "ATK": "atk",
    "DEF": "def",
    "HP_": "hp_",
    "ATK_": "atk_",
    "DEF_": "def_",
    "SPD": "spd",
    "CRIT Rate_": "crit_",
    "CRIT DMG_": "crit_dmg_",
    "Effect Hit Rate_": "eff_",
    "Effect RES_": "eff_res_",
    "Break Effect_": "brEff_",
}


def convert_to_sro(data: dict, game_data: GameData) -> dict:
    """Reformat data to SRO format

    :param data: The data to reformat
    :param game_data: The GameData class instance
    :return: The reformatted data
    """
    res = {
        "format": "SRO",
        "source": "HSR-Scanner",
        "version": 1,
    }

    sro_mappings = game_data.get_sro_mappings()
    get_sro_character_key = lambda key: _get_sro_character_key(key, sro_mappings)

    if data["characters"]:
        res["characters"] = _convert_characters_sro(
            data["characters"], get_sro_character_key
        )

    if data["relics"]:
        res["relics"] = _convert_relics_sro(
            data["relics"], sro_mappings, get_sro_character_key
        )

    if data["light_cones"]:
        res["lightCones"] = _convert_light_cones_sro(
            data["light_cones"], sro_mappings, get_sro_character_key
        )
    return res


def _convert_characters_sro(
    characters: list[dict], character_key_fn: Callable
) -> list[dict]:
    """Convert characters to SRO format

    :param characters: The characters to convert
    :param character_key_fn: The function to get the SRO character key
    :return: The converted characters
    """
    formatted_characters = []
    for character in characters:
        res = {
            "key": character_key_fn(character[CHAR_ID]),
            "level": character[CHAR_LEVEL],
            "eidolon": character[CHAR_EIDOLON],
            "ascension": character[CHAR_ASCENSION],
            "basic": character[CHAR_SKILLS][BASIC],
            "skill": character[CHAR_SKILLS][SKILL],
            "ult": character[CHAR_SKILLS][ULT],
            "talent": character[CHAR_SKILLS][TALENT],
            "bonusAbilities": {
                1: character[CHAR_TRACES][ABILITY_1],
                2: character[CHAR_TRACES][ABILITY_2],
                3: character[CHAR_TRACES][ABILITY_3],
            },
            "statBoosts": {
                1: character[CHAR_TRACES][STAT_1],
                2: character[CHAR_TRACES][STAT_2],
                3: character[CHAR_TRACES][STAT_3],
                4: character[CHAR_TRACES][STAT_4],
                5: character[CHAR_TRACES][STAT_5],
                6: character[CHAR_TRACES][STAT_6],
                7: character[CHAR_TRACES][STAT_7],
                8: character[CHAR_TRACES][STAT_8],
                9: character[CHAR_TRACES][STAT_9],
                10: character[CHAR_TRACES][STAT_10],
            },
        }
        formatted_characters.append(res)

    return formatted_characters


def _convert_relics_sro(
    relics: list[dict], sro_mappings: dict, character_key_fn: Callable
) -> list[dict]:
    """Convert relics to SRO format

    :param relics: The relics to convert
    :param sro_mappings: The SRO key mappings
    :param character_key_fn: The function to get the SRO character key
    :return: The converted relics
    """
    formatted_relics = []
    for relic in relics:
        mainstat = SRO_MAIN_STAT_MAP[relic[RELIC_MAINSTAT]]
        if relic[RELIC_SLOT] not in ["Head", "Hands"] and relic["mainstat"] != "SPD":
            mainstat += "_"

        substats = []
        for substat in relic[RELIC_SUBSTATS]:
            try:
                value = (
                    round(substat[RELIC_SUBSTAT_VALUE] / 100, 3)
                    if substat[RELIC_SUBSTAT_NAME].endswith("_")
                    else substat[RELIC_SUBSTAT_VALUE]
                )
                substats.append(
                    {
                        "key": SRO_SUB_STAT_MAP[substat[RELIC_SUBSTAT_NAME]],
                        "value": value,
                    }
                )
            except KeyError:
                pass

        res = {
            "setKey": sro_mappings["relic_sets"][relic[RELIC_NAME]],
            "slotKey": SRO_SLOT_MAP[relic[RELIC_SLOT]],
            "level": relic[RELIC_LEVEL],
            "rarity": relic[RELIC_RARITY],
            "mainstat": mainstat,
            "location": character_key_fn(relic[RELIC_LOCATION]),
            "lock": relic[RELIC_LOCK],
            "discard": relic[RELIC_DISCARD],
            "substats": substats,
        }
        formatted_relics.append(res)

    return formatted_relics


def _convert_light_cones_sro(
    light_cones: list[dict], sro_mappings: dict, character_key_fn: Callable
) -> list[dict]:
    """Convert light cones to SRO format

    :param light_cones: The light cones to convert
    :param sro_mappings: The SRO key mappings
    :param character_key_fn: The function to get the SRO character key
    :return: The converted light cones
    """
    formatted_light_cones = []
    for light_cone in light_cones:
        res = {
            "key": sro_mappings["light_cones"][light_cone[LC_NAME]],
            "level": light_cone[LC_LEVEL],
            "ascension": light_cone[LC_ASCENSION],
            "superimpose": light_cone[LC_SUPERIMPOSITION],
            "location": character_key_fn(light_cone[LC_LOCATION]),
            "lock": light_cone[LC_LOCK],
        }
        formatted_light_cones.append(res)

    return formatted_light_cones


def _get_sro_character_key(key: str, sro_mappings: dict) -> str:
    """Get the SRO character key

    :param key: The character key
    :param sro_mappings: The SRO key mappings
    :return: The SRO character key
    """
    if not key:
        return ""
    return sro_mappings["characters"][key]
