class GameData:

    # From: https://honkai-star-rail.fandom.com/wiki/Light_Cone/List
    #   res = []
    #   Array.from($('tbody')[1].children).forEach(x => {res.push('"'+x.children[1].children[0].title+'"')})
    #   res.join(',')
    @staticmethod
    def get_light_cones():
        return {"A Secret Vow", "Adversarial", "Amber", "Arrows", "Before Dawn", "But the Battle Isn't Over", "Carve the Moon, Weave the Clouds", "Chorus", "Collapsing Sky", "Cornucopia", "Cruising in the Stellar Sea", "Dance! Dance! Dance!", "Darting Arrow", "Data Bank", "Day One of My New Life", "Defense", "Echoes of the Coffin", "Eyes of the Prey", "Fermata", "Fine Fruit", "Geniuses' Repose", "Good Night and Sleep Well", "Hidden Shadow", "In the Name of the World", "In the Night", "Incessant Rain", "Landau's Choice", "Loop", "Make the World Clamor", "Mediation", "Memories of the Past", "Meshing Cogs", "Moment of Victory", "Multiplication", "Mutual Demise", "Night on the Milky Way", "Nowhere to Run", "On the Fall of an Aeon",
                "Only Silence Remains", "Passkey", "Past and Future", "Patience Is All You Need", "Perfect Timing", "Pioneering", "Planetary Rendezvous", "Post-Op Conversation", "Quid Pro Quo", "Resolution Shines As Pearls of Sweat", "Return to Darkness", "River Flows in Spring", "Sagacity", "Shared Feeling", "Shattered Home", "Sleep Like the Dead", "Something Irreplaceable", "Subscribe for More!", "Swordplay", "Texture of Memories", "The Birth of the Self", "The Moles Welcome You", "The Seriousness of Breakfast", "The Unreachable Side", "This Is Me!", "Time Waits for No One", "Today Is Another Peaceful Day", "Trend of the Universal Market", "Under the Blue Sky", "Void", "Warmth Shortens Cold Nights", "We Are Wildfire", "We Will Meet Again", "Woof! Walk Time!"}
