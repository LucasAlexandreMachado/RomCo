import os
import sqlite3
import json
import shutil
import re
from backend.config import get_config, get_active_rom_path
from backend.database import get_db_path
from backend.utils import format_size, parse_filename

class RomsMixin:
    def get_roms(self):
        config = get_config()
        folder_path = get_active_rom_path()
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
                "filename": r["filename"],
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

    def rename_rom(self, rom_id, new_base_name):
        config = get_config()
        folder_path = get_active_rom_path()
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

    def delete_roms(self, rom_ids):
        config = get_config()
        folder_path = get_active_rom_path()
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

    def move_roms(self, rom_ids, target_path):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path or not os.path.exists(folder_path):
            return False
            
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        target_path_clean = target_path.strip('/')
        if target_path_clean == 'Uncategorized':
            dest_dir = folder_path
            new_system = 'Uncategorized'
        else:
            dest_dir = os.path.join(folder_path, target_path_clean.replace('/', os.sep))
            new_system = target_path_clean.split('/')[0]
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
                    source_filepath = os.path.join(folder_path, old_unique_filename.replace('/', os.sep))
                
                dest_filepath = os.path.join(dest_dir, filename_only)
                
                if os.path.exists(source_filepath):
                    try:
                        shutil.move(source_filepath, dest_filepath)
                        new_unique_filename = f"{target_path_clean}/{filename_only}" if target_path_clean != 'Uncategorized' else f"Uncategorized/{filename_only}"
                        
                        c.execute('''
                            UPDATE roms 
                            SET filename = ?, system = ? 
                            WHERE id = ?
                        ''', (new_unique_filename, new_system, rom_id))
                    except Exception as e:
                        print(f"Error moving file {filename_only}: {e}")
                        
        conn.commit()
        conn.close()
        
        self.scan_folder(folder_path)
        return True

    def toggle_favorite(self, rom_id):
        config = get_config()
        folder_path = get_active_rom_path()
        if folder_path:
            db_path = get_db_path(folder_path)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('UPDATE roms SET is_favorite = NOT is_favorite WHERE id = ?', (rom_id,))
            conn.commit()
            conn.close()
