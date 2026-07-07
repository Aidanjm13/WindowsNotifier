import os
import csv

def get_data_path():
    app_data = os.path.join(os.environ["LOCALAPPDATA"], "Aidanjm13", "WindowsNotifier")
    os.makedirs(app_data, exist_ok=True)
    return os.path.join(app_data, "data.csv")

def create_file():
    path = get_data_path()
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "appName", "title", "content"])

def get_next_id():
    entries = get_entries()
    if not entries:
        return 1
    return max(int(e["id"]) for e in entries) + 1

def add_entry(appName, title, content):
    with open(get_data_path(), "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "appName", "title", "content"])
        writer.writerow({"id": get_next_id(), "appName": appName, "title": title, "content": content})

def get_entries():
    with open(get_data_path(), "r") as f:
        reader = csv.DictReader(f)
        return list(reader)

def get_entry(id):
    for entry in get_entries():
        if entry["id"] == str(id):
            return entry
    return None

def update_entry(id, new_appName, new_title, new_content):
    entries = get_entries()
    with open(get_data_path(), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "appName", "title", "content"])
        writer.writeheader()
        for entry in entries:
            if entry["id"] == str(id):
                writer.writerow({"id": id, "appName": new_appName, "title": new_title, "content": new_content})
            else:
                writer.writerow(entry)

def delete_entry(id):
    entries = get_entries()
    with open(get_data_path(), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "appName", "title", "content"])
        writer.writeheader()
        for entry in entries:
            if entry["id"] != str(id):
                writer.writerow(entry)