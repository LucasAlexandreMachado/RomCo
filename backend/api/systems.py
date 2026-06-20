import os
import sqlite3
import shutil
import re
from backend.config import get_config, get_active_rom_path
from backend.database import get_db_path

class SystemsMixin:
    def get_systems(self):
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
        folder_path = get_active_rom_path()
        if folder_path:
            db_path = get_db_path(folder_path)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('UPDATE systems SET display_name = ? WHERE folder_name = ?', (new_display_name, folder_name))
            conn.commit()
            conn.close()
        return True

    def create_system(self, folder_name):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        folder_name = re.sub(r'[\\/*?:"<>|]', "", folder_name).strip()
        if not folder_name: return False
        
        dest_dir = os.path.join(folder_path, folder_name)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            self.scan_folder(folder_path)
            return True
        return False

    def create_subfolder(self, parent_system, folder_name):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        folder_name = re.sub(r'[\\/*?:"<>|]', "", folder_name).strip()
        if not folder_name: return False
        
        if parent_system == 'Uncategorized':
            dest_dir = os.path.join(folder_path, folder_name)
        else:
            dest_dir = os.path.join(folder_path, parent_system.replace('/', os.sep), folder_name)
            
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            self.scan_folder(folder_path)
            return True
        return False

    def delete_subfolder(self, parent_system, folder_name):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        if parent_system == 'Uncategorized':
            target_dir = os.path.join(folder_path, folder_name)
            parent_dir = folder_path
        else:
            target_dir = os.path.join(folder_path, parent_system.replace('/', os.sep), folder_name)
            parent_dir = os.path.join(folder_path, parent_system.replace('/', os.sep))
            
        if not os.path.exists(target_dir): return False
        
        for file in os.listdir(target_dir):
            source_filepath = os.path.join(target_dir, file)
            if os.path.isfile(source_filepath):
                dest_filepath = os.path.join(parent_dir, file)
                shutil.move(source_filepath, dest_filepath)
                
        try:
            os.rmdir(target_dir)
        except:
            pass
            
        self.scan_folder(folder_path)
        return True

    def rename_subfolder(self, parent_system, old_folder_name, new_folder_name):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return False
        
        new_folder_name = re.sub(r'[\\/*?:"<>|]', "", new_folder_name).strip()
        if not new_folder_name: return False
        
        if parent_system == 'Uncategorized':
            source_dir = os.path.join(folder_path, old_folder_name)
            target_dir = os.path.join(folder_path, new_folder_name)
        else:
            source_dir = os.path.join(folder_path, parent_system.replace('/', os.sep), old_folder_name)
            target_dir = os.path.join(folder_path, parent_system.replace('/', os.sep), new_folder_name)
            
        if not os.path.exists(source_dir) or os.path.exists(target_dir):
            return False
            
        try:
            os.rename(source_dir, target_dir)
            
            db_path = get_db_path(folder_path)
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            old_prefix = f"{parent_system}/{old_folder_name}/" if parent_system != 'Uncategorized' else f"Uncategorized/{old_folder_name}/"
            new_prefix = f"{parent_system}/{new_folder_name}/" if parent_system != 'Uncategorized' else f"Uncategorized/{new_folder_name}/"
            
            c.execute('SELECT id, filename FROM roms WHERE filename LIKE ?', (f"{old_prefix}%",))
            
            for row in c.fetchall():
                new_filename = row[1].replace(old_prefix, new_prefix, 1)
                c.execute('UPDATE roms SET filename = ? WHERE id = ?', (new_filename, row[0]))
                
            conn.commit()
            conn.close()
            
            self.scan_folder(folder_path)
            return True
        except:
            return False

    def delete_system(self, folder_name):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path or folder_name == 'Uncategorized': return False
        
        system_dir = os.path.join(folder_path, folder_name.replace('/', os.sep))
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
