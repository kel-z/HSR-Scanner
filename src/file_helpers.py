import sys
import os
import json
import datetime

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
