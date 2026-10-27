import json
from fetch_sheets import fetch_sheet

objects = {}
file_path = "data.json"

def load_json(self, json_file="test.json"):
    # Load previously saved JSON objects
    objects = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                objects = json.load(f)
            except json.JSONDecodeError:
                messagebox.showwarning(
                    "Warning",
                    "Invalid JSON file. Starting with an empty object list.")
    return objects

def save_json(id, name, n_id=0, e_id=0, s_id=0, w_id=0):
    data = {
        "id": id,
        "name": name,
        "description": "",
        "connections": {
            "N": {
                "id": n_id,
                "description":""
            },
            "E": {
                "id": e_id,
                "description":""
            },
            "S": {
                "id": s_id,
                "description":""
            },
            "W": {
                "id": w_id,
                "description":""
            }
        }
    }
    obj_id = int(data["id"])
    objects[obj_id] = data  # Store the object in the dictionary using the ID as the key
    with open(file_path, "w") as f:
        json.dump(objects, f, indent=4)

def fetch_json():
    obj_id = int(fetch_id_entry.get())
    if obj_id in objects:
        data = objects[obj_id]
        print(f"JSON object with ID {obj_id}:\n{json.dumps(data, indent=4)}")
    else:
        print(f"JSON object with ID {obj_id} not found!")


def assign_ids(grid):
    rows = len(grid)
    cols = len(grid[0])
    id_counter = 1

    # Create a new grid with dictionaries for each element
    grid_with_ids = [[{"name": grid[i][j]} for j in range(cols)] for i in range(rows)]

    # Assign IDs to each element
    for i in range(rows):
        for j in range(cols):
            element = grid_with_ids[i][j]
            element["id"] = id_counter
            id_counter += 1

    # Assign neighbor IDs for each element
    for i in range(rows):
        for j in range(cols):
            element = grid_with_ids[i][j]

            # Calculate the IDs of neighboring elements
            element["n_id"] = grid_with_ids[i-1][j]["id"] if i > 0 else 0
            element["e_id"] = grid_with_ids[i][j+1]["id"] if j < cols-1 else 0
            element["s_id"] = grid_with_ids[i+1][j]["id"] if i < rows-1 else 0
            element["w_id"] = grid_with_ids[i][j-1]["id"] if j > 0 else 0

    return grid_with_ids


ll = fetch_sheet()

grid_with_ids = assign_ids(ll)

for row in grid_with_ids:
    for element in row:
        save_json(element['id'], element['name'], n_id = element['n_id'], e_id = element['e_id'], s_id = element['s_id'], w_id = element['w_id'])
