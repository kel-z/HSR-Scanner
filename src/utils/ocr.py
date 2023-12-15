import cv2
import numpy as np
import pytesseract
from PIL import Image


def preprocess_img(img: Image) -> Image:
    """Preprocess image

    :param img: The image to preprocess
    :return: The preprocessed image
    """

    return _preprocess_img_by_colour_filter(img, (255, 255, 255), 80)


def image_to_string(
    img: Image,
    whitelist: str,
    psm: int,
    force_preprocess=False,
    preprocess_func=preprocess_img,
    remove_newline=True,
) -> str:
    """Convert image to string

    :param img: The image to convert
    :param whitelist: The whitelist of characters to use
    :param psm: The page segmentation mode to use
    :param force_preprocess: The flag to force preprocessing, defaults to False
    :param preprocess_func: The preprocessing function to use, defaults to None
    :param strip_text: The flag to strip text, defaults to True
    :return: The string representation of the image
    """
    config = f'-c tessedit_char_whitelist="{whitelist}" --psm {psm} -l DIN-Alternate'

    res = ""
    if not force_preprocess:
        res = pytesseract.image_to_string(img, config=config)

    if not res.strip():
        res = pytesseract.image_to_string(preprocess_func(img), config=config)

    if remove_newline:
        res = res.replace("\n", " ")

    return res.strip()


def preprocess_char_count_img(img: Image) -> Image:
    """Preprocess character count image in the Data Bank screen

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, (218, 194, 145), 30)


def preprocess_lc_level_img(img: Image) -> Image:
    """Preprocess light cone level image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, [(255, 255, 255), (239, 160, 61)], 80)


def preprocess_trace_img(img: Image) -> Image:
    """Preprocess trace image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    img = _preprocess_img_by_colour_filter(
        img,
        [
            (255, 255, 255),
            (212, 214, 214),
            (160, 166, 175),
            (45, 240, 240),
            (26, 145, 150),
            (33, 180, 182),
            (38, 212, 206),
            (14, 77, 82),
        ],
        [50, 50, 20, 20, 30, 30, 15, 10],
    )
    return img


def preprocess_equipped_img(img: Image) -> Image:
    """Preprocess equipped image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, (202, 177, 134), 75)


def preprocess_main_stat_img(img: Image) -> Image:
    """Preprocess main stat image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, (226, 155, 61), 50)


def preprocess_sub_stat_img(img: Image) -> Image:
    """Preprocess sub stat image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    img = _preprocess_img_by_colour_filter(img, (255, 255, 255), 100)
    return img


def preprocess_superimposition_img(img: Image) -> Image:
    """Preprocess superimposition image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    img = _preprocess_img_by_colour_filter(img, (220, 196, 145), 50)
    return img


def _preprocess_img_by_colour_filter(
    img: Image, colour: tuple | list[tuple], variance: int | list[int]
) -> Image:
    """Preprocess image by filtering out colours that are not within the variance of the colour

    :param img: The image to preprocess
    :param colour: The colour or list of colours to filter
    :param variance: The variance or list of variances to use for each colour
    :return: The preprocessed image
    """
    if isinstance(colour, tuple):
        colour = [colour]
    if isinstance(variance, int):
        variance = [variance] * len(colour)

    if len(colour) != len(variance):
        raise ValueError(
            f"Length of colour ({len(colour)}) and variance ({len(variance)}) must be the same"
        )

    img_arr = np.array(img)

    mask = np.zeros(img_arr.shape[:2], dtype="uint8")
    for c, v in zip(colour, variance):
        lower = np.array([max(0, c - v) for c in c], dtype="uint8")
        upper = np.array([min(255, c + v) for c in c], dtype="uint8")
        mask = cv2.bitwise_or(mask, cv2.inRange(img_arr, lower, upper))

    img_arr = cv2.bitwise_and(img_arr, img_arr, mask=mask)
    img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)

    # blur
    img_arr = cv2.GaussianBlur(img_arr, (3, 3), 1)

    # brighten image
    img_arr = cv2.convertScaleAbs(img_arr, alpha=2, beta=0)

    # invert
    img_arr = 255 - img_arr

    return Image.fromarray(img_arr)
