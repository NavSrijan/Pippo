import networkx as nx
import matplotlib.pyplot as plt
import json

G = nx.Graph()

# Add nodes (rooms)
G.add_node(1, description="You are in a small room with a wooden door.")
G.add_node(2, description="You enter a large hall with high ceilings.")
G.add_node(3, description="You find yourself in a dimly lit corridor.")

# Add edges (connections)
G.add_edge(1, 2, connection_description="A wooden door leads to the hall.")
G.add_edge(2, 3, connection_description="You see a corridor ahead.")
G.add_edge(3, 1, connection_description="You find a secret passage back to the small room.")

# Player's current room
current_room = 1

# Example usage: printing current room description and available connections
#print(G.nodes[current_room]["description"])

#for connected_room in G.neighbors(current_room):
#    connection_description = G.edges[current_room, connected_room]["connection_description"]
#    print(" -", connection_description)

# Visualization (optional)
nx.draw(G, with_labels=True)
plt.show()

class Map():
    """
          N (0)
            |
     NW (7) |  NE (1)
    ________|________
   |        |        |
   |        |        |
 W (6)------*------E (2)
   |        |        |
   |        |        |
   |________|________|
     SW (5) |  SE (3)
            |
            |
          S (4)

    """
    DIRECTIONS = {
    'N': 0,
    'NE': 1,
    'E': 2,
    'SE': 3,
    'S': 4,
    'SW': 5,
    'W': 6,
    'NW': 7
}


    def __init__(self):
        self.load_json()

    def load_json(self, json_file="test.json"):
        # Load connections from JSON file
        with open(json_file) as file:
            data = json.load(file)

        # Access nodes and connections
        self.nodes = data['nodes']

    def show_adjacent_rooms(self, id):
        self.room_dict = {room['id']: room for room in rooms}
        print(self.nodes)


class Player():
    def __init__(self, x, y):
        self.x = x
        self.y = y
