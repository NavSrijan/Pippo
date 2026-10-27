tk = None
messagebox = None
import json
import os


def save_json():
    data = {
        "id": int(id_entry.get()),
        "name": name_entry.get(),
        "description": desc_entry.get(),
        "connections": {
            "N": {
                "id": int(north_id_entry.get()),
                "description": north_desc_entry.get(1.0, tk.END).strip()
            },
            "E": {
                "id": int(east_id_entry.get()),
                "description": east_desc_entry.get(1.0, tk.END).strip()
            },
            "S": {
                "id": int(south_id_entry.get()),
                "description": south_desc_entry.get(1.0, tk.END).strip()
            },
            "W": {
                "id": int(west_id_entry.get()),
                "description": west_desc_entry.get(1.0, tk.END).strip()
            }
        }
    }
    obj_id = str(data["id"])
    objects[obj_id] = data  # Store the object in the dictionary using the ID as the key
    with open(file_path, "w") as f:
        json.dump(objects, f, indent=4)
    messagebox.showinfo("Success", "JSON data saved!")

def fetch_json():
    fetch_id = fetch_id_entry.get()
    if fetch_id in objects:
        fetched_obj = objects[fetch_id]
        id_entry.delete(0, tk.END)
        id_entry.insert(tk.END, fetched_obj["id"])
        name_entry.delete(0, tk.END)
        name_entry.insert(tk.END, fetched_obj["name"])
        desc_entry.delete(0, tk.END)
        desc_entry.insert(tk.END, fetched_obj["description"])
        north_id_entry.delete(0, tk.END)
        north_id_entry.insert(tk.END, fetched_obj["connections"]["N"]["id"])
        east_id_entry.delete(0, tk.END)
        east_id_entry.insert(tk.END, fetched_obj["connections"]["E"]["id"])
        south_id_entry.delete(0, tk.END)
        south_id_entry.insert(tk.END, fetched_obj["connections"]["S"]["id"])
        west_id_entry.delete(0, tk.END)
        west_id_entry.insert(tk.END, fetched_obj["connections"]["W"]["id"])

        north_desc_entry.delete(1.0, tk.END)
        north_desc_entry.insert(tk.END, fetched_obj["connections"]["N"].get("description", ""))
        east_desc_entry.delete(1.0, tk.END)
        east_desc_entry.insert(tk.END, fetched_obj["connections"]["E"].get("description", ""))
        south_desc_entry.delete(1.0, tk.END)
        south_desc_entry.insert(tk.END, fetched_obj["connections"]["S"].get("description", ""))
        west_desc_entry.delete(1.0, tk.END)
        west_desc_entry.insert(tk.END, fetched_obj["connections"]["W"].get("description", ""))

        # Fill direction labels with corresponding object names
        north_label.config(text="North: " + get_object_name(fetched_obj["connections"]["N"]["id"]))
        east_label.config(text="East: " + get_object_name(fetched_obj["connections"]["E"]["id"]))
        south_label.config(text="South: " + get_object_name(fetched_obj["connections"]["S"]["id"]))
        west_label.config(text="West: " + get_object_name(fetched_obj["connections"]["W"]["id"]))
    else:
        messagebox.showwarning("Warning", "No object found with the specified ID.")


def get_object_name(obj_id):
    if obj_id==0:
        return "Border"
    obj_id = str(obj_id)
    if obj_id in objects:
        return objects[obj_id]["name"]
    return "Object Not Found"


def main():
    global tk, messagebox, window, objects, file_path, id_entry, name_entry, desc_entry, fetch_id_entry, north_id_entry, north_desc_entry, east_id_entry, east_desc_entry, south_id_entry, south_desc_entry, west_id_entry, west_desc_entry, north_label, east_label, south_label, west_label
    import tkinter as tk
    from tkinter import ttk, messagebox

    # Create the main window
    window = tk.Tk()
    window.title("JSON Object")

    # Create a styled frame
    frame = ttk.Frame(window, padding=20)
    frame.grid(column=0, row=0, sticky="nsew")

    # Create labels and entry fields for each attribute
    id_label = ttk.Label(frame, text="ID:")
    id_label.grid(column=0, row=0, sticky="w", padx=10, pady=5)
    id_entry = ttk.Entry(frame)
    id_entry.grid(column=1, row=0, sticky="w", padx=10, pady=5)

    name_label = ttk.Label(frame, text="Name:")
    name_label.grid(column=0, row=1, sticky="w", padx=10, pady=5)
    name_entry = ttk.Entry(frame)
    name_entry.grid(column=1, row=1, sticky="w", padx=10, pady=5)

    desc_label = ttk.Label(frame, text="Description:")
    desc_label.grid(column=0, row=2, sticky="w", padx=10, pady=5)
    desc_entry = ttk.Entry(frame)
    desc_entry.grid(column=1, row=2, sticky="w", padx=10, pady=5)

    # Labels for each direction's ID
    north_label = ttk.Label(frame, text="North:")
    north_label.grid(column=0, row=3, sticky="w", padx=10, pady=5)
    north_id_label = ttk.Label(frame, text="ID:")
    north_id_label.grid(column=0, row=4, sticky="w", padx=10, pady=5)
    north_id_entry = ttk.Entry(frame)
    north_id_entry.grid(column=1, row=4, sticky="w", padx=10, pady=5)
    north_desc_label = ttk.Label(frame, text="Description:")
    north_desc_label.grid(column=0, row=5, sticky="w", padx=10, pady=5)
    north_desc_entry = tk.Text(frame, height=5, width=30)
    north_desc_entry.grid(column=1, row=5, sticky="w", padx=10, pady=5)

    east_label = ttk.Label(frame, text="East:")
    east_label.grid(column=2, row=3, sticky="w", padx=10, pady=5)
    east_id_label = ttk.Label(frame, text="ID:")
    east_id_label.grid(column=2, row=4, sticky="w", padx=10, pady=5)
    east_id_entry = ttk.Entry(frame)
    east_id_entry.grid(column=3, row=4, sticky="w", padx=10, pady=5)
    east_desc_label = ttk.Label(frame, text="Description:")
    east_desc_label.grid(column=2, row=5, sticky="w", padx=10, pady=5)
    east_desc_entry = tk.Text(frame, height=5, width=30)
    east_desc_entry.grid(column=3, row=5, sticky="w", padx=10, pady=5)

    south_label = ttk.Label(frame, text="South:")
    south_label.grid(column=0, row=6, sticky="w", padx=10, pady=5)
    south_id_label = ttk.Label(frame, text="ID:")
    south_id_label.grid(column=0, row=7, sticky="w", padx=10, pady=5)
    south_id_entry = ttk.Entry(frame)
    south_id_entry.grid(column=1, row=7, sticky="w", padx=10, pady=5)
    south_desc_label = ttk.Label(frame, text="Description:")
    south_desc_label.grid(column=0, row=8, sticky="w", padx=10, pady=5)
    south_desc_entry = tk.Text(frame, height=5, width=30)
    south_desc_entry.grid(column=1, row=8, sticky="w", padx=10, pady=5)

    west_label = ttk.Label(frame, text="West:")
    west_label.grid(column=2, row=6, sticky="w", padx=10, pady=5)
    west_id_label = ttk.Label(frame, text="ID:")
    west_id_label.grid(column=2, row=7, sticky="w", padx=10, pady=5)
    west_id_entry = ttk.Entry(frame)
    west_id_entry.grid(column=3, row=7, sticky="w", padx=10, pady=5)
    west_desc_label = ttk.Label(frame, text="Description:")
    west_desc_label.grid(column=2, row=8, sticky="w", padx=10, pady=5)
    west_desc_entry = tk.Text(frame, height=5, width=30)
    west_desc_entry.grid(column=3, row=8, sticky="w", padx=10, pady=5)

    fetch_id_label = ttk.Label(frame, text="Fetch by ID:")
    fetch_id_label.grid(column=0, row=10, sticky="w", padx=10, pady=5)
    fetch_id_entry = ttk.Entry(frame)
    fetch_id_entry.grid(column=1, row=10, sticky="w", padx=10, pady=5)

    # Create a button to save the JSON object
    save_button = ttk.Button(frame, text="Save JSON", command=save_json)
    save_button.grid(column=0, row=9, columnspan=2, pady=10)

    # Create a button to fetch the JSON object by ID
    fetch_button = ttk.Button(frame, text="Fetch JSON", command=fetch_json)
    fetch_button.grid(column=2, row=9, columnspan=2, pady=10)

    # Configure grid weights for responsive resizing
    frame.columnconfigure((0, 1, 2, 3), weight=1)
    frame.rowconfigure((9, 10), weight=1)

    # Load previously saved JSON objects
    file_path = "data.json"
    objects = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                objects = json.load(f)
            except json.JSONDecodeError:
                messagebox.showwarning("Warning", "Invalid JSON file. Starting with an empty object list.")

    # Start the Tkinter event loop
    window.mainloop()



if __name__ == "__main__":
    main()
