import sqlite3
import os
from datetime import datetime

DB_PATH = "./data/system_log.db"

def init_db():
    os.makedirs("./data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  log_type TEXT,
                  account TEXT,
                  action TEXT,
                  details TEXT)''')
    conn.commit()
    conn.close()

def add_log(account, log_type, action, details=""):
    """
    log_type: "AUDIT" or "OPERATION"
    """
    if not account:
        account = "SYSTEM"
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        c.execute("INSERT INTO logs (timestamp, log_type, account, action, details) VALUES (?, ?, ?, ?, ?)",
                  (timestamp, log_type, account, action, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to write log: {e}")

def log_audit(account, action, details=""):
    add_log(account, "AUDIT", action, details)

def log_operation(account, action, details=""):
    add_log(account, "OPERATION", action, details)

def get_logs(log_type=None, limit=1000):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        if log_type and log_type != "ALL":
            c.execute("SELECT timestamp, log_type, account, action, details FROM logs WHERE log_type=? ORDER BY id DESC LIMIT ?", (log_type, limit))
        else:
            c.execute("SELECT timestamp, log_type, account, action, details FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Failed to read logs: {e}")
        return []
