import json
import os
import sys
from datetime import datetime

from PIL.Image import Image


def resource_path(relative_path: str) -> str:
    """Get resource path for PyInstaller

    https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile

    :param relative_path: The relative path to the resource
    :return: The absolute path to the resource
    """
    # get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # get src directory: assuming the utils module is under the `src` directory
    src_dir = os.path.dirname(current_dir)

    base_path = getattr(sys, "_MEIPASS", src_dir)
    return os.path.join(base_path, relative_path)


def executable_path(path: str) -> str:
    """Get executable path for PyInstaller

    :param path: The relative path to the executable
    :return: The absolute path to the executable
    """
    return os.path.join(os.path.dirname(sys.executable), path)


def create_debug_folder(output_location: str) -> str:
    """Create a debug folder

    :param output_location: The output location
    """
    debug_folder_path = os.path.join(
        output_location, "debug", datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    )
    os.makedirs(debug_folder_path, exist_ok=True)
    return debug_folder_path


def save_to_json(data: dict, output_location: str, file_name: str) -> None:
    """Save data to json file

    :param data: The data to save
    :param output_location: The output location
    :param file_name: The file name
    """
    if not os.path.exists(output_location):
        os.makedirs(output_location)

    with open(os.path.join(output_location, file_name), "w") as outfile:
        json.dump(data, outfile, indent=4)


def save_to_txt(content: str, output_location: str, file_name: str) -> None:
    """Save content to text file

    :param content: The content to save
    :param output_location: The output location
    :param file_name: The file name
    """
    if not os.path.exists(output_location):
        os.makedirs(output_location)

    with open(os.path.join(output_location, file_name), "w") as file:
        file.write(content)


def get_json_data(file_path: str) -> dict:
    """Get json data from file

    :param file_path: The file path
    :return: The json data
    """
    with open(file_path) as json_file:
        return json.load(json_file)


def filter_images_from_dict(d):
    """Filter images from dictionary

    :param d: The dictionary
    :return: The dictionary with images filtered out
    """
    return {k: v for k, v in d.items() if not isinstance(v, Image)}
