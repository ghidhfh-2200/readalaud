"""
account_io.py —— acounts.json 的读写封装 + 密码哈希/验证（bcrypt）。
"""
import base64
import hashlib
import json
import os

import bcrypt


ACCOUNTS_PATH = "./data/acounts.json"
DEFAULT_ACCOUNTS = {"names": [], "passwords": {}, "login_guard": {}}
DEFAULT_SETTINGS = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}

_BCRYPT_PREFIX = "bcrypt$"


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码，返回存储格式字符串。"""
    return _BCRYPT_PREFIX + bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored: str) -> tuple:
    """验证密码，返回 (is_valid: bool, upgraded_hash: str | None)。

    自动从旧格式（SHA-256 / base64 明文）迁移到 bcrypt。
    """
    # 1) bcrypt 格式
    if stored.startswith(_BCRYPT_PREFIX):
        bcrypt_hash = stored[len(_BCRYPT_PREFIX):].encode("utf-8")
        try:
            return bcrypt.checkpw(password.encode("utf-8"), bcrypt_hash), None
        except ValueError:
            return False, None

    # 2) 旧格式：salt$sha256
    if "$" in stored:
        try:
            salt, expected_hash = stored.split("$", 1)
            input_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
            if input_hash == expected_hash:
                return True, hash_password(password)
        except Exception:
            pass
        return False, None

    # 3) 旧格式：纯 SHA-256（无 salt）
    if hashlib.sha256(password.encode("utf-8")).hexdigest() == stored:
        return True, hash_password(password)

    # 4) 旧格式：base64 明文密码（兼容历史遗留）
    try:
        if base64.urlsafe_b64decode(stored).decode("utf-8") == password:
            return True, hash_password(password)
    except Exception:
        pass

    return False, None


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
        data.setdefault("login_guard", {})
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
