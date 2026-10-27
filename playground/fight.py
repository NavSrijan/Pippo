import json
import ipdb
import toml

character_dir = "characters/"

# Character Class
class Character():
    def __init__(self, name: str):
        self.name = name
        self.load_character_from_name()
        self.load_stats()
        self.load_moves()

    def load_character_from_name(self) -> None:
        """Load the character data from the TOML file"""
        character_file = character_dir + self.name + ".toml"
        self.data = toml.load(character_file)

    def load_stats(self) -> None:
        """Load the stats from the dict to variables for easier use"""
        stats = self.data['stats']
        self.hp = stats['hp']
        self.dp = stats['dp']
        self.heal_multiplier = stats['heal_multiplier']
        self.mana_gain = stats['mana_gain']

    def load_moves(self) -> None:
        """Load the moves"""
        self.moves = self.data['moves']
        print(self.moves)


class Move():
    def __init__(self, move_type, probability_to_work):
        # Move types: LA(1): Light Attack HA(1): Heavy Attack DE(2): Defend SA(3): Special Attack
        self.move_type = move_type
        self.move_id = move_id
        self.probability = probability_to_work

    def use(self, ch1: Character, ch2: Character):
        "ch1 uses the move on ch2"
        # TODO
        pass




# The fighting engine
## It will take two character classes and simulate a turn based fighting game.
## Current idea:    It will change appropriate values.
##                  It will have a win value, which will show if a character has won or not.
##

class Fight():
    def __init__(self, ch1: Character, ch2: Character):
        self.ch1 = ch1
        self.ch2 = ch2

    def use_move(self):
        """Use a move"""
        # TODO
        pass


c = Character('nav')
