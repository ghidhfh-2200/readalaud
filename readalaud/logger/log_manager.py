import sqlite3
import os
from datetime import datetime
import base64

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
    account = base64.urlsafe_b64decode(account).decode("utf-8")
    add_log(account, "AUDIT", action, details)

def log_operation(account, action, details=""):
    account = base64.urlsafe_b64decode(account).decode("utf-8")
    add_log(account, "OPERATION", action, details)

def get_logs(log_type=None, month=None, limit=1000):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        c = conn.cursor()
        
        query = "SELECT timestamp, log_type, account, action, details FROM logs WHERE 1=1"
        params = []
        
        if log_type and log_type != "ALL":
            query += " AND log_type=?"
            params.append(log_type)
            
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
