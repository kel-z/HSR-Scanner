import Levenshtein


# From: https://honkai-star-rail.fandom.com/wiki/Light_Cone/List
#   res = []
#   Array.from($('tbody')[1].children).forEach(x => {res.push('"'+x.children[1].children[0].title+'"')})
#   res.join(',')
light_cone_names = {"A Secret Vow", "Adversarial", "Amber", "Arrows", "Before Dawn", "But the Battle Isn't Over", "Carve the Moon, Weave the Clouds", "Chorus", "Collapsing Sky", "Cornucopia", "Cruising in the Stellar Sea", "Dance! Dance! Dance!", "Darting Arrow", "Data Bank", "Day One of My New Life", "Defense", "Echoes of the Coffin", "Eyes of the Prey", "Fermata", "Fine Fruit", "Geniuses' Repose", "Good Night and Sleep Well", "Hidden Shadow", "In the Name of the World", "In the Night", "Incessant Rain", "Landau's Choice", "Loop", "Make the World Clamor", "Mediation", "Memories of the Past", "Meshing Cogs", "Moment of Victory", "Multiplication", "Mutual Demise", "Night on the Milky Way", "Nowhere to Run", "On the Fall of an Aeon",
                    "Only Silence Remains", "Passkey", "Past and Future", "Patience Is All You Need", "Perfect Timing", "Pioneering", "Planetary Rendezvous", "Post-Op Conversation", "Quid Pro Quo", "Resolution Shines As Pearls of Sweat", "Return to Darkness", "River Flows in Spring", "Sagacity", "Shared Feeling", "Shattered Home", "Sleep Like the Dead", "Something Irreplaceable", "Subscribe for More!", "Swordplay", "Texture of Memories", "The Birth of the Self", "The Moles Welcome You", "The Seriousness of Breakfast", "The Unreachable Side", "This Is Me!", "Time Waits for No One", "Today Is Another Peaceful Day", "Trend of the Universal Market", "Under the Blue Sky", "Void", "Warmth Shortens Cold Nights", "We Are Wildfire", "We Will Meet Again", "Woof! Walk Time!"}

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
relic_meta_data = {
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

relic_main_stats = {
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

relic_sub_stats = {
    "SPD",
    "ATK",
    "DEF",
    "HP",
    "Effect Hit Rate",
    "Effect RES",
    "CRIT Rate",
    "CRIT DMG",
    "Break Effect"
}


class GameData:

    @staticmethod
    def get_relic_meta_data(name):
        return relic_meta_data[name]

    @staticmethod
    def get_closest_relic_name(name):
        return get_closest_match(name, relic_meta_data)

    @staticmethod
    def get_closest_light_cone_name(name):
        return get_closest_match(name, light_cone_names)

    @staticmethod
    def get_closest_relic_sub_stat(name):
        return get_closest_match(name, relic_sub_stats)

    @staticmethod
    def get_closest_relic_main_stat(name):
        return get_closest_match(name, relic_main_stats)


def get_closest_match(name, targets):
    if not name:
        return name, 100

    if name in targets:
        return name, 0

    min_dist = 100
    min_name = ""
    for relic in targets:
        dist = Levenshtein.distance(name, relic)
        if dist < min_dist:
            min_dist = dist
            min_name = relic
    name = min_name

    return name, min_dist
