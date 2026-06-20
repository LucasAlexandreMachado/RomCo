import os
import sqlite3
import json
import random
from backend.config import get_config, get_active_rom_path
from backend.database import get_db_path

class TagsMixin:
    def get_all_tags(self):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path or not os.path.exists(folder_path):
            return []
            
        db_path = get_db_path(folder_path)
        if not os.path.exists(db_path):
            return []
            
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT tags FROM roms')
        rows = c.fetchall()
        conn.close()
        
        all_tags = set()
        for r in rows:
            try:
                tags = json.loads(r[0])
                all_tags.update(tags)
            except:
                pass
        return sorted(list(all_tags))

    def get_tag_colors(self):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path or not os.path.exists(folder_path):
            return {}
            
        db_path = get_db_path(folder_path)
        if not os.path.exists(db_path):
            return {}
            
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT tag, color FROM tag_colors')
        rows = c.fetchall()
        conn.close()
        
        return {r[0]: r[1] for r in rows}

    def set_tag_color(self, tag, color):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO tag_colors (tag, color)
            VALUES (?, ?)
            ON CONFLICT(tag) DO UPDATE SET color=excluded.color
        ''', (tag, color))
        
        conn.commit()
        conn.close()
        return True

    def add_tag(self, rom_ids, tag):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('SELECT color FROM tag_colors WHERE tag = ?', (tag,))
        if not c.fetchone():
            colors = ['#FF453A', '#30D158', '#0A84FF', '#FF9F0A', '#BF5AF2', '#5E5CE6', '#FF375F', '#64D2FF', '#FFD60A']
            random_color = random.choice(colors)
            c.execute('INSERT INTO tag_colors (tag, color) VALUES (?, ?)', (tag, random_color))
        
        for rom_id in rom_ids:
            c.execute('SELECT tags FROM roms WHERE id = ?', (rom_id,))
            row = c.fetchone()
            if row:
                try:
                    tags = json.loads(row[0])
                except:
                    tags = []
                if tag not in tags:
                    tags.append(tag)
                    c.execute('UPDATE roms SET tags = ? WHERE id = ?', (json.dumps(tags), rom_id))
        
        conn.commit()
        conn.close()
        return True

    def delete_tag_globally(self, tag):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('DELETE FROM tag_colors WHERE tag = ?', (tag,))
        
        c.execute('SELECT id, tags FROM roms')
        for row in c.fetchall():
            rom_id = row[0]
            try:
                current_tags = json.loads(row[1])
            except:
                continue
            if tag in current_tags:
                current_tags.remove(tag)
                c.execute('UPDATE roms SET tags = ? WHERE id = ?', (json.dumps(current_tags), rom_id))
                
        conn.commit()
        conn.close()
        return True

    def remove_tag(self, rom_id, tag):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('SELECT tags FROM roms WHERE id = ?', (rom_id,))
        row = c.fetchone()
        if row:
            try:
                tags = json.loads(row[0])
            except:
                tags = []
            if tag in tags:
                tags.remove(tag)
                c.execute('UPDATE roms SET tags = ? WHERE id = ?', (json.dumps(tags), rom_id))
        
        conn.commit()
        conn.close()
        return True
