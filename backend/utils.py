import os
import re

def parse_filename(filename):
    name_ext = os.path.splitext(filename)
    base_name = name_ext[0]
    
    tags = re.findall(r'(\(.*?\)|\[.*?\])', base_name)
    region_str = ' '.join(tags) if tags else 'Unknown'
    
    clean_name = re.sub(r'(\(.*?\)|\[.*?\])', '', base_name).strip()
    return clean_name, region_str

def format_size(size_bytes):
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"
