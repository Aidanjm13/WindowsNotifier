import os
import csv
import json
import sys


def get_app_data_dir():
    app_name = "WindowsNotifier"
    author = "Aidanjm13"

    if sys.platform == "win32":
        base = os.environ["LOCALAPPDATA"]
        path = os.path.join(base, author, app_name)
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser("~/Library/Application Support"), app_name)
    else:  # Linux and other Unix-likes
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        path = os.path.join(base, app_name)

    os.makedirs(path, exist_ok=True)
    return path

def get_data_path():
    return os.path.join(get_app_data_dir(), "data.csv")


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

def get_settings_path():
    return os.path.join(get_app_data_dir(), "settings.json")

def read_settings():
    filepath = get_settings_path()
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    else:
        return None
    
def update_settings(settingsDict):
    with open(get_settings_path(), "w") as f:
            json.dump(settingsDict, f)
