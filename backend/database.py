"""
SQLite Database Layer for RESCUENET-X
Provides persistent storage for disaster events, rescue units, and dispatch logs.
Data survives server restarts.
"""

import sqlite3
import json
import os
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path

from .config import PROJECT_ROOT, DB_PATH, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG

_db_lock = threading.Lock()

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with dict row access."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables for events, units, and dispatch log."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Events table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            sector TEXT NOT NULL,
            severity INTEGER NOT NULL,
            casualty_count INTEGER NOT NULL,
            summary TEXT NOT NULL,
            confidence REAL NOT NULL,
            source TEXT NOT NULL,
            raw_transcript TEXT,
            verified INTEGER NOT NULL,
            status TEXT NOT NULL,
            assigned_unit TEXT,
            cluster_count INTEGER NOT NULL DEFAULT 1,
            phash TEXT,
            image_url TEXT,
            raw_severity INTEGER,
            urgency REAL,
            location_unknown INTEGER NOT NULL DEFAULT 0,
            timestamp REAL NOT NULL
        )
        """)

        # Rescue Units table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            unit_type TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            status TEXT NOT NULL,
            eta_minutes INTEGER NOT NULL,
            contact TEXT NOT NULL
        )
        """)

        # Dispatch Audit Log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispatch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            unit_id TEXT,
            timestamp REAL NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        )
        """)

        conn.commit()
        conn.close()

# Auto-initialize tables upon module load
init_db()
