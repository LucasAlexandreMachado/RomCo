import os
import webview
from backend.api.main_api import Api

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
    webview.start(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
