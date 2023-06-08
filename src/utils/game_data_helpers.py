import Levenshtein
import numpy as np
import cv2

# From: https://honkai-star-rail.fandom.com/wiki/Light_Cone/List
#   res = []
#   Array.from($('tbody')[1].children).forEach(x => {res.push('"'+x.children[1].children[0].title+'": {' +
# 	    '"rarity": ' + x.children[2].innerText.split(' ').length
#   +'}')})
#   res.join(',\n')
LIGHT_CONE_META_DATA = {
    "A Secret Vow": {"rarity": 4},
    "Adversarial": {"rarity": 3},
    "Amber": {"rarity": 3},
    "Arrows": {"rarity": 3},
    "Before Dawn": {"rarity": 5},
    "But the Battle Isn't Over": {"rarity": 5},
    "Carve the Moon, Weave the Clouds": {"rarity": 4},
    "Chorus": {"rarity": 3},
    "Collapsing Sky": {"rarity": 3},
    "Cornucopia": {"rarity": 3},
    "Cruising in the Stellar Sea": {"rarity": 5},
    "Dance! Dance! Dance!": {"rarity": 4},
    "Darting Arrow": {"rarity": 3},
    "Data Bank": {"rarity": 3},
    "Day One of My New Life": {"rarity": 4},
    "Defense": {"rarity": 3},
    "Echoes of the Coffin": {"rarity": 5},
    "Eyes of the Prey": {"rarity": 4},
    "Fermata": {"rarity": 4},
    "Fine Fruit": {"rarity": 3},
    "Geniuses' Repose": {"rarity": 4},
    "Good Night and Sleep Well": {"rarity": 4},
    "Hidden Shadow": {"rarity": 3},
    "In the Name of the World": {"rarity": 5},
    "In the Night": {"rarity": 5},
    "Incessant Rain": {"rarity": 5},
    "Landau's Choice": {"rarity": 4},
    "Loop": {"rarity": 3},
    "Make the World Clamor": {"rarity": 4},
    "Mediation": {"rarity": 3},
    "Memories of the Past": {"rarity": 4},
    "Meshing Cogs": {"rarity": 3},
    "Moment of Victory": {"rarity": 5},
    "Multiplication": {"rarity": 3},
    "Mutual Demise": {"rarity": 3},
    "Night on the Milky Way": {"rarity": 5},
    "Nowhere to Run": {"rarity": 4},
    "On the Fall of an Aeon": {"rarity": 5},
    "Only Silence Remains": {"rarity": 4},
    "Passkey": {"rarity": 3},
    "Past and Future": {"rarity": 4},
    "Patience Is All You Need": {"rarity": 5},
    "Perfect Timing": {"rarity": 4},
    "Pioneering": {"rarity": 3},
    "Planetary Rendezvous": {"rarity": 4},
    "Post-Op Conversation": {"rarity": 4},
    "Quid Pro Quo": {"rarity": 4},
    "Resolution Shines As Pearls of Sweat": {"rarity": 4},
    "Return to Darkness": {"rarity": 4},
    "River Flows in Spring": {"rarity": 4},
    "Sagacity": {"rarity": 3},
    "Shared Feeling": {"rarity": 4},
    "Shattered Home": {"rarity": 3},
    "Sleep Like the Dead": {"rarity": 5},
    "Something Irreplaceable": {"rarity": 5},
    "Subscribe for More!": {"rarity": 4},
    "Swordplay": {"rarity": 4},
    "Texture of Memories": {"rarity": 5},
    "The Birth of the Self": {"rarity": 4},
    "The Moles Welcome You": {"rarity": 4},
    "The Seriousness of Breakfast": {"rarity": 4},
    "The Unreachable Side": {"rarity": 5},
    "This Is Me!": {"rarity": 4},
    "Time Waits for No One": {"rarity": 5},
    "Today Is Another Peaceful Day": {"rarity": 4},
    "Trend of the Universal Market": {"rarity": 4},
    "Under the Blue Sky": {"rarity": 4},
    "Void": {"rarity": 3},
    "Warmth Shortens Cold Nights": {"rarity": 4},
    "We Are Wildfire": {"rarity": 4},
    "We Will Meet Again": {"rarity": 4},
    "Woof! Walk Time!": {"rarity": 4}
}

# From: https://honkai-star-rail.fandom.com/wiki/Relic/Sets
# For each set wiki page:
#   res = "\n"
#   for (let i = 0; i < $("h3 .mw-headline").length; i++) {
#       res += '"' + $("h3 .mw-headline")[i].innerText.trim()
#           + '": {'
#           + '"setKey": "' +$('.mw-page-title-main')[0].innerText.trim()
#           + '", "slotKey": "'
#           + $('.pi-data-value b')[i].innerText.trim().toLowerCase()
#           + '"},\n'
#   }
#   res
RELIC_META_DATA = {
    "Band's Polarized Sunglasses": {"setKey": "Band of Sizzling Thunder", "slotKey": "Head"},
    "Band's Touring Bracelet": {"setKey": "Band of Sizzling Thunder", "slotKey": "Hand"},
    "Band's Leather Jacket With Studs": {"setKey": "Band of Sizzling Thunder", "slotKey": "Body"},
    "Band's Ankle Boots With Rivets": {"setKey": "Band of Sizzling Thunder", "slotKey": "Feet"},

    "Belobog's Fortress of Preservation": {"setKey": "Belobog of the Architects", "slotKey": "Planar Sphere"},
    "Belobog's Iron Defense": {"setKey": "Belobog of the Architects", "slotKey": "Link Rope"},

    "Planet Screwllum's Mechanical Sun": {"setKey": "Celestial Differentiator", "slotKey": "Planar Sphere"},
    "Planet Screwllum's Ring System": {"setKey": "Celestial Differentiator", "slotKey": "Link Rope"},

    "Champion's Headgear": {"setKey": "Champion of Streetwise Boxing", "slotKey": "Head"},
    "Champion's Heavy Gloves": {"setKey": "Champion of Streetwise Boxing", "slotKey": "Hand"},
    "Champion's Chest Guard": {"setKey": "Champion of Streetwise Boxing", "slotKey": "Body"},
    "Champion's Fleetfoot Boots": {"setKey": "Champion of Streetwise Boxing", "slotKey": "Feet"},

    "Eagle's Beaked Helmet": {"setKey": "Eagle of Twilight Line", "slotKey": "Head"},
    "Eagle's Soaring Ring": {"setKey": "Eagle of Twilight Line", "slotKey": "Hand"},
    "Eagle's Winged Suit Harness": {"setKey": "Eagle of Twilight Line", "slotKey": "Body"},
    "Eagle's Quilted Puttees": {"setKey": "Eagle of Twilight Line", "slotKey": "Feet"},

    "Firesmith's Obsidian Goggles": {"setKey": "Firesmith of Lava-Forging", "slotKey": "Head"},
    "Firesmith's Ring of Flame-Mastery": {"setKey": "Firesmith of Lava-Forging", "slotKey": "Hand"},
    "Firesmith's Fireproof Apron": {"setKey": "Firesmith of Lava-Forging", "slotKey": "Body"},
    "Firesmith's Alloy Leg": {"setKey": "Firesmith of Lava-Forging", "slotKey": "Feet"},

    "The Xianzhou Luofu's Celestial Ark": {"setKey": "Fleet of the Ageless", "slotKey": "Planar Sphere"},
    "The Xianzhou Luofu's Ambrosial Arbor Vines": {"setKey": "Fleet of the Ageless", "slotKey": "Link Rope"},

    "Genius's Ultraremote Sensing Visor": {"setKey": "Genius of Brilliant Stars", "slotKey": "Head"},
    "Genius's Frequency Catcher": {"setKey": "Genius of Brilliant Stars", "slotKey": "Hand"},
    "Genius's Metafield Suit": {"setKey": "Genius of Brilliant Stars", "slotKey": "Body"},
    "Genius's Gravity Walker": {"setKey": "Genius of Brilliant Stars", "slotKey": "Feet"},

    "Guard's Cast Iron Helmet": {"setKey": "Guard of Wuthering Snow", "slotKey": "Head"},
    "Guard's Shining Gauntlets": {"setKey": "Guard of Wuthering Snow", "slotKey": "Hand"},
    "Guard's Uniform of Old": {"setKey": "Guard of Wuthering Snow", "slotKey": "Body"},
    "Guard's Silver Greaves": {"setKey": "Guard of Wuthering Snow", "slotKey": "Feet"},

    "Hunter's Artaius Hood": {"setKey": "Hunter of Glacial Forest", "slotKey": "Head"},
    "Hunter's Lizard Gloves": {"setKey": "Hunter of Glacial Forest", "slotKey": "Hand"},
    "Hunter's Soft Elkskin Boots": {"setKey": "Hunter of Glacial Forest", "slotKey": "Body"},
    "Hunter's Ice Dragon Cloak": {"setKey": "Hunter of Glacial Forest", "slotKey": "Feet"},

    "Salsotto's Moving City": {"setKey": "Inert Salsotto", "slotKey": "Planar Sphere"},
    "Salsotto's Terminator Line": {"setKey": "Inert Salsotto", "slotKey": "Link Rope"},

    "Knight's Forgiving Casque": {"setKey": "Knight of Purity Palace", "slotKey": "Head"},
    "Knight's Silent Oath Ring": {"setKey": "Knight of Purity Palace", "slotKey": "Hand"},
    "Knight's Solemn Breastplate": {"setKey": "Knight of Purity Palace", "slotKey": "Body"},
    "Knight's Iron Boots of Order": {"setKey": "Knight of Purity Palace", "slotKey": "Feet"},

    "Musketeer's Wild Wheat Felt Hat": {"setKey": "Musketeer of Wild Wheat", "slotKey": "Head"},
    "Musketeer's Coarse Leather Gloves": {"setKey": "Musketeer of Wild Wheat", "slotKey": "Hand"},
    "Musketeer's Wind-Hunting Shawl": {"setKey": "Musketeer of Wild Wheat", "slotKey": "Body"},
    "Musketeer's Rivets Riding Boots": {"setKey": "Musketeer of Wild Wheat", "slotKey": "Feet"},

    "The IPC's Mega HQ": {"setKey": "Pan-Galactic Commercial Enterprise", "slotKey": "Planar Sphere"},
    "The IPC's Trade Route": {"setKey": "Pan-Galactic Commercial Enterprise", "slotKey": "Link Rope"},

    "Passerby's Rejuvenated Wooden Hairstick": {"setKey": "Passerby of Wandering Cloud", "slotKey": "Head"},
    "Passerby's Roaming Dragon Bracer": {"setKey": "Passerby of Wandering Cloud", "slotKey": "Hand"},
    "Passerby's Ragged Embroided Coat": {"setKey": "Passerby of Wandering Cloud", "slotKey": "Body"},
    "Passerby's Stygian Hiking Boots": {"setKey": "Passerby of Wandering Cloud", "slotKey": "Feet"},

    "Herta's Space Station": {"setKey": "Space Sealing Station", "slotKey": "Planar Sphere"},
    "Herta's Wandering Trek": {"setKey": "Space Sealing Station", "slotKey": "Link Rope"},

    "Vonwacq's Island of Birth": {"setKey": "Sprightly Vonwacq", "slotKey": "Planar Sphere"},
    "Vonwacq's Islandic Coast": {"setKey": "Sprightly Vonwacq", "slotKey": "Link Rope"},

    "Talia's Nailscrap Town": {"setKey": "Talia Kingdom of Banditry", "slotKey": "Planar Sphere"},
    "Talia's Exposed Electric Wire": {"setKey": "Talia Kingdom of Banditry", "slotKey": "Link Rope"},

    "Thief's Myriad-Faced Mask": {"setKey": "Thief of Shooting Meteor", "slotKey": "Head"},
    "Thief's Gloves With Prints": {"setKey": "Thief of Shooting Meteor", "slotKey": "Hand"},
    "Thief's Steel Grappling Hook": {"setKey": "Thief of Shooting Meteor", "slotKey": "Body"},
    "Thief's Meteor Boots": {"setKey": "Thief of Shooting Meteor", "slotKey": "Feet"},

    "Wastelander's Breathing Mask": {"setKey": "Wastelander of Banditry Desert", "slotKey": "Head"},
    "Wastelander's Desert Terminal": {"setKey": "Wastelander of Banditry Desert", "slotKey": "Hand"},
    "Wastelander's Friar Robe": {"setKey": "Wastelander of Banditry Desert", "slotKey": "Body"},
    "Wastelander's Powered Greaves": {"setKey": "Wastelander of Banditry Desert", "slotKey": "Feet"},
}

CHARACTER_META_DATA = {
    "Bronya": {"e3": {"ult": 2, "talent": 2}, "e5": {"skill": 2, "basic": 1}},
    "Seele": {"e3": {"skill": 2, "talent": 2}, "e5": {"ult": 2, "basic": 1}},
    "Clara": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Bailu": {"e3": {"skill": 2, "talent": 2}, "e5": {"ult": 2, "basic": 1}},
    "March 7th": {"e3": {"ult": 2, "basic": 1}, "e5": {"skill": 2, "talent": 2}},
    "Dan Heng": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Arlan": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Asta": {"e3": {"skill": 2, "talent": 2}, "e5": {"ult": 2, "basic": 1}},
    "Herta": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Serval": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Natasha": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Pela": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Hook": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Qingque": {"e3": {"skill": 2, "talent": 2}, "e5": {"ult": 2, "basic": 1}},
    "Tingyun": {"e3": {"ult": 2, "basic": 1}, "e5": {"skill": 2, "talent": 2}},
    "Sushang": {"e3": {"ult": 2, "talent": 2}, "e5": {"skill": 2, "basic": 1}},
    "Himeko": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Welt": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Gepard": {"e3": {"ult": 2, "talent": 2}, "e5": {"skill": 2, "basic": 1}},
    "Jing Yuan": {"e3": {"ult": 2, "basic": 1}, "e5": {"skill": 2, "talent": 2}},
    "Yanqing": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "Sampo": {"e3": {"skill": 2, "basic": 1}, "e5": {"ult": 2, "talent": 2}},
    "TrailblazerDestruction": {"e3": {"skill": 2, "talent": 2}, "e5": {"ult": 2, "basic": 1}},
    "TrailblazerPreservation": {"e3": {"skill": 2, "talent": 2}, "e5": {"ult": 2, "basic": 1}},
}

RELIC_MAIN_STATS = {
    "SPD",
    "HP",
    "ATK",
    "DEF",
    "Break Effect",
    "Effect Hit Rate",
    "Energy Regeneration Rate",
    "Outgoing Healing Boost",
    "Physical DMG Boost",
    "Fire DMG Boost",
    "Ice DMG Boost",
    "Wind DMG Boost",
    "Lightning DMG Boost",
    "Quantum DMG Boost",
    "Imaginary DMG Boost",
    "CRIT Rate",
    "CRIT DMG",
}

RELIC_SUB_STATS = {
    "SPD",
    "ATK",
    "DEF",
    "HP",
    "Effect Hit Rate",
    "Effect RES",
    "CRIT Rate",
    "CRIT DMG",
    "Break Effect",
}

CHARACTER_KEYS = list(CHARACTER_META_DATA.keys())
if "TrailblazerDestruction" in CHARACTER_KEYS:
    CHARACTER_KEYS.remove("TrailblazerDestruction")
    CHARACTER_KEYS.append("TrailblazerDestruction#M")
    CHARACTER_KEYS.append("TrailblazerDestruction#F")
if "TrailblazerPreservation" in CHARACTER_KEYS:
    CHARACTER_KEYS.remove("TrailblazerPreservation")
    CHARACTER_KEYS.append("TrailblazerPreservation#M")
    CHARACTER_KEYS.append("TrailblazerPreservation#F")

EQUIPPED_ICONS = {}


def get_relic_meta_data(name):
    return RELIC_META_DATA[name]


def get_light_cone_meta_data(name):
    return LIGHT_CONE_META_DATA[name]


def get_character_meta_data(name):
    return CHARACTER_META_DATA[name]


def get_equipped_character(equipped_avatar_img, img_path_prefix):
    equipped_avatar_img = np.array(equipped_avatar_img)

    max_conf = 0
    character = ""

    # Get character with highest confidence
    for c in CHARACTER_KEYS:
        if c not in EQUIPPED_ICONS:
            file_name = c.replace(" ", "")
            img = cv2.imread(f"{img_path_prefix}/{file_name}.png")
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)

            min_dim = int(min(equipped_avatar_img.shape[:2]))
            img = cv2.resize(img, (min_dim, min_dim))

            # Circle mask
            mask = np.zeros(img.shape[:2], dtype="uint8")
            (h, w) = img.shape[:2]
            cv2.circle(mask, (int(w / 2), int(h / 2)),
                    int(min_dim / 2), 255, -1)
            img = cv2.bitwise_and(img, img, mask=mask)

            EQUIPPED_ICONS[c] = img

        # Get confidence
        conf = cv2.matchTemplate(
            equipped_avatar_img, EQUIPPED_ICONS[c], cv2.TM_CCOEFF_NORMED).max()
        if conf > max_conf:
            max_conf = conf
            character = c

    return character.split("#")[0]


def get_closest_relic_name(name):
    return __get_closest_match(name, RELIC_META_DATA)


def get_closest_light_cone_name(name):
    return __get_closest_match(name, LIGHT_CONE_META_DATA)


def get_closest_relic_sub_stat(name):
    return __get_closest_match(name, RELIC_SUB_STATS)


def get_closest_relic_main_stat(name):
    return __get_closest_match(name, RELIC_MAIN_STATS)


def get_closest_character_name(name):
    return __get_closest_match(name, CHARACTER_META_DATA)


def get_closest_rarity(pixel):
    # where i + 1 is the rarity
    colors = [[94, 97, 111], [74, 100, 121], [
        61, 90, 145], [101, 92, 142], [158, 109, 95]]

    colors = np.array(colors)
    distances = np.sqrt(np.sum((colors - pixel)**2, axis=1))

    return int(np.argmin(distances)) + 1


def __get_closest_match(name, targets):
    if not name:
        return name, 100

    if name in targets:
        return name, 0

    min_dist = 100
    min_name = ""
    for x in targets:
        dist = Levenshtein.distance(name, x)
        if dist < min_dist:
            min_dist = dist
            min_name = x
    name = min_name

    return name, min_dist
