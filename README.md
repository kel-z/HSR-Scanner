# Honkai: Star Rail - Data Scanner

Easily export light cones, relics, and character data from Honkai: Star Rail to JSON format using OCR.

The resulting output can be used in [Fribbels HSR Optimizer](https://fribbels.github.io/hsr-optimizer/).

## Installation

[Download latest HSR Scanner](https://github.com/kel-z/HSR-Scanner/releases/latest) and then run as administrator (required to simulate keyboard and mouse presses).

<!-- If you haven't already, download and install [Microsoft Visual C++ Redistributable for Visual Studio 2015-2022](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2015-2017-2019-and-2022) (x86 or x64 depending on system). -->

## Instructions

1. Set text language to English.
2. Set in-game resolution to one that has an aspect ratio of 16:9 (e.g. 1920x1080, 1280x720).
3. **In Star Rail, look away from any bright colours.** _Yes, really._ The inventory screen is translucent and bright colours can bleed through to make the text harder to accurately detect and recognize. Looking towards the ground usually works in most cases, as long as the right side of the screen is relatively dark. (Double-check by opening the inventory page and see if the item info on the right contrasts well with the background.) You can skip this step if you're only scanning characters.
   ![Dark background example](./example.png)
4. Open the cellphone menu (ESC menu).
5. Configure the necessary [scanner settings](#scanner-settings-and-configurations) in HSR Scanner.
6. Start the scan.
7. Do not move your mouse during the scan process.
8. Once the scan is complete, some additional time may be required to process the data before generating the final JSON file output.

As of `v0.3.0`, the app's database is [updated separately](https://github.com/kel-z/HSR-Data) from this repo. If the database version doesn't match the latest game version, then the database hasn't been updated yet.

## Scanner settings and configurations

HSR Scanner has the following scan options:

- Select whether to scan light cones, relics, and/or characters.
- Include account UID in the JSON file (disabled by default).
- Set output location for the JSON file.
- Filter light cones, relics, and characters based on a minimum rarity or level threshhold.

If Star Rail lags on your system, the scanner might perform its inputs too fast for the game to respond or re-render in time. To work around this, there are two types of delays that can be increased in the configure tab:

- Navigation delay for navigating between different pages (inventory, character details, etc.)
- Scan delay for clicking between individual items (relics, light cones, and characters).

The scanner uses `b` and `c` by default to navigate to the inventory and character screen, respectively. If you changed these hotkeys, you will need to update the corresponding key in the configure tab.

If debug mode is enabled, the scanner will save ALL the screenshots taken during a scan to a debug folder in the specified output directory.

## Output

The output is loosely based off of Genshin's `.GOOD` export format. If a breaking change has to made to the output, the version will be incremented by one to differentiate the change from previous versions.

### Notes

- SPD substats have a hidden decimal place that the scanner cannot directly parse. As a result, reproducing your character's stats (such as on optimizer websites) will most likely have a lower SPD stat than what it displays in-game. This is not an issue with the scanner, but rather a limitation when obtaining substats through OCR.
- The `id` value for light cones, relic sets, and characters correspond to the same unique ID assigned by the game.
  - Similarly, the `location` value for light cones and relics correspond to the character ID that is equipping the item.
- If the Trailblazer variant was not determinable during the scan or previous scans, it will default to `Stelle`.
- Flat substats and percentage substats are differentiated by an underscore suffix in the key.
  - Main stats will never have an underscore suffix.
- Substats are sorted in the order of: `HP, ATK, DEF, HP%, ATK%, DEF%, SPD, CRIT Rate, CRIT DMG, Effect Hit Rate, Effect RES, Break Effect`. This ordering applies for every relic with the exception of newly upgraded relics, which gets fixed when the user logs out and logs back in. As a result, the scanner will automatically sort the substats before generating the output.
- The `_uid` value for light cones and relics is arbitrarily assigned during the scanning process. It is intended for easy lookup in case of any errors logged during the scan, for double-checking or manual correction purposes.
- For `Dan Heng • Imbibitor Lunae`, the character `•` will appear as `\u2022` in the JSON output. This is the Unicode representation of the character and is a normal behaviour when special characters are included in JSON. Most modern environments will automatically render `\u2022` as `•` when displaying or processing the JSON.
- For character traces, `ability_#` and `stat_#` are ordered by earliest availability (i.e. `stat_1` can be unlocked at Ascension 0, but `stat_2` requires Ascension 2).
  - In the case of ties, namely two stat bonuses _X_ and _Y_ that both unlock at the same Ascension level, the one that visually connects to the highest `stat_#` on the in-game character traces page comes first. For example, if a stat bonus _X_ connects to `stat_2` and stat bonus _Y_ connects to `stat_1`, then _X_ would be `stat_3` and _Y_ would be `stat_4`.
    - If _X_ and _Y_ both connect to the same `stat_#` (only found in Erudition), then visually assign from bottom to top.
- Characters on the Remembrance path will have a `memosprite` key in the character data (see example below).

Current output sample:

```JSON
{
    "source": "HSR-Scanner",
    "build": "v1.4.0",
    "version": 4,
    "metadata": {
        "uid": 601869216,
        "trailblazer": "Stelle"
    },
    "light_cones": [
        {
            "id": "20010",
            "name": "Defense",
            "level": 80,
            "ascension": 6,
            "superimposition": 5,
            "location": "1001",
            "lock": true,
            "_uid": "light_cone_1"
        },
        {
            "id": "20020",
            "name": "Sagacity",
            "level": 1,
            "ascension": 0,
            "superimposition": 1,
            "location": "",
            "lock": false,
            "_uid": "light_cone_2"
        }
    ],
    "relics": [
        {
            "set_id": "102",
            "name": "Musketeer of Wild Wheat",
            "slot": "Hands",
            "rarity": 5,
            "level": 15,
            "mainstat": "ATK",
            "substats": [
                {
                    "key": "DEF",
                    "value": 16
                },
                {
                    "key": "DEF_",
                    "value": 5.4
                },
                {
                    "key": "CRIT Rate_",
                    "value": 5.1
                },
                {
                    "key": "CRIT DMG_",
                    "value": 31.7
                }
            ],
            "location": "1101",
            "lock": true,
            "discard": false,
            "_uid": "relic_1"
        },
        {
            "set_id": "111",
            "name": "Thief of Shooting Meteor",
            "slot": "Hands",
            "rarity": 5,
            "level": 0,
            "mainstat": "ATK",
            "substats": [
                {
                    "key": "ATK_",
                    "value": 4.3
                },
                {
                    "key": "DEF_",
                    "value": 4.3
                },
                {
                    "key": "CRIT DMG_",
                    "value": 5.8
                }
            ],
            "location": "",
            "lock": false,
            "discard": false,
            "_uid": "relic_2"
        }
    ],
    "characters": [
        {
            "id": "1001",
            "name": "March 7th",
            "path": "Preservation",
            "level": 80,
            "ascension": 6,
            "eidolon": 6,
            "skills": {
                "basic": 1,
                "skill": 10,
                "ult": 4,
                "talent": 2
            },
            "traces": {
                "ability_1": true,
                "ability_2": true,
                "ability_3": true,
                "stat_1": true,
                "stat_2": true,
                "stat_3": false,
                "stat_4": true,
                "stat_5": true,
                "stat_6": true,
                "stat_7": true,
                "stat_8": true,
                "stat_9": false,
                "stat_10": true
            }
        },
        {
            "id": "8008",
            "name": "Trailblazer",
            "path": "Remembrance",
            "level": 80,
            "ascension": 6,
            "eidolon": 0,
            "skills": {
                "basic": 1,
                "skill": 1,
                "ult": 2,
                "talent": 1
            },
            "traces": {
                "ability_1": true,
                "ability_2": false,
                "ability_3": false,
                "stat_1": false,
                "stat_2": false,
                "stat_3": false,
                "stat_4": false,
                "stat_5": false,
                "stat_6": false,
                "stat_7": false,
                "stat_8": false,
                "stat_9": false,
                "stat_10": false
            },
            "memosprite": {
                "skill": 4,
                "talent": 3
            }
        }
    ]
}
```

Check [sample_output.json](sample_output.json) for a full-sized, unfiltered example.

---

HSR-Scanner is not affiliated with, endorsed, sponsored, or approved by HoYoverse.
