import requests
from config.endpoints import (
    TEXT_MAP_EN_URL,
    LIGHT_CONE_URL,
    RELIC_PIECE_URL,
    RELIC_SET_URL,
    CHARACTERS_URL,
    EIDOLONS_URL,
    SKILLS_URL,
)


def fetch_game_data() -> dict:
    try:
        text_map_en = requests.get(TEXT_MAP_EN_URL).json()
    except Exception as e:
        print(f"Failed to fetch text map: {e}")
        return {}

    light_cones = fetch_light_cones(text_map_en)
    relics = fetch_relics(text_map_en)
    characters = fetch_characters(text_map_en)

    return {
        "light_cones": light_cones,
        "relics": relics,
        "characters": characters,
    }


def fetch_light_cones(text_map_en: dict) -> dict:
    try:
        light_cones = requests.get(LIGHT_CONE_URL).json()
    except Exception as e:
        print(f"Failed to fetch light cones: {e}")
        return {}

    res = {}
    for lc_id in light_cones:
        try:
            lc = light_cones[lc_id]
            name = text_map_en[str(lc["EquipmentName"]["Hash"])]

            res[name] = {"rarity": int(lc["Rarity"][-1])}
        except KeyError as e:
            print(f"Failed to parse light cone {lc_id}: {e}")
            continue

    return res


def fetch_relics(text_map_en: dict) -> dict:
    try:
        relic_pieces = requests.get(RELIC_PIECE_URL).json()
        relic_sets = requests.get(RELIC_SET_URL).json()
    except Exception as e:
        print(f"Failed to fetch relics: {e}")
        return {}

    res = {}
    for rset_id in relic_pieces:
        try:
            set_name = text_map_en[str(relic_sets[rset_id]["SetName"]["Hash"])]
            relics = relic_pieces[rset_id]
            for rid in relics:
                relic = relics[rid]
                name = text_map_en[_get_stable_hash(relic["RelicName"])]
                res[name] = {
                    "setKey": set_name,
                    "slotKey": _get_slot_from_relic_type(relic["Type"]),
                }

        except KeyError as e:
            print(f"Failed to parse relic set {rset_id}: {e}")
            continue

    return res


def fetch_characters(text_map_en: dict) -> dict:
    try:
        characters = requests.get(CHARACTERS_URL).json()
        eidolons = requests.get(EIDOLONS_URL).json()
        skills = requests.get(SKILLS_URL).json()
    except Exception as e:
        print(f"Failed to fetch characters: {e}")
        return {}

    res = {}
    for cid in characters:
        try:
            character = characters[cid]
            name = text_map_en[str(character["AvatarName"]["Hash"])]
            if name == "{NICKNAME}":
                name = "Trailblazer" + _get_path_from_avatar_base_type(
                    character["AvatarBaseType"]
                )
            else:
                name = " ".join([word for word in name.split() if word.isalnum()])

            e3_id = str(character["RankIDList"][2])
            e5_id = str(character["RankIDList"][4])

            res[name] = {
                "e3": _parse_skill_levels(skills, eidolons[e3_id]["SkillAddLevelList"]),
                "e5": _parse_skill_levels(skills, eidolons[e5_id]["SkillAddLevelList"]),
            }

        except KeyError as e:
            print(f"Failed to parse character {cid}: {e}")
            continue

    return res


def _get_stable_hash(s):
    hash1 = 5381
    hash2 = hash1
    max_int = 2**31 - 1  # Maximum representable positive integer in C#

    for i in range(0, len(s), 2):
        hash1 = (((hash1 << 5) + hash1) ^ ord(s[i])) & 0xFFFFFFFF
        if i < len(s) - 1:  # additional string characters available
            hash2 = (((hash2 << 5) + hash2) ^ ord(s[i + 1])) & 0xFFFFFFFF

    hash_val = (hash1 + (hash2 * 1566083941)) & 0xFFFFFFFF

    # adjust for max signed int32 value
    return str(hash_val if hash_val <= max_int else hash_val - 2**32)


def _get_slot_from_relic_type(relic_type: str) -> str:
    match relic_type:
        case "HEAD":
            return "Head"
        case "HAND":
            return "Hand"
        case "BODY":
            return "Body"
        case "FOOT":
            return "Feet"
        case "NECK":
            return "Link Rope"
        case "OBJECT":
            return "Planar Sphere"
        case _:
            raise ValueError(f"Invalid relic type: {relic_type}")


def _get_path_from_avatar_base_type(base_type: str) -> str:
    match base_type:
        case "Warrior":
            return "Destruction"
        case "Rogue":
            return "The Hunt"
        case "Mage":
            return "Erudition"
        case "Shaman":
            return "Harmony"
        case "Warlock":
            return "Nihility"
        case "Knight":
            return "Preservation"
        case "Priest":
            return "Abundance"
        case _:
            raise ValueError(f"Invalid base type: {base_type}")


def _parse_skill_levels(skills: dict, skill_add_level_dict: dict) -> dict:
    res = {}

    for sid in skill_add_level_dict:
        key = ""
        match skills[sid]["1"]["SkillTriggerKey"]:
            case "Skill01":
                key = "basic"
            case "Skill02":
                key = "skill"
            case "Skill03":
                key = "ult"
            case "SkillP01":
                key = "talent"
            case _:
                continue
        res[key] = skill_add_level_dict[sid]

    return res
