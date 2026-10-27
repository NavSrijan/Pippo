import networkx as nx
import matplotlib.pyplot as plt
import json
import ipdb


class Map():

    def __init__(self):
        self.directions = {0:"North", 1:"East", 2:"South", 3:"West"}
        self.directions = {"N":"North", "E":"East", "S":"South", "W":"West"}

        self.load_json()

    def load_json(self, json_file="data.json"):
        # Load connections from JSON file
        with open(json_file) as file:
            self.data = json.load(file)

    def load_nodes(self):
        self.lookup = {node['id']: node for node in self.nodes_data}

    def get_node(self, node_id):
        return self.data.get(str(node_id))

    def get_directions_to_proceed_in(self, node_id):
        node = self.get_node(node_id)
        directions = {}
        for i in node['connections']:
            if node['connections'][i]['id']!=0:
                directions[i] = node['connections'][i]['id']

        return directions


mp = Map()
current_room = 1

while True:
    node = mp.get_node(current_room)
    print(node['description'])
    to_go = input("--> ")
    dirns = mp.get_directions_to_proceed_in(current_room)
    if to_go in dirns.keys():
        current_room = dirns[to_go]
        next_node = node['connections'][to_go]
        print(f"Currently in {mp.get_node(str(next_node['id']))['name']}")
    else:
        print("No way that side.")
