import webview
import uuid
from backend.config import get_config, save_config

class CollectionsMixin:
    def get_collections(self):
        config = get_config()
        return {
            'collections': config.get('collections', []),
            'active_collection_id': config.get('active_collection_id')
        }
        
    def add_collection(self, name):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            folder_path = result[0]
            config = get_config()
            new_id = str(uuid.uuid4())
            
            if 'collections' not in config:
                config['collections'] = []
                
            config['collections'].append({
                'id': new_id,
                'name': name,
                'path': folder_path
            })
            config['active_collection_id'] = new_id
            save_config(config)
            
            # Use the existing scan_folder but it will now pull the active path automatically
            self.scan_folder()
            return True
        return False
        
    def set_active_collection(self, collection_id):
        config = get_config()
        # Verify collection exists
        exists = False
        for col in config.get('collections', []):
            if col['id'] == collection_id:
                exists = True
                break
                
        if exists:
            config['active_collection_id'] = collection_id
            save_config(config)
            self.scan_folder()
            return True
        return False
        
    def remove_collection(self, collection_id):
        config = get_config()
        collections = config.get('collections', [])
        new_collections = [c for c in collections if c['id'] != collection_id]
        
        if len(new_collections) == len(collections):
            return False # Nothing removed
            
        config['collections'] = new_collections
        if config.get('active_collection_id') == collection_id:
            if new_collections:
                config['active_collection_id'] = new_collections[0]['id']
            else:
                config['active_collection_id'] = None
                
        save_config(config)
        
        # Rescan to reflect the new active collection (or empty state)
        if config['active_collection_id']:
            self.scan_folder()
        return True
