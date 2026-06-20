import webview
import os
import json
import sqlite3
import re
import shutil
import subprocess
import sys
import zipfile
import random
from datetime import datetime

CONFIG_FILE = 'config.json'
SUPPORTED_EXTS = {'.nes', '.sfc', '.smc', '.gb', '.gbc', '.gba', '.md', '.gen', '.zip', '.7z'}

def get_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def parse_filename(filename):
    name_ext = os.path.splitext(filename)
    base_name = name_ext[0]
    
    tags = re.findall(r'(\(.*?\)|\[.*?\])', base_name)
    region_str = ' '.join(tags) if tags else 'Unknown'
    
    clean_name = re.sub(r'(\(.*?\)|\[.*?\])', '', base_name).strip()
    return clean_name, region_str

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

def format_size(size_bytes):
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"

class Api:
    def __init__(self, window=None):
        self.window = window

    def choose_folder(self):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            folder_path = result[0]
            config = get_config()
            config['last_rom_path'] = folder_path
            save_config(config)
            
            self.scan_folder(folder_path)
            return True
        return False

    def scan_folder(self, folder_path=None):
        config = get_config()
        if not folder_path:
            folder_path = config.get('last_rom_path')
            
        if not folder_path or not os.path.exists(folder_path):
            return False
            
        db_path = get_db_path(folder_path)
        conn = init_db(db_path)
        c = conn.cursor()
        
        c.execute('SELECT filename FROM roms')
        existing_files = {row[0] for row in c.fetchall()}
        found_files = set()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        show_all = config.get('show_all_files', False)
        
        found_changes = False
        
        folders = ['Uncategorized']
        for item in os.listdir(folder_path):
            if item == '.romco': continue
            if os.path.isdir(os.path.join(folder_path, item)):
                folders.append(item)
                
        for folder in folders:
            c.execute('SELECT 1 FROM systems WHERE folder_name = ?', (folder,))
            if not c.fetchone():
                c.execute('INSERT INTO systems (folder_name, display_name) VALUES (?, ?)', (folder, folder))
                found_changes = True
            
        changes1 = self._scan_directory(folder_path, 'Uncategorized', c, existing_files, found_files, now, show_all)
        if changes1: found_changes = True
        
        for folder in folders:
            if folder != 'Uncategorized':
                changes2 = self._scan_directory(os.path.join(folder_path, folder), folder, c, existing_files, found_files, now, show_all)
                if changes2: found_changes = True
                
        deleted_files = existing_files - found_files
        if len(deleted_files) > 0:
            found_changes = True
            for df in deleted_files:
                c.execute('DELETE FROM roms WHERE filename = ?', (df,))
            
        conn.commit()
        conn.close()
        return found_changes

    def _scan_directory(self, dir_path, system_name, cursor, existing_files, found_files, now, show_all):
        changes = False
        if not os.path.exists(dir_path): return changes
        for file in os.listdir(dir_path):
            if file == '.romco': continue
            filepath = os.path.join(dir_path, file)
            if not os.path.isfile(filepath): continue
            
            ext = os.path.splitext(file)[1].lower()
            if show_all or ext in SUPPORTED_EXTS:
                unique_filename = f"{system_name}/{file}"
                found_files.add(unique_filename)
                
                if unique_filename not in existing_files:
                    size = os.path.getsize(filepath)
                    clean_name, region = parse_filename(file)
                    
                    cursor.execute('''
                        INSERT INTO roms (filename, name, system, region, size_bytes, imported_on)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (unique_filename, clean_name, system_name, region, size, now))
                    changes = True
        return changes

    def get_library_summary(self):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path or not os.path.exists(folder_path):
            return "No library selected. Click 'Import Folder' to start."
            
        db_path = get_db_path(folder_path)
        if not os.path.exists(db_path):
            return "Library not scanned yet."
            
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*), SUM(size_bytes), COUNT(DISTINCT system) FROM roms')
        row = c.fetchone()
        conn.close()
        
        count = row[0] or 0
        total_size = row[1] or 0
        systems_count = row[2] or 0
        
        return f"You have a {format_size(total_size)} ROM library with {count} ROMs across {systems_count} systems."

    def get_systems(self):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path or not os.path.exists(folder_path):
            return []
            
        db_path = get_db_path(folder_path)
        if not os.path.exists(db_path):
            return []
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT s.folder_name, s.display_name, COUNT(r.id) as rom_count 
            FROM systems s 
            LEFT JOIN roms r ON s.folder_name = r.system 
            GROUP BY s.folder_name
            HAVING rom_count > 0 OR s.folder_name != 'Uncategorized'
        ''')
        rows = c.fetchall()
        conn.close()
        
        return [dict(r) for r in rows]

    def rename_system(self, folder_name, new_display_name):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if folder_path:
            db_path = get_db_path(folder_path)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('UPDATE systems SET display_name = ? WHERE folder_name = ?', (new_display_name, folder_name))
            conn.commit()
            conn.close()
        return True

    def get_roms(self):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path or not os.path.exists(folder_path):
            return []
            
        db_path = get_db_path(folder_path)
        if not os.path.exists(db_path):
            return []
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT r.*, s.display_name as system_display 
            FROM roms r
            LEFT JOIN systems s ON r.system = s.folder_name
            ORDER BY r.name ASC
        ''')
        rows = c.fetchall()
        conn.close()
        
        result = []
        for r in rows:
            try:
                tags = json.loads(r["tags"])
            except:
                tags = []
                
            result.append({
                "id": r["id"],
                "filename": r["filename"].split('/')[-1],
                "name": r["name"],
                "system": r["system_display"] or r["system"],
                "folder_name": r["system"],
                "region": r["region"],
                "size": format_size(r["size_bytes"]),
                "imported_on": r["imported_on"],
                "is_favorite": r["is_favorite"],
                "tags": tags
            })
        return result

    def get_all_tags(self):
        config = get_config()
        folder_path = config.get('last_rom_path')
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
        folder_path = config.get('last_rom_path')
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
        folder_path = config.get('last_rom_path')
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
        folder_path = config.get('last_rom_path')
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
        folder_path = config.get('last_rom_path')
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Remove from tag_colors
        c.execute('DELETE FROM tag_colors WHERE tag = ?', (tag,))
        
        # Remove from all roms
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
        folder_path = config.get('last_rom_path')
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

    def toggle_favorite(self, rom_id):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if folder_path:
            db_path = get_db_path(folder_path)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('UPDATE roms SET is_favorite = NOT is_favorite WHERE id = ?', (rom_id,))
            conn.commit()
            conn.close()

    def get_settings(self):
        config = get_config()
        return {
            'show_all_files': config.get('show_all_files', False)
        }

    def toggle_show_all_files(self):
        config = get_config()
        val = not config.get('show_all_files', False)
        config['show_all_files'] = val
        save_config(config)
        self.scan_folder()
        return val

    def move_roms(self, rom_ids, target_system):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path or not os.path.exists(folder_path):
            return False
            
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if target_system == 'Uncategorized':
            dest_dir = folder_path
        else:
            dest_dir = os.path.join(folder_path, target_system)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
                
        for rom_id in rom_ids:
            c.execute('SELECT filename, system FROM roms WHERE id = ?', (rom_id,))
            row = c.fetchone()
            if row:
                old_unique_filename = row['filename']
                old_system = row['system']
                filename_only = old_unique_filename.split('/')[-1]
                
                if old_system == 'Uncategorized':
                    source_filepath = os.path.join(folder_path, filename_only)
                else:
                    source_filepath = os.path.join(folder_path, old_system, filename_only)
                
                dest_filepath = os.path.join(dest_dir, filename_only)
                
                if os.path.exists(source_filepath):
                    try:
                        shutil.move(source_filepath, dest_filepath)
                        new_unique_filename = f"{target_system}/{filename_only}"
                        
                        c.execute('''
                            UPDATE roms 
                            SET filename = ?, system = ? 
                            WHERE id = ?
                        ''', (new_unique_filename, target_system, rom_id))
                    except Exception as e:
                        print(f"Error moving file {filename_only}: {e}")
                        
        conn.commit()
        conn.close()
        
        self.scan_folder(folder_path)
        return True

    def open_system_folder(self, target_system):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path: return False
        
        if target_system == 'Uncategorized':
            dest_dir = folder_path
        else:
            dest_dir = os.path.join(folder_path, target_system)
            
        if os.path.exists(dest_dir):
            try:
                if sys.platform == 'win32':
                    os.startfile(dest_dir)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', dest_dir])
                else:
                    subprocess.Popen(['xdg-open', dest_dir])
                return True
            except Exception as e:
                print(f"Error opening folder: {e}")
        return False

    def create_system(self, folder_name):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path: return False
        
        folder_name = re.sub(r'[\\/*?:"<>|]', "", folder_name).strip()
        if not folder_name: return False
        
        dest_dir = os.path.join(folder_path, folder_name)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            self.scan_folder(folder_path)
            return True
        return False

    def delete_system(self, folder_name):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path or folder_name == 'Uncategorized': return False
        
        system_dir = os.path.join(folder_path, folder_name)
        if not os.path.exists(system_dir): return False
        
        for file in os.listdir(system_dir):
            source_filepath = os.path.join(system_dir, file)
            if os.path.isfile(source_filepath):
                dest_filepath = os.path.join(folder_path, file)
                shutil.move(source_filepath, dest_filepath)
                
        try:
            os.rmdir(system_dir)
        except:
            pass
            
        self.scan_folder(folder_path)
        return True

    def delete_roms(self, rom_ids):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        for rom_id in rom_ids:
            c.execute('SELECT filename, system FROM roms WHERE id = ?', (rom_id,))
            row = c.fetchone()
            if row:
                old_unique_filename = row['filename']
                old_system = row['system']
                filename_only = old_unique_filename.split('/')[-1]
                
                if old_system == 'Uncategorized':
                    source_filepath = os.path.join(folder_path, filename_only)
                else:
                    source_filepath = os.path.join(folder_path, old_system, filename_only)
                    
                if os.path.exists(source_filepath):
                    os.remove(source_filepath)
                    
        conn.close()
        self.scan_folder(folder_path)
        return True

    def rename_rom(self, rom_id, new_base_name):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path: return False
        
        new_base_name = re.sub(r'[\\/*?:"<>|]', "", new_base_name).strip()
        if not new_base_name: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT filename, system FROM roms WHERE id = ?', (rom_id,))
        row = c.fetchone()
        if row:
            old_unique_filename = row['filename']
            old_system = row['system']
            filename_only = old_unique_filename.split('/')[-1]
            ext = os.path.splitext(filename_only)[1]
            
            if old_system == 'Uncategorized':
                source_filepath = os.path.join(folder_path, filename_only)
                dest_filepath = os.path.join(folder_path, f"{new_base_name}{ext}")
                new_unique_filename = f"{new_base_name}{ext}"
            else:
                source_filepath = os.path.join(folder_path, old_system, filename_only)
                dest_filepath = os.path.join(folder_path, old_system, f"{new_base_name}{ext}")
                new_unique_filename = f"{old_system}/{new_base_name}{ext}"
                
            if os.path.exists(source_filepath) and not os.path.exists(dest_filepath):
                os.rename(source_filepath, dest_filepath)
                
                clean_name, region = parse_filename(f"{new_base_name}{ext}")
                c.execute('''
                    UPDATE roms 
                    SET filename = ?, name = ?, region = ?
                    WHERE id = ?
                ''', (new_unique_filename, clean_name, region, rom_id))
                
        conn.commit()
        conn.close()
        self.scan_folder(folder_path)
        return True

    def zip_roms(self, rom_ids):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        for rom_id in rom_ids:
            c.execute('SELECT filename, system FROM roms WHERE id = ?', (rom_id,))
            row = c.fetchone()
            if row:
                old_unique_filename = row['filename']
                old_system = row['system']
                filename_only = old_unique_filename.split('/')[-1]
                ext = os.path.splitext(filename_only)[1].lower()
                base = os.path.splitext(filename_only)[0]
                
                if ext in {'.zip', '.7z'}:
                    continue
                
                if old_system == 'Uncategorized':
                    source_filepath = os.path.join(folder_path, filename_only)
                    zip_filepath = os.path.join(folder_path, f"{base}.zip")
                else:
                    source_filepath = os.path.join(folder_path, old_system, filename_only)
                    zip_filepath = os.path.join(folder_path, old_system, f"{base}.zip")
                    
                if os.path.exists(source_filepath):
                    try:
                        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            zipf.write(source_filepath, filename_only)
                        os.remove(source_filepath)
                        
                        new_unique_filename = zip_filepath.replace(folder_path, '').strip(os.sep)
                        new_unique_filename = new_unique_filename.replace('\\', '/')
                        
                        size = os.path.getsize(zip_filepath)
                        c.execute('''
                            UPDATE roms 
                            SET filename = ?, size_bytes = ?
                            WHERE id = ?
                        ''', (new_unique_filename, size, rom_id))
                    except Exception as e:
                        print(f"Error zipping {filename_only}: {e}")
                        
        conn.commit()
        conn.close()
        self.scan_folder(folder_path)
        return True

    def unzip_roms(self, rom_ids):
        config = get_config()
        folder_path = config.get('last_rom_path')
        if not folder_path: return False
        
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        for rom_id in rom_ids:
            c.execute('SELECT filename, system FROM roms WHERE id = ?', (rom_id,))
            row = c.fetchone()
            if row:
                old_unique_filename = row['filename']
                old_system = row['system']
                filename_only = old_unique_filename.split('/')[-1]
                ext = os.path.splitext(filename_only)[1].lower()
                
                if ext != '.zip':
                    continue
                
                if old_system == 'Uncategorized':
                    source_filepath = os.path.join(folder_path, filename_only)
                    dest_dir = folder_path
                else:
                    source_filepath = os.path.join(folder_path, old_system, filename_only)
                    dest_dir = os.path.join(folder_path, old_system)
                    
                if os.path.exists(source_filepath):
                    try:
                        extracted_files = []
                        with zipfile.ZipFile(source_filepath, 'r') as zipf:
                            extracted_files = zipf.namelist()
                            zipf.extractall(dest_dir)
                        
                        os.remove(source_filepath)
                        
                        if extracted_files:
                            new_file = extracted_files[0]
                            new_filepath = os.path.join(dest_dir, new_file)
                            
                            new_unique_filename = new_filepath.replace(folder_path, '').strip(os.sep)
                            new_unique_filename = new_unique_filename.replace('\\', '/')
                            
                            size = os.path.getsize(new_filepath)
                            c.execute('''
                                UPDATE roms 
                                SET filename = ?, size_bytes = ?
                                WHERE id = ?
                            ''', (new_unique_filename, size, rom_id))
                    except Exception as e:
                        print(f"Error unzipping {filename_only}: {e}")
                        
        conn.commit()
        conn.close()
        self.scan_folder(folder_path)
        return True

if __name__ == '__main__':
    api = Api(None)
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'index.html')
    
    window = webview.create_window(
        title='RomCo', 
        url=f'file://{html_path}',
        js_api=api,
        width=1024,
        height=768,
        background_color='#1C1C1E'
    )
    api.window = window
    
    api.scan_folder()
    webview.start()
