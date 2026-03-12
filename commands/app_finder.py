import os
import config
from commands.pc_indexer import PCIndexer

class AppFinder:
    def __init__(self):
        # Use the indexer as primary source
        self.indexer = PCIndexer()
        
        # Start Menu paths (fallback for live search)
        self.start_menu_paths = [
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
        ]
    
    def find_app(self, app_name):
        """
        Search for an app using indexer first, then fallback to live search.
        Combines speed of indexing with robustness of your original logic.
        """
        app_lower = app_name.lower()
        
        if config.DEBUG_MODE:
            print(f"AppFinder: Searching for app '{app_name}'")
        
        # Strategy 1: Use indexer (FAST - 0.001s)
        result = self.indexer.find_app(app_name)
        if result and os.path.exists(result):
            if config.DEBUG_MODE:
                print(f"Found in index: {result}")
            return result
        
        # Strategy 2: Live search (FALLBACK - slower but thorough)
        if config.DEBUG_MODE:
            print("Not found in index, performing live search...")
        
        result = self._search_start_menu(app_lower)
        if result:
            if config.DEBUG_MODE:
                print(f"Found via live search: {result}")
            # Trigger reindex in background so next time it's in the index
            import threading
            threading.Thread(target=self.indexer.rebuild_index, kwargs={'force': True}, daemon=True).start()
        
        return result
    
    def _search_start_menu(self, app_name):
        """
        Your original robust search logic - used as fallback.
        Search Start Menu for shortcuts with flexible matching.
        """
        # Clean app name (your logic)
        app_name_clean = app_name.lower()
        app_name_clean = app_name_clean.replace('microsoft ', '')
        app_name_clean = app_name_clean.replace('ms ', '')
        
        for base_path in self.start_menu_paths:
            if not os.path.exists(base_path):
                continue
            
            if config.DEBUG_MODE:
                print(f"Live searching in: {base_path}")
            
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.lower().endswith('.lnk'):
                        file_lower = file.lower().replace('.lnk', '')
                        
                        # Skip unwanted shortcuts (your logic)
                        if any(skip in file_lower for skip in ['send to', 'uninstall', 'readme', 'help']):
                            continue
                        
                        # Flexible matching: check both ways (your logic)
                        if app_name_clean in file_lower or file_lower in app_name_clean:
                            found_path = os.path.join(root, file)
                            if config.DEBUG_MODE:
                                print(f"Live search found: {found_path}")
                            return found_path
        
        if config.DEBUG_MODE:
            print(f"App not found in live search")
        
        return None
    
    def rebuild_index(self):
        """Manual index rebuild"""
        self.indexer.rebuild_index(force=True)