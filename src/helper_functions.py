import sys
import os
import json
import datetime
import cv2
import numpy as np
import pytesseract
from PIL import ImageFilter, Image

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
            if (pixel[0] > 170 and pixel[1] > 170 and pixel[2] > 170) or (210 < pixel[0] < 230 and 190 < pixel[1] < 200 and 140 < pixel[2] < 150):
                # img.putpixel((x, y), (255, 255, 255))
                pass
            else:
                img.putpixel(
                    (x, y), (0, 0, 0))
    # img = cv2.resize(np.array(img), None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # img = img.convert('L')
    img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)
    # cv2.adaptiveThreshold(cv2.medianBlur(img, 9), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
    # img = img.filter(ImageFilter.EDGE_ENHANCE)
    # img = img.filter(ImageFilter.GaussianBlur(radius=1))

    kernel = np.ones((1, 1))
    img = cv2.dilate(img, kernel, iterations=1)
    img = cv2.erode(img, kernel, iterations=1)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    img = cv2.medianBlur(img, 3)

    # return image from numpy array
    img = Image.fromarray(img)
    return img
