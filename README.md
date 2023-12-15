# Honkai: Star Rail - Data Scanner

Easily export light cones, relics, and character data from Honkai: Star Rail to JSON format using OCR.

The resulting output can be used in various community-made optimization tools including:

- [Fribbels HSR Optimizer](https://fribbels.github.io/hsr-optimizer/)
- [Relic Harmonizer](https://relicharmonizer.com/)

## Installation

[Download latest HSR Scanner](https://github.com/kel-z/HSR-Scanner/releases/latest) and then run as administrator (required to simulate keyboard and mouse presses).

<!-- If you haven't already, download and install [Microsoft Visual C++ Redistributable for Visual Studio 2015-2022](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2015-2017-2019-and-2022) (x86 or x64 depending on system). -->

## Instructions

1. Set in-game resolution to one that has an aspect ratio of 16:9 (e.g. 1920x1080, 1280x720).
   <!-- - Changing off from an ultra-wide resolution requires a game restart to reset the UI layout. -->
   <!-- ^^ wait... is this a thing in Star Rail? I know it was for Genshin -->
2. **In Star Rail, look away from any bright colours.** _Yes, really._ The inventory screen is translucent and bright colours can bleed through to make the text harder to accurately detect and recognize. Looking towards the ground usually works in most cases, as long as the right side of the screen is relatively dark. (Double-check by opening the inventory page and see if the item info on the right contrasts well with the background.) You can skip this step if you're only scanning characters.
3. Open the cellphone menu (ESC menu).
4. Configure the necessary [scanner settings](#scanner-settings-and-configurations) in HSR Scanner.
5. Start the scan.
6. Do not move your mouse during the scan process.
7. Once the scan is complete, some additional time may be required to process the data before generating the final JSON file output.

As of `v0.3.0`, the app's database is [updated separately](https://github.com/kel-z/HSR-Data) from this repo. If the database version doesn't match the latest game version, then the database hasn't been updated yet.

## Scanner settings and configurations

HSR Scanner has the following scan options:

- Select whether to scan light cones, relics, and/or characters.
- Set output location for the JSON file.
- Filter light cones and relics based on a minimum rarity or level threshhold.

The scanner uses `b` and `c` by default to navigate to the inventory and character screen, respectively. If you changed these hotkeys, you will need to update the corresponding key in the configure tab.

## Output

The output is loosely based off of Genshin's `.GOOD` export format. I don't expect this output to change anytime soon. If a breaking change has to made to the output, the version will be incremented by one to differentiate the change from previous versions.

### Notes

- Flat substats and percentage substats are differentiated by an underscore suffix in the key.
  - Main stats will never have an underscore suffix.
- The `_id` value for light cones and relics is arbitrarily assigned during the scanning process. It is intended for easy lookup in case of any errors logged during the scan, for double-checking or manual correction purposes.
- For character traces, `ability_#` and `stat_#` are ordered by earliest availability (i.e. `stat_1` can be unlocked at Ascension 0, but `stat_2` requires Ascension 2).
  - In the case of ties, namely two stat bonuses _X_ and _Y_ that both unlock at the same Ascension level, the one that visually connects to the highest `stat_#` on the in-game character traces page comes first. For example, if a stat bonus _X_ connects to `stat_2` and stat bonus _Y_ connects to `stat_1`, then _X_ would be `stat_3` and _Y_ would be `stat_4`.
    - If _X_ and _Y_ both connect to the same `stat_#` (only found in Erudition), then visually assign from bottom to top.
- The exact string values used can be found [here](src/models/game_data.py).

Current output sample:

```JSON
{
    "source": "HSR-Scanner",
    "version": 3,
    "light_cones": [
        {
            "key": "Cruising in the Stellar Sea",
            "level": 60,
            "ascension": 4,
            "superimposition": 2,
            "location": "Seele",
            "lock": true,
            "_id": "light_cone_1"
        },
        {
            "key": "Meshing Cogs",
            "level": 1,
            "ascension": 0,
            "superimposition": 5,
            "location": "",
            "lock": true,
            "_id": "light_cone_2"
        }
    ],
    "relics": [
        {
            "set": "Celestial Differentiator",
            "slot": "Planar Sphere",
            "rarity": 5,
            "level": 15,
            "mainstat": "Wind DMG Boost",
            "substats": [
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
            "location": "Bronya",
            "lock": true,
            "_id": "relic_1"
        },
        {
            "set": "Thief of Shooting Meteor",
            "slot": "Body",
            "rarity": 4,
            "level": 0,
            "mainstat": "Outgoing Healing Boost",
            "substats": [
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
            "_id": "relic_2"
        }
    ],
    "characters": [
        {
            "key": "Seele",
            "level": 59,
            "ascension": 4,
            "eidolon": 0,
            "skills": {
                "basic": 4,
                "skill": 6,
                "ult": 6,
                "talent": 6
            },
            "traces": {
                "ability_1": true,
                "ability_2": true,
                "ability_3": false,
                "stat_1": true,
                "stat_2": true,
                "stat_3": true,
                "stat_4": true,
                "stat_5": true,
                "stat_6": false,
                "stat_7": false,
                "stat_8": false,
                "stat_9": false,
                "stat_10": false
            }
        },
        {
            "key": "Bronya",
            "level": 20,
            "ascension": 1,
            "eidolon": 0,
            "skills": {
                "basic": 1,
                "skill": 1,
                "ult": 1,
                "talent": 1
            },
            "traces": {
                "ability_1": true,
                "ability_2": false,
                "ability_3": false,
                "stat_1": true,
                "stat_2": false,
                "stat_3": false,
                "stat_4": false,
                "stat_5": false,
                "stat_6": false,
                "stat_7": false,
                "stat_8": false,
                "stat_9": false,
                "stat_10": false
            }
        }
    ]
}
```

Check [sample_output.json](sample_output.json) for a full-sized, unfiltered example.

---

HSR-Scanner is not affiliated with, endorsed, sponsored, or approved by HoYoverse.
