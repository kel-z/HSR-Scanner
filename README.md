# Honkai: Star Rail - Data Scanner
Easily export light cones, relics, and character data from Honkai: Star Rail to JSON format using OCR.

## (NOTE: Character export is still under development. Currently, only light cone and relic data can be exported.)

## Installation
If you haven't already, download and install [Microsoft Visual C++ Redistributable for Visual Studio 2015-2022](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2015-2017-2019-and-2022) (x86 or x64 depending on system).

[Download latest HSR Scanner](https://github.com/kel-z/HSR-Scanner/releases/latest) and then run as administrator (required to simulate keyboard and mouse presses).

## Instructions
1. Set in-game resolution to one that has an aspect ratio of 16:9 (e.g. 1920x1080, 1280x720).
    <!-- - Changing off from an ultra-wide resolution requires a game restart to reset the UI layout. -->
    <!-- ^^ wait... is this a thing in Star Rail? I know it was for Genshin -->
2. **In Star Rail, look away from any bright colours.** The inventory screen is *translucent* and bright colours can bleed through to make the text harder to accurately detect and recognize. Looking towards the ground usually works in most cases, as long as the right side of the screen is relatively dark. (Double-check by opening the inventory page and see if the item info on the right contrasts well with the background.) You can skip this step if you're only scanning characters.
3. Open the cellphone menu (ESC menu).
4. Configure the necessary [scanner settings](#scanner-settings-and-configurations) in HSR Scanner.
5. Start the scan.
    - If you have multiple monitors, ensure that both Star Rail and HSR Scanner are on the same monitor before starting the scan.
6. Do not move your mouse during the scan process.
7. Once the scan is complete, additional time may be required to process the data before generating the final JSON file output.

## Scanner settings and configurations
HSR Scanner assumes that the inventory and character key bindings are unchanged ("b" and "c", respectively). If you have modified these bindings, please set them appropriately in the "Configure" tab of HSR Scanner.

HSR Scanner has the following scan options:

- Select whether to scan light cones or relics.
- Set output location for the JSON file.
- Filter light cones and relics based on a minimum rarity or level threshhold (*in development*).

## Output
The output is loosely based off of Genshin's `.GOOD` export format. **Please note that the current output format is subject to change.**
### Notes
- Flat substats and percentage substats are differentiated by an underscore suffix in the key.
  - Main stats will never have an underscore suffix.
- The `id` value is arbitrarily assigned during the scanning process. It is intended for easy lookup in case of any errors logged during the scan, for double-checking or manual correction purposes.
- The exact string values can be found in [game_data.py](src/utils/game_data.py).

Current output sample:
```
{
    "light_cones": [
        {
            "name": "Cruising in the Stellar Sea",
            "level": 60,
            "ascension": 4,
            "superimposition": 2,
            "location": "seele",
            "lock": true,
            "id": 0
        },
        {
            "name": "Meshing Cogs",
            "level": 1,
            "ascension": 0,
            "superimposition": 5,
            "location": "",
            "lock": true,
            "id": 1
        }
    ],
    "relics": [
        {
            "setKey": "Celestial Differentiator",
            "slotKey": "Planar Sphere",
            "rarity": 5,
            "level": 15,
            "mainStatKey": "Wind DMG Boost",
            "subStats": [
                {
                    "key": "HP",
                    "value": 105
                },
                {
                    "key": "CRIT Rate_",
                    "value": 3.2
                },
                {
                    "key": "CRIT DMG_",
                    "value": 17.4
                },
                {
                    "key": "Effect Hit Rate_",
                    "value": 8.2
                }
            ],
            "location": "bronya",
            "lock": true,
            "id": 2
        },
        {
            "setKey": "Thief of Shooting Meteor",
            "slotKey": "Body",
            "rarity": 4,
            "level": 0,
            "mainStatKey": "Outgoing Healing Boost",
            "subStats": [
                {
                    "key": "HP",
                    "value": 30
                },
                {
                    "key": "HP_",
                    "value": 3.4
                }
            ],
            "location": "",
            "lock": false,
            "id": 3
        }
    ]
}
```

## Dev notes
- **Expect data inaccuracies.** This app relies on reading text from images captured during the scan process, as opposed to reading off some save file. It also doesn't help that the inventory screen is translucent, as mentioned in step two of [instructions](#instructions).
- **If you have A LOT of light cones or relics, it could take a few minutes to process the images once the initial scan is done.** The current implementation includes preprocessing and error-checking for each relic to ensure accuracy, which comes at the cost of speed. Since this is my first time working with Tesseract and OCR as a whole, there is a lot of room for improvement and optimization in future releases.