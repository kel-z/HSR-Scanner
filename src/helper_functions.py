import sys
import os
import json
import datetime
import pytesseract
from PIL import ImageFilter

# https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(
        os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def executable_path(path):
    return os.path.join(os.path.dirname(sys.executable), path)


def save_to_json(data, output_location):
    if not os.path.exists(output_location):
        os.makedirs(output_location)

    file_name = f"HSRScanData_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(os.path.join(output_location, file_name), 'w') as outfile:
        json.dump(data, outfile, indent=4)


def image_to_string(img, whitelist, psm, force_preprocess=False):
    config = f"-c tessedit_char_whitelist=\"{whitelist}\" --psm {psm}"

    res = ""
    if not force_preprocess:
        res = pytesseract.image_to_string(
            img, config=config).replace("\n", " ").strip()

    if not res:
        res = pytesseract.image_to_string(
            preprocess_img(img), config=config).replace("\n", " ").strip()

    return res


def preprocess_img(img):
    if img.height < 50:
        img = img.resize((img.width * 2, img.height * 2))

    for x in range(img.width):
        for y in range(img.height):
            pixel = img.getpixel((x, y))
            if pixel[0] > 150 and pixel[1] > 150 and pixel[2] > 150:
                img.putpixel((x, y), (255, 255, 255))
            else:
                img.putpixel(
                    (x, y), (pixel[0] - 75, pixel[1] - 75, pixel[2] - 75))

    img = img.convert('L')
    img = img.filter(ImageFilter.EDGE_ENHANCE)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))

    return img
