import sqlite3
import os
from datetime import datetime
import base64

DB_PATH = "./data/system_log.db"

LOG_LEVELS = ("INFO", "SUCCESS", "WARNING", "ERROR", "FATAL")

def init_db():
    os.makedirs("./data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  log_level TEXT,
                  log_type TEXT,
                  account TEXT,
                  action TEXT,
                  details TEXT)''')
    c.execute("PRAGMA table_info(logs)")
    columns = {row[1] for row in c.fetchall()}
    if "log_level" not in columns:
        try:
            c.execute("ALTER TABLE logs ADD COLUMN log_level TEXT DEFAULT 'INFO'")
        except Exception:
            pass
    conn.commit()
    conn.close()

def add_log(account, log_level, action, details="", log_type="GENERAL"):
    """
    log_level: INFO / SUCCESS / WARNING / ERROR / FATAL
    """
    if not account:
        account = "SYSTEM"
    if log_level not in LOG_LEVELS:
        log_level = "INFO"
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        c.execute(
            "INSERT INTO logs (timestamp, log_level, log_type, account, action, details) VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, log_level, log_type, account, action, details),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to write log: {e}")


def _decode_account_safe(account):
    if not account:
        return "SYSTEM"
    try:
        return base64.urlsafe_b64decode(account).decode("utf-8")
    except Exception:
        return str(account)

def log_audit(account, action, details=""):
    add_log(_decode_account_safe(account), "SUCCESS", action, details, log_type="AUDIT")

def log_operation(account, action, details=""):
    add_log(_decode_account_safe(account), "INFO", action, details, log_type="OPERATION")


def log_info(account, action, details="", log_type="OPERATION"):
    add_log(_decode_account_safe(account), "INFO", action, details, log_type=log_type)


def log_success(account, action, details="", log_type="AUDIT"):
    add_log(_decode_account_safe(account), "SUCCESS", action, details, log_type=log_type)


def log_warning(account, action, details="", log_type="OPERATION"):
    add_log(_decode_account_safe(account), "WARNING", action, details, log_type=log_type)


def log_error(account, action, details=""):
    add_log(_decode_account_safe(account), "ERROR", action, details, log_type="ERROR")


def log_fatal(account, action, details=""):
    add_log(_decode_account_safe(account), "FATAL", action, details, log_type="FATAL")


def log_system(action, details=""):
    add_log("SYSTEM", "INFO", action, details, log_type="SYSTEM")

def get_logs(log_type=None, month=None, level=None, limit=1000):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        
        query = "SELECT id, timestamp, log_level, log_type, account, action, details FROM logs WHERE 1=1"
        params = []
        
        if log_type and log_type != "ALL":
            query += " AND log_type=?"
            params.append(log_type)

        if level and level != "ALL":
            query += " AND log_level=?"
            params.append(level)
            
        if month and month != "全部月份":
            query += " AND timestamp LIKE ?"
            params.append(f"{month}%")
            
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        c.execute(query, tuple(params))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Failed to read logs: {e}")
        return []


def delete_logs_by_ids(log_ids):
    if not log_ids:
        return 0
    try:
        ids = [int(i) for i in log_ids if str(i).strip()]
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        c.execute(f"DELETE FROM logs WHERE id IN ({placeholders})", tuple(ids))
        deleted = c.rowcount or 0
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        print(f"Failed to delete logs by ids: {e}")
        return 0


def delete_logs(log_type=None, month=None, level=None):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        query = "DELETE FROM logs WHERE 1=1"
        params = []

        if log_type and log_type != "ALL":
            query += " AND log_type=?"
            params.append(log_type)

        if level and level != "ALL":
            query += " AND log_level=?"
            params.append(level)

        if month and month != "全部月份":
            query += " AND timestamp LIKE ?"
            params.append(f"{month}%")

        c.execute(query, tuple(params))
        deleted = c.rowcount or 0
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        print(f"Failed to delete logs: {e}")
        return 0

def get_available_months():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        c.execute("SELECT DISTINCT substr(timestamp, 1, 7) FROM logs ORDER BY timestamp DESC")
        rows = c.fetchall()
        conn.close()
        months = [row[0] for row in rows if row[0]]
        if not months:
            months = [datetime.now().strftime("%Y-%m")]
        return months
    except Exception as e:
        print(f"Failed to read available months: {e}")
        return [datetime.now().strftime("%Y-%m")]
