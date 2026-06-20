import os
import json
import sqlite3
import hashlib
import zipfile
import requests
import time
from backend.config import get_config, get_active_rom_path
from backend.database import get_db_path

# Mapping from common system/folder names to RetroAchievements Console IDs
# Users may name their folders differently, so we try common variations
SYSTEM_TO_RA_CONSOLE_ID = {
    # Sega
    'genesis': 1, 'mega drive': 1, 'megadrive': 1, 'sega genesis': 1, 'md': 1, 'gen': 1,
    'n64': 2, 'nintendo 64': 2, 'nintendo64': 2,
    'snes': 3, 'super nintendo': 3, 'super famicom': 3, 'sfc': 3, 'super nes': 3,
    'gb': 4, 'game boy': 4, 'gameboy': 4, 'dmg': 4,
    'gba': 5, 'game boy advance': 5, 'gameboy advance': 5,
    'gbc': 6, 'game boy color': 6, 'gameboy color': 6,
    'nes': 7, 'famicom': 7, 'nintendo': 7, 'fc': 7, 'nintendo entertainment system': 7,
    'pce': 8, 'pc engine': 8, 'turbografx': 8, 'turbografx-16': 8, 'tg16': 8,
    'sega cd': 9, 'segacd': 9, 'mega cd': 9, 'megacd': 9,
    '32x': 10, 'sega 32x': 10,
    'master system': 11, 'sms': 11, 'sega master system': 11,
    'ps1': 12, 'psx': 12, 'playstation': 12, 'playstation 1': 12, 'ps': 12,
    'lynx': 13, 'atari lynx': 13,
    'ngp': 14, 'neo geo pocket': 14, 'neogeo pocket': 14,
    'gg': 15, 'game gear': 15, 'gamegear': 15,
    'gc': 16, 'gamecube': 16, 'ngc': 16,
    'jaguar': 17, 'atari jaguar': 17,
    'nds': 18, 'nintendo ds': 18, 'ds': 18,
    'wii': 19,
    'wii u': 20, 'wiiu': 20,
    'ps2': 21, 'playstation 2': 21,
    'xbox': 22,
    'pokemon mini': 24,
    'atari 2600': 25, '2600': 25,
    'arcade': 27,
    'virtual boy': 28, 'vb': 28,
    'msx': 29,
    'c64': 30, 'commodore 64': 30,
    'sg-1000': 33, 'sg1000': 33,
    'saturn': 39, 'sega saturn': 39,
    'dreamcast': 40, 'dc': 40,
    'psp': 41, 'playstation portable': 41,
    '3do': 43,
    'colecovision': 44,
    'intellivision': 45,
    'vectrex': 46,
    'wonderswan': 53, 'ws': 53,
    'neo geo cd': 56, 'neogeo cd': 56,
    'zx spectrum': 59, 'spectrum': 59,
    '3ds': 62, 'nintendo 3ds': 62,
    'fds': 81, 'famicom disk system': 81,
    'pce cd': 76, 'turbografx-cd': 76,
    # Common ROM folder names
    'roms-ps2': 21, 'roms-psx': 12, 'roms-ps1': 12,
    'roms-gba': 5, 'roms-gb': 4, 'roms-gbc': 6,
    'roms-nes': 7, 'roms-snes': 3, 'roms-n64': 2,
    'roms-sega': 1, 'roms-genesis': 1, 'roms-megadrive': 1,
    'roms-nds': 18, 'roms-ds': 18,
    'roms-psp': 41, 'roms-dreamcast': 40, 'roms-dc': 40,
    'roms-arcade': 27, 'roms-mame': 27,
    'bios-ps233': None,  # Not a real system
}

# Cache for game lists (console_id -> {hash -> game_info})
_hash_cache = {}
_cache_timestamps = {}
CACHE_TTL = 3600  # 1 hour

class RetroAchievementsMixin:
    def get_ra_game_info(self, rom_id):
        config = get_config()
        ra_user = config.get('ra_username', '').strip()
        ra_key = config.get('ra_api_key', '').strip()
        
        if not ra_user or not ra_key:
            return {"error": "Credentials not configured"}
            
        folder_path = get_active_rom_path()
        if not folder_path:
            return {"error": "No active folder"}
            
        db_path = get_db_path(folder_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT filename, system FROM roms WHERE id = ?', (rom_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return {"error": "ROM not found"}
            
        filename = row['filename']
        system = row['system']
        
        if system == 'Uncategorized':
            filepath = os.path.join(folder_path, filename.split('/')[-1])
        else:
            filepath = os.path.join(folder_path, filename.replace('/', os.sep))
            
        if not os.path.exists(filepath):
            return {"error": "File not found"}
        
        # Determine the RA console ID from the system/folder name
        console_id = self._get_console_id(system)
        if not console_id:
            # Try to infer from file extension
            console_id = self._get_console_id_from_extension(filepath)
        
        if not console_id:
            return {"error": f"System '{system}' not supported by RetroAchievements"}
            
        # Calculate MD5
        file_hash = self._calculate_md5(filepath)
        if not file_hash:
            return {"error": "Failed to hash file"}
        
        print(f"RA Debug: system='{system}', console_id={console_id}, hash={file_hash}, file={os.path.basename(filepath)}")
            
        # Look up game ID by hash using cached game list
        game_id = self._find_game_by_hash(file_hash, console_id, ra_user, ra_key)
        
        if not game_id:
            # Try searching by game name as fallback
            game_name = self._extract_game_name(filename)
            game_id = self._find_game_by_name(game_name, console_id, ra_user, ra_key)
            
        if not game_id:
            return {"error": "Game not found in RetroAchievements"}
            
        # Get extended game info with achievements
        game_info = self._ra_api_request("API_GetGameExtended.php", {"i": game_id}, ra_user, ra_key)
        if not game_info:
            return {"error": "Failed to fetch game details"}
            
        return {"success": True, "data": game_info}
    
    def _get_console_id(self, system_name):
        """Map a system/folder name to a RetroAchievements console ID."""
        if not system_name:
            return None
        lookup = system_name.lower().strip()
        return SYSTEM_TO_RA_CONSOLE_ID.get(lookup)
    
    def _get_console_id_from_extension(self, filepath):
        """Infer console ID from file extension."""
        ext = os.path.splitext(filepath)[1].lower()
        
        # Handle zip files - look inside
        if ext == '.zip':
            try:
                with zipfile.ZipFile(filepath, 'r') as zf:
                    names = zf.namelist()
                    if names:
                        ext = os.path.splitext(names[0])[1].lower()
            except:
                return None
        
        ext_to_console = {
            '.nes': 7, '.fds': 81,
            '.sfc': 3, '.smc': 3,
            '.gb': 4, '.sgb': 4,
            '.gbc': 6,
            '.gba': 5,
            '.md': 1, '.gen': 1, '.bin': 1,
            '.sms': 11,
            '.gg': 15,
            '.n64': 2, '.z64': 2, '.v64': 2,
            '.nds': 18,
            '.pce': 8,
            '.iso': None,  # Too ambiguous
            '.cue': None,
        }
        return ext_to_console.get(ext)
    
    def _extract_game_name(self, filename):
        """Extract a clean game name from a filename for search."""
        # Get just the file name without path and extension
        name = os.path.splitext(filename.split('/')[-1])[0]
        # Remove common parenthetical tags like (USA), (Europe), etc.
        import re
        name = re.sub(r'\s*\([^)]*\)', '', name)
        name = re.sub(r'\s*\[[^\]]*\]', '', name)
        return name.strip()
    
    def _find_game_by_hash(self, file_hash, console_id, user, key):
        """Look up a game ID by hash using the cached game list."""
        global _hash_cache, _cache_timestamps
        
        cache_key = console_id
        now = time.time()
        
        # Check if we need to refresh the cache
        if cache_key not in _hash_cache or (now - _cache_timestamps.get(cache_key, 0)) > CACHE_TTL:
            # Fetch the game list with hashes for this console
            game_list = self._ra_api_request(
                "API_GetGameList.php",
                {"i": console_id, "h": 1, "f": 1},
                user, key
            )
            
            if game_list and isinstance(game_list, list):
                hash_map = {}
                for game in game_list:
                    game_id = game.get('ID')
                    hashes = game.get('Hashes', [])
                    if isinstance(hashes, list):
                        for h in hashes:
                            hash_map[h.lower()] = game_id
                
                _hash_cache[cache_key] = hash_map
                _cache_timestamps[cache_key] = now
                print(f"RA Debug: Cached {len(hash_map)} hashes for console {console_id}")
            else:
                print(f"RA Debug: Failed to fetch game list for console {console_id}")
                return None
        
        # Look up the hash
        return _hash_cache.get(cache_key, {}).get(file_hash.lower())
    
    def _find_game_by_name(self, game_name, console_id, user, key):
        """Fallback: try to find a game by name match in the cached game list."""
        global _hash_cache, _cache_timestamps
        
        cache_key = console_id
        now = time.time()
        
        # Make sure we have the game list cached
        if cache_key not in _hash_cache or (now - _cache_timestamps.get(cache_key, 0)) > CACHE_TTL:
            game_list = self._ra_api_request(
                "API_GetGameList.php",
                {"i": console_id, "h": 1, "f": 1},
                user, key
            )
            if game_list and isinstance(game_list, list):
                hash_map = {}
                for game in game_list:
                    game_id = game.get('ID')
                    hashes = game.get('Hashes', [])
                    if isinstance(hashes, list):
                        for h in hashes:
                            hash_map[h.lower()] = game_id
                _hash_cache[cache_key] = hash_map
                _cache_timestamps[cache_key] = now
        
        # We need to re-fetch the game list to search by name (hash_map doesn't have titles)
        # Use a lightweight request with no hashes
        game_list = self._ra_api_request(
            "API_GetGameList.php",
            {"i": console_id, "f": 1},
            user, key
        )
        
        if not game_list or not isinstance(game_list, list):
            return None
        
        search_name = game_name.lower().strip()
        
        # Try exact match first
        for game in game_list:
            title = game.get('Title', '').lower().strip()
            if title == search_name:
                return game.get('ID')
        
        # Try partial match
        for game in game_list:
            title = game.get('Title', '').lower().strip()
            if search_name in title or title in search_name:
                return game.get('ID')
        
        return None
        
    def _calculate_md5(self, filepath):
        try:
            ext = os.path.splitext(filepath)[1].lower()
            md5 = hashlib.md5()
            
            def hash_file_obj(f, is_nes, is_snes, file_size):
                if is_nes:
                    f.read(16) # Skip iNES header
                elif is_snes and file_size % 1024 == 512:
                    f.read(512) # Skip SNES copier header
                    
                for chunk in iter(lambda: f.read(4096), b""):
                    md5.update(chunk)
                return md5.hexdigest()

            if ext == '.zip':
                with zipfile.ZipFile(filepath, 'r') as zf:
                    names = zf.namelist()
                    if names:
                        info = zf.getinfo(names[0])
                        inner_ext = os.path.splitext(names[0])[1].lower()
                        with zf.open(names[0]) as f:
                            return hash_file_obj(f, inner_ext == '.nes', inner_ext in ['.sfc', '.smc'], info.file_size)
            
            # Default hash
            file_size = os.path.getsize(filepath)
            with open(filepath, "rb") as f:
                return hash_file_obj(f, ext == '.nes', ext in ['.sfc', '.smc'], file_size)
                
        except Exception as e:
            print(f"RA Hash Error: {e}")
            return None

    def _ra_api_request(self, endpoint, params, user, key):
        url = f"https://retroachievements.org/API/{endpoint}"
        query = {"z": user, "y": key}
        query.update(params)
        
        try:
            response = requests.get(url, params=query, timeout=30, headers={'User-Agent': 'ROM-Manager/1.0'})
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 404:
                print(f"RA API HTTP Error: {e}")
            return None
        except Exception as e:
            print(f"RA API Error: {e}")
            return None
