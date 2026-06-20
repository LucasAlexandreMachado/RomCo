import os
import sys
import subprocess
import sqlite3
import zipfile
import webview
from datetime import datetime
from backend.config import get_config, save_config, SUPPORTED_EXTS, get_active_rom_path
from backend.database import get_db_path, init_db
from backend.utils import format_size, parse_filename

class FilesMixin:
    def scan_folder(self, folder_path=None):
        config = get_config()
        if not folder_path:
            folder_path = get_active_rom_path()
            
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
        
        c.execute('SELECT 1 FROM systems WHERE folder_name = ?', ('Uncategorized',))
        if not c.fetchone():
            c.execute('INSERT INTO systems (folder_name, display_name) VALUES (?, ?)', ('Uncategorized', 'Uncategorized'))
            found_changes = True

        # Migration: delete any systems that have '/' in their folder_name
        c.execute("DELETE FROM systems WHERE folder_name LIKE '%/%'")
        if c.rowcount > 0:
            found_changes = True

        for root, dirs, files in os.walk(folder_path):
            if '.romco' in root: continue
            
            rel_path = os.path.relpath(root, folder_path)
            if rel_path == '.':
                system_name = 'Uncategorized'
                rel_dir = ''
            else:
                rel_path_unix = rel_path.replace(os.sep, '/')
                parts = rel_path_unix.split('/')
                system_name = parts[0]
                rel_dir = rel_path_unix
                
                c.execute('SELECT 1 FROM systems WHERE folder_name = ?', (system_name,))
                if not c.fetchone():
                    c.execute('INSERT INTO systems (folder_name, display_name) VALUES (?, ?)', (system_name, system_name))
                    found_changes = True

            changes = self._scan_directory(root, system_name, rel_dir, c, existing_files, found_files, now, show_all)
            if changes: found_changes = True
                
        deleted_files = existing_files - found_files
        if len(deleted_files) > 0:
            found_changes = True
            for df in deleted_files:
                c.execute('DELETE FROM roms WHERE filename = ?', (df,))
            
        conn.commit()
        conn.close()
        return found_changes

    def _scan_directory(self, dir_path, system_name, rel_dir, cursor, existing_files, found_files, now, show_all):
        changes = False
        if not os.path.exists(dir_path): return changes
        for file in os.listdir(dir_path):
            if file == '.romco': continue
            filepath = os.path.join(dir_path, file)
            if not os.path.isfile(filepath): continue
            
            ext = os.path.splitext(file)[1].lower()
            if show_all or ext in SUPPORTED_EXTS:
                if rel_dir == '':
                    unique_filename = f"Uncategorized/{file}"
                else:
                    unique_filename = f"{rel_dir}/{file}"
                    
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
        folder_path = get_active_rom_path()
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

    def get_settings(self):
        config = get_config()
        return {
            'show_all_files': config.get('show_all_files', False),
            'ra_username': config.get('ra_username', ''),
            'ra_api_key': config.get('ra_api_key', '')
        }

    def set_ra_credentials(self, username, api_key):
        config = get_config()
        config['ra_username'] = username
        config['ra_api_key'] = api_key
        save_config(config)
        return True

    def toggle_show_all_files(self):
        config = get_config()
        val = not config.get('show_all_files', False)
        config['show_all_files'] = val
        save_config(config)
        self.scan_folder()
        return val

    def open_system_folder(self, target_system):
        config = get_config()
        folder_path = get_active_rom_path()
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

    def get_subdirectories(self, base_path):
        config = get_config()
        folder_path = get_active_rom_path()
        if not folder_path: return []
        
        target_dir = os.path.join(folder_path, base_path.replace('/', os.sep))
        if not os.path.exists(target_dir): return []
        
        result = []
        try:
            for item in os.listdir(target_dir):
                if item == '.romco': continue
                if os.path.isdir(os.path.join(target_dir, item)):
                    result.append(item)
        except:
            pass
        return result

    def zip_roms(self, rom_ids):
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
