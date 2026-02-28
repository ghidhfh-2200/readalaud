"""
account_io.py —— acounts.json 的读写封装。
"""
import json
import os


ACCOUNTS_PATH = "./data/acounts.json"
DEFAULT_ACCOUNTS = {"names": [], "passwords": {}}
DEFAULT_SETTINGS = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}


def ensure_data_dir():
    if not os.path.exists("./data"):
        os.makedirs("./data")


def load_accounts():
    ensure_data_dir()
    if not os.path.exists(ACCOUNTS_PATH):
        with open(ACCOUNTS_PATH, "w") as f:
            json.dump(DEFAULT_ACCOUNTS, f)
    try:
        with open(ACCOUNTS_PATH, "r") as f:
            data = json.load(f)
        data.setdefault("names", [])
        data.setdefault("passwords", {})
        return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {"names": [], "passwords": {}}


def save_accounts(data):
    ensure_data_dir()
    with open(ACCOUNTS_PATH, "w") as f:
        json.dump(data, f)


def ensure_user_dir(encoded_account):
    user_path = f"./data/{encoded_account}"
    os.makedirs(user_path, exist_ok=True)
    settings_path = f"{user_path}/settings.json"
    if not os.path.exists(settings_path):
        with open(settings_path, "w") as f:
            json.dump(DEFAULT_SETTINGS.copy(), f)
    return user_path
