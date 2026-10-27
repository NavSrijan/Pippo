"""
Name: The name of the monster.
Description: A brief description of the monster, including its appearance and characteristics.
Health Points (HP): The amount of health or vitality the monster has.
Level: The level or difficulty of the monster, which can determine its strength and rewards.
Attack Power: The amount of damage the monster can inflict on the player.
Defense: The level of defense or resistance the monster has against attacks.
Experience Points (XP): The amount of experience points awarded to the player upon defeating the monster.
Loot: The items or rewards the monster drops when defeated.
Special Abilities: Any unique abilities or skills the monster possesses, such as magical attacks or buffs.
Weaknesses: Elements, weapons, or strategies that the monster is particularly vulnerable to.
Immunities: Elements, weapons, or strategies that the monster is immune to or resistant against.
Behavior or AI: The monster's behavior in combat, such as aggressive, defensive, or strategic tendencies.
Spawn Rate: The likelihood or frequency of the monster appearing in specific areas.
"""

class Monster():
    def __init__(self):
        self.load_json()

    def load_json(self, json_file="m1.json"):
        # Load connections from JSON file
        with open(json_file) as file:
            self.data = json.load(file)


    def load_strings(self):
        lines = self.data['lines']
        self.about = lines['about']
        self.atk = lines['atk_line1']
        self.defn = lines['def_lines1']

    def load_attributes(self):
        self.id = seld.data['id']
        self.name = self.data['name']
        self.hp = self.data['hp']
        self.level = self.data['level']
        self.atk_pw = self.data['atk_pw']
        self.def_pw = self.data['def_pw']
        self.xp = self.data['xp']

    def special_attributes(self):
        self.items_dropped = self.data['items_dropped']
        self.special_abilities = self.data['special_abilities']
        self.weaknessess = self.data['weaknessess']
        self.immunities = self.data['immunities']
        self.style = self.data['style']
