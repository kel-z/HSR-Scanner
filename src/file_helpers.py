import sys
import os
import json

# https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(
        os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def save_to_json(data):
    with open('data.json', 'w') as outfile:
        json.dump(data, outfile, indent=4)