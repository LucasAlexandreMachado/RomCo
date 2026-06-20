import sqlite3
import os
import shutil

def get_db_path(folder_path):
    romco_dir = os.path.join(folder_path, '.romco')
    if not os.path.exists(romco_dir):
        os.makedirs(romco_dir, exist_ok=True)
    
    old_db = os.path.join(folder_path, 'romco.db')
    new_db = os.path.join(romco_dir, 'romco.db')
    if os.path.exists(old_db) and not os.path.exists(new_db):
        shutil.move(old_db, new_db)
        
    return new_db

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS systems (
            folder_name TEXT PRIMARY KEY,
            display_name TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS roms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            name TEXT,
            system TEXT,
            region TEXT,
            size_bytes INTEGER,
            is_favorite BOOLEAN DEFAULT 0,
            imported_on DATETIME,
            tags TEXT DEFAULT '[]',
            FOREIGN KEY(system) REFERENCES systems(folder_name)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tag_colors (
            tag TEXT PRIMARY KEY,
            color TEXT
        )
    ''')
    try:
        c.execute('ALTER TABLE roms ADD COLUMN tags TEXT DEFAULT "[]"')
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    return conn
