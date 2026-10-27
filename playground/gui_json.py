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
    objects[
        obj_id] = data  # Store the object in the dictionary using the ID as the key
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
        north_desc_entry.delete(1.0, tk.END)
        north_desc_entry.insert(tk.END,
                                fetched_obj["connections"]["N"]["description"])
        east_id_entry.delete(0, tk.END)
        east_id_entry.insert(tk.END, fetched_obj["connections"]["E"]["id"])
        east_desc_entry.delete(1.0, tk.END)
        east_desc_entry.insert(tk.END,
                               fetched_obj["connections"]["E"]["description"])
        south_id_entry.delete(0, tk.END)
        south_id_entry.insert(tk.END, fetched_obj["connections"]["S"]["id"])
        south_desc_entry.delete(1.0, tk.END)
        south_desc_entry.insert(tk.END,
                                fetched_obj["connections"]["S"]["description"])
        west_id_entry.delete(0, tk.END)
        west_id_entry.insert(tk.END, fetched_obj["connections"]["W"]["id"])
        west_desc_entry.delete(1.0, tk.END)
        west_desc_entry.insert(tk.END,
                               fetched_obj["connections"]["W"]["description"])
    else:
        messagebox.showwarning("Warning",
                               "No object found with the specified ID.")


def main():
    global tk, messagebox, window, objects, file_path, id_entry, name_entry, desc_entry, fetch_id_entry, north_id_entry, north_desc_entry, east_id_entry, east_desc_entry, south_id_entry, south_desc_entry, west_id_entry, west_desc_entry
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
    id_label.grid(column=0, row=0, sticky="w")
    id_entry = ttk.Entry(frame)
    id_entry.grid(column=1, row=0, sticky="w")

    name_label = ttk.Label(frame, text="Name:")
    name_label.grid(column=0, row=1, sticky="w")
    name_entry = ttk.Entry(frame)
    name_entry.grid(column=1, row=1, sticky="w")

    desc_label = ttk.Label(frame, text="Description:")
    desc_label.grid(column=0, row=2, sticky="w")
    desc_entry = ttk.Entry(frame)
    desc_entry.grid(column=1, row=2, sticky="w")

    north_id_label = ttk.Label(frame, text="North ID:")
    north_id_label.grid(column=0, row=3, sticky="w")
    north_id_entry = ttk.Entry(frame)
    north_id_entry.grid(column=1, row=3, sticky="w")

    north_desc_label = ttk.Label(frame, text="North Description:")
    north_desc_label.grid(column=0, row=4, sticky="w")
    north_desc_entry = tk.Text(frame, height=5, width=30)
    north_desc_entry.grid(column=1, row=4, sticky="w")

    east_id_label = ttk.Label(frame, text="East ID:")
    east_id_label.grid(column=2, row=3, sticky="w")
    east_id_entry = ttk.Entry(frame)
    east_id_entry.grid(column=3, row=3, sticky="w")

    east_desc_label = ttk.Label(frame, text="East Description:")
    east_desc_label.grid(column=2, row=4, sticky="w")
    east_desc_entry = tk.Text(frame, height=5, width=30)
    east_desc_entry.grid(column=3, row=4, sticky="w")

    south_id_label = ttk.Label(frame, text="South ID:")
    south_id_label.grid(column=0, row=5, sticky="w")
    south_id_entry = ttk.Entry(frame)
    south_id_entry.grid(column=1, row=5, sticky="w")

    south_desc_label = ttk.Label(frame, text="South Description:")
    south_desc_label.grid(column=0, row=6, sticky="w")
    south_desc_entry = tk.Text(frame, height=5, width=30)
    south_desc_entry.grid(column=1, row=6, sticky="w")

    west_id_label = ttk.Label(frame, text="West ID:")
    west_id_label.grid(column=2, row=5, sticky="w")
    west_id_entry = ttk.Entry(frame)
    west_id_entry.grid(column=3, row=5, sticky="w")

    west_desc_label = ttk.Label(frame, text="West Description:")
    west_desc_label.grid(column=2, row=6, sticky="w")
    west_desc_entry = tk.Text(frame, height=5, width=30)
    west_desc_entry.grid(column=3, row=6, sticky="w")

    fetch_id_label = ttk.Label(frame, text="Fetch by ID:")
    fetch_id_label.grid(column=0, row=8, sticky="w")
    fetch_id_entry = ttk.Entry(frame)
    fetch_id_entry.grid(column=1, row=8, sticky="w")

    # Create a button to save the JSON object
    save_button = ttk.Button(frame, text="Save JSON", command=save_json)
    save_button.grid(column=0, row=7, columnspan=2, pady=10)

    # Create a button to fetch the JSON object by ID
    fetch_button = ttk.Button(frame, text="Fetch JSON", command=fetch_json)
    fetch_button.grid(column=2, row=7, columnspan=2, pady=10)

    # Configure grid weights for responsive resizing
    frame.columnconfigure((0, 1, 2, 3), weight=1)
    frame.rowconfigure((7, 8), weight=1)

    # Load previously saved JSON objects
    file_path = "data.json"
    objects = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                objects = json.load(f)
            except json.JSONDecodeError:
                messagebox.showwarning(
                    "Warning",
                    "Invalid JSON file. Starting with an empty object list.")

    # Start the Tkinter event loop
    window.mainloop()


if __name__ == "__main__":
    main()
