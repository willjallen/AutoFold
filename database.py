import requests
import sqlite3
import json
import time

class Database:
    def __init__(self):
        pass



# Initialize SQLite database
conn = sqlite3.connect("manifold.db")
cursor = conn.cursor()

# Create tables
cursor.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, data TEXT, timestamp INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY, data TEXT, timestamp INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS markets (id TEXT PRIMARY KEY, data TEXT, timestamp INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS user_assets (id TEXT PRIMARY KEY, data TEXT, timestamp INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS user_predictions (id TEXT PRIMARY KEY, data TEXT, timestamp INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS market_comments (id TEXT PRIMARY KEY, data TEXT, timestamp INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS market_trades (id TEXT PRIMARY KEY, data TEXT, timestamp INTEGER)")

# Commit changes and close connection
conn.commit()
conn.close()

# General function to store data in SQLite
def store_data(table, id, data):
    conn = sqlite3.connect("manifold.db")
    cursor = conn.cursor()
    cursor.execute(f"REPLACE INTO {table} (id, data, timestamp) VALUES (?, ?, ?)", (id, json.dumps(data), int(time.time())))
    conn.commit()
    conn.close()

# General function to retrieve data from SQLite
def get_data(table, id):
    conn = sqlite3.connect("manifold.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT data FROM {table} WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None