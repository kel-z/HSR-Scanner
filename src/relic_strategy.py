from utils.game_data import GameData
import numpy as np
import pytesseract
from file_helpers import resource_path
from PIL import Image
from pyautogui import locate


class RelicStrategy:
    scan_type = 1
    nav_data = {
        "16:9": {
            "inv_tab": (0.43, 0.06),
            "row_start_top": (0.1, 0.25),
            "row_start_bottom": (0.1, 0.77),
            "scroll_start_y": 0.85,
            "scroll_end_y": 0.186,
            "offset_x": 0.075,
            "offset_y": 0.157,
            "rows": 4,
            "cols": 8
        }
    }

    def __init__(self, screenshot, logger):
        self._lock_icon = Image.open(resource_path("./images/lock.png"))
        self._screenshot = screenshot
        self._logger = logger

    def screenshot_stats(self):
        return self._screenshot.screenshot_relic_stats()

    def parse(self, img_dict, _id, interrupt):
        if interrupt.is_set():
            return

        # Preprocess
        for k in img_dict:
            if k not in {"name", "mainStatKey", "rarity_sample", "lock", "equipped", "equipped_avatar"}:
                self._screenshot.preprocess_img(img_dict[k])

        # Get each cropped img
        name = img_dict["name"]
        level = img_dict["level"]
        mainStatKey = img_dict["mainStatKey"]
        lock = img_dict["lock"]
        rarity_sample = img_dict["rarity_sample"]
        equipped = img_dict["equipped"]

        # OCR
        name = pytesseract.image_to_string(
            name, config="-c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZ \'abcedfghijklmnopqrstuvwxyz-\" --psm 6")
        level = pytesseract.image_to_string(
            level, config='-c tessedit_char_whitelist=0123456789 --psm 7')
        mainStatKey = pytesseract.image_to_string(
            mainStatKey, config='-c tessedit_char_whitelist=\'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz\' --psm 7')
        equipped = pytesseract.image_to_string(
            equipped, config='-c tessedit_char_whitelist=Equipped --psm 7')

        # Clean up
        name = name.strip().replace("\n", " ")
        level = level.strip()
        mainStatKey = mainStatKey.strip()
        equipped = equipped.strip()

        # Fix OCR errors
        name, _ = GameData.get_closest_relic_name(name)
        mainStatKey, _ = GameData.get_closest_relic_main_stat(mainStatKey)

        # Parse substats
        subStats = []
        for i in range(1, 5):
            key = img_dict["subStatKey_" + str(i)]
            val = img_dict["subStatVal_" + str(i)]

            key = pytesseract.image_to_string(
                key, config='-c tessedit_char_whitelist=\'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz\' --psm 7')
            val = pytesseract.image_to_string(
                val, config='-c tessedit_char_whitelist=0123456789.% --psm 7')

            key = key.strip()
            val = val.strip()

            key, min_dist = GameData.get_closest_relic_sub_stat(key)
            if min_dist > 5:
                break

            if len(val) == 0:
                self._logger.emit(
                    f"Relic ID {_id}: Found substat with no value: {key}. Either it doesn't exist or the OCR failed.")
                break

            if val[-1] == '%':
                val = float(val[:-1])
                key += '_'
            else:
                val = int(val)

            subStats.append(
                {
                    "key": key,
                    "value": val
                }
            )

        metadata = GameData.get_relic_meta_data(name)
        setKey = metadata["setKey"]
        slotKey = metadata["slotKey"]

        # Get rarity by color matching
        rarity_sample = np.array(rarity_sample)
        rarity_sample = rarity_sample[int(
            rarity_sample.shape[0]/2)][int(rarity_sample.shape[1]/2)]

        rarity = GameData.get_closest_rarity(rarity_sample)

        # Check if locked by image matching
        min_dim = min(lock.size)
        locked = self._lock_icon.resize((min_dim, min_dim))
        if locate(locked, lock, confidence=0.1):
            lock = True
        else:
            lock = False

        location = ""
        if equipped == "Equipped":
            equipped_avatar = img_dict["equipped_avatar"]

            location = GameData.get_equipped_character(
                equipped_avatar, resource_path("./images/avatars/"))

        result = {
            "setKey": setKey,
            "slotKey": slotKey,
            "rarity": rarity,
            "level": int(level),
            "mainStatKey": mainStatKey,
            "subStats": subStats,
            "location": location,
            "lock": lock,
            "id": _id
        }

        return result
