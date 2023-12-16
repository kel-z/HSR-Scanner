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
    trailblazer_suffix = "F" if game_data.is_trailblazer_female else "M"
    get_sro_character_key = lambda key: _get_sro_character_key(
        key, sro_mappings, trailblazer_suffix
    )

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
    characters: list[dict], character_key_fn: callable
) -> list[dict]:
    """Convert characters to SRO format

    :param characters: The characters to convert
    :param character_key_fn: The function to get the SRO character key
    :return: The converted characters
    """
    formatted_characters = []
    for character in characters:
        res = {
            "key": character_key_fn(character["key"]),
            "level": character["level"],
            "eidolon": character["eidolon"],
            "ascension": character["ascension"],
            "basic": character["skills"]["basic"],
            "skill": character["skills"]["skill"],
            "ult": character["skills"]["ult"],
            "talent": character["skills"]["talent"],
            "bonusAbilities": {
                1: character["traces"]["ability_1"],
                2: character["traces"]["ability_2"],
                3: character["traces"]["ability_3"],
            },
            "statBoosts": {
                1: character["traces"]["stat_1"],
                2: character["traces"]["stat_2"],
                3: character["traces"]["stat_3"],
                4: character["traces"]["stat_4"],
                5: character["traces"]["stat_5"],
                6: character["traces"]["stat_6"],
                7: character["traces"]["stat_7"],
                8: character["traces"]["stat_8"],
                9: character["traces"]["stat_9"],
                10: character["traces"]["stat_10"],
            },
        }
        formatted_characters.append(res)

    return formatted_characters


def _convert_relics_sro(
    relics: list[dict], sro_mappings: dict, character_key_fn: callable
) -> list[dict]:
    """Convert relics to SRO format

    :param relics: The relics to convert
    :param sro_mappings: The SRO key mappings
    :param character_key_fn: The function to get the SRO character key
    :return: The converted relics
    """
    formatted_relics = []
    for relic in relics:
        mainStatKey = SRO_MAIN_STAT_MAP[relic["mainstat"]]
        if relic["slot"] not in ["Head", "Hands"] and relic["mainstat"] != "SPD":
            mainStatKey += "_"

        substats = []
        for substat in relic["substats"]:
            try:
                substats.append(
                    {
                        "key": SRO_SUB_STAT_MAP[substat["key"]],
                        "value": substat["value"],
                    }
                )
            except KeyError:
                pass

        res = {
            "setKey": sro_mappings["relic_sets"][relic["set"]],
            "slotKey": SRO_SLOT_MAP[relic["slot"]],
            "level": relic["level"],
            "rarity": relic["rarity"],
            "mainStatKey": mainStatKey,
            "location": character_key_fn(relic["location"]),
            "lock": relic["lock"],
            "substats": substats,
        }
        formatted_relics.append(res)

    return formatted_relics


def _convert_light_cones_sro(
    light_cones: list[dict], sro_mappings: dict, character_key_fn: callable
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
            "key": sro_mappings["light_cones"][light_cone["key"]],
            "level": light_cone["level"],
            "ascension": light_cone["ascension"],
            "superimpose": light_cone["superimposition"],
            "location": character_key_fn(light_cone["location"]),
            "lock": light_cone["lock"],
        }
        formatted_light_cones.append(res)

    return formatted_light_cones


def _get_sro_character_key(
    key: str, sro_mappings: dict, trailblazer_suffix: str
) -> str:
    """Get the SRO character key

    :param key: The character key
    :param sro_mappings: The SRO key mappings
    :param trailblazer_suffix: The Trailblazer suffix
    :return: The SRO character key
    """
    if not key:
        return ""
    sro_key = sro_mappings["characters"][key]
    if "Trailblazer" in key:
        sro_key += trailblazer_suffix

    return sro_key
