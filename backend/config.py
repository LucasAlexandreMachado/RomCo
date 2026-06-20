import os
import json
import uuid

CONFIG_FILE = 'config.json'
SUPPORTED_EXTS = {'.nes', '.sfc', '.smc', '.gb', '.gbc', '.gba', '.md', '.gen', '.zip', '.7z'}

def get_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except:
            pass
            
    # Migration
    changed = False
    if 'collections' not in config:
        config['collections'] = []
        changed = True
        
    if 'last_rom_path' in config:
        path = config.pop('last_rom_path')
        if path:
            new_id = str(uuid.uuid4())
            config['collections'].append({
                'id': new_id,
                'name': 'Default Library',
                'path': path
            })
            config['active_collection_id'] = new_id
            changed = True
            
    if changed:
        save_config(config)
        
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def get_active_rom_path():
    config = get_config()
    active_id = config.get('active_collection_id')
    if not active_id:
        return None
    for col in config.get('collections', []):
        if col.get('id') == active_id:
            return col.get('path')
    return None
