import os
import json
import re
import threading
from datetime import datetime
import config

class PCIndexer:
    """
    Hybrid indexer: Pre-indexes PC for speed, but uses robust matching logic.
    Combines fast lookups with flexible search strategies.
    """
    
    def __init__(self):
        self.user_home = os.path.expanduser("~")
        self.index_file = os.path.join(self.user_home, ".jarvis_pc_index.json")
        
        # Separate indexes
        self.folder_index = {}  # {'ml': ['E:\\ML', 'C:\\Users\\Danish\\ML']}
        self.app_index = {}     # {'chrome': ['C:\\...\\chrome.lnk']}
        
        self.skip_folders = {
            'appdata', 'application data', '$recycle.bin',
            'system volume information', 'windows', 'windows.old',
            'program files', 'program files (x86)', 'programdata',
            'node_modules', '.git', '__pycache__', 'venv', '.venv',
            'cache', 'temp', 'tmp', 'new folder', 'new folder (2)',
            'new folder (3)', 'recycle.bin', 'onedrive'
        }
        
        # Search roots with depth limits
        self.search_roots = [
    (self.user_home, 4, "user"),      # ✅ FIX: Increased depth from 3 to 4
    ("C:\\", 1, "system"),
    ("D:\\", 4, "data"),
    ("E:\\", 4, "data"),
    ("F:\\", 4, "data"),
    # ✅ FIX: Explicitly added Downloads with deep scan
    (os.path.expanduser("~\\Downloads"), 5, "downloads"),
    (os.path.expanduser("~\\Documents"), 5, "documents"),
    (os.path.expanduser("~\\Desktop"), 5, "desktop"),
]
        
        # Load existing index
        self._load_index()
        
        # Auto-rebuild if needed (in background)
        if self._needs_reindex():
            if config.DEBUG_MODE:
                print("JARVIS: Rebuilding PC index in background...")
            threading.Thread(target=self.rebuild_index, daemon=True).start()
    
    def _normalize(self, name):
        """
        ✅ FIX: Normalize a name for fuzzy matching.
        Strips punctuation, dashes, underscores, extra spaces.
        e.g. 'UD - Unit 3' -> 'ud unit 3'
             'UD-Unit3'     -> 'ud unit3'
             'UD_Unit_3'    -> 'ud unit 3'
        """
        name = name.lower()
        # Replace dashes, underscores, dots with spaces
        name = re.sub(r'[-_.]', ' ', name)
        # Remove all other punctuation except alphanumeric and spaces
        name = re.sub(r'[^\w\s]', '', name)
        # Collapse multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _fuzzy_match(self, search, key):
        """
        ✅ FIX: Compare normalized versions of both strings.
        Returns a score (0 = no match, 100 = exact).
        """
        search_norm = self._normalize(search)
        key_norm = self._normalize(key)

        if search_norm == key_norm:
            return 100   # Exact after normalization
        if key_norm.startswith(search_norm):
            return 90    # Key starts with search
        if key_norm.endswith(search_norm):
            return 85    # Key ends with search
        if search_norm in key_norm:
            return 70    # Search is substring of key
        if key_norm in search_norm:
            return 50    # Key is substring of search

        # ✅ FIX: Word-level matching — all words in search must appear in key
        search_words = set(search_norm.split())
        key_words = set(key_norm.split())
        if search_words and search_words.issubset(key_words):
            return 75    # All search words found in key
        if search_words and key_words.issubset(search_words):
            return 60    # All key words found in search

        return 0  # No match

    def find_folder(self, folder_name):
        """
        Find folder with smart prioritization and robust matching.
        """
        folder_lower = folder_name.lower()
        
        if config.DEBUG_MODE:
            print(f"PCIndexer: Searching for folder '{folder_name}'")
        
        # Special cases
        if folder_lower in ["danish", "user", "home"]:
            return self.user_home
        
        # Strategy 1: Exact match on raw key
        if folder_lower in self.folder_index:
            paths = self.folder_index[folder_lower]
            return self._prioritize_path(paths, folder_lower)
        
        # Strategy 2: Fuzzy/normalized matching
        best_match = self._flexible_folder_match(folder_lower)
        if best_match:
            return best_match
        
        if config.DEBUG_MODE:
            print(f"Folder '{folder_name}' not found in index")
        
        return None
    
    def find_app(self, app_name):
        """
        Find application with robust matching.
        """
        app_lower = app_name.lower()
        app_clean = app_lower.replace('microsoft ', '').replace('ms ', '')
        
        if config.DEBUG_MODE:
            print(f"PCIndexer: Searching for app '{app_name}' (cleaned: '{app_clean}')")
        
        # Strategy 1: Exact match
        if app_clean in self.app_index:
            return self._get_best_app(self.app_index[app_clean])
        
        # Strategy 2: Fuzzy matching
        best_match = self._flexible_app_match(app_clean)
        if best_match:
            return best_match
        
        if config.DEBUG_MODE:
            print(f"App '{app_name}' not found in index")
        
        return None
    
    def _flexible_folder_match(self, folder_name):
        """
        ✅ FIX: Fuzzy folder matching using normalized comparison.
        Handles dashes, underscores, spaces, mixed cases.
        e.g. 'UD - Unit 3' matches 'ud - unit 3' or 'UD_Unit_3' etc.
        """
        matches = []
        
        skip_generic = {'new folder', 'folder', 'temp', 'tmp'}
        
        for key, paths in self.folder_index.items():
            if key in skip_generic:
                continue
            
            # ✅ FIX: Use fuzzy scoring instead of raw substring match
            score = self._fuzzy_match(folder_name, key)
            
            if score > 0:
                matches.append((score, paths))
        
        if matches:
            matches.sort(key=lambda x: x[0], reverse=True)
            best_paths = matches[0][1]
            return self._prioritize_path(best_paths, folder_name)
        
        return None
    
    def _flexible_app_match(self, app_name):
        """
        ✅ FIX: Fuzzy app matching using normalized comparison.
        """
        unwanted = ['uninstall', 'readme', 'help', 'send to', 'support']
        matches = []
        
        for key, paths in self.app_index.items():
            if any(skip in key for skip in unwanted):
                continue
            
            # ✅ FIX: Use fuzzy scoring
            score = self._fuzzy_match(app_name, key)
            
            if score > 0:
                matches.append((score, paths))
        
        if matches:
            matches.sort(key=lambda x: x[0], reverse=True)
            return self._get_best_app(matches[0][1])
        
        return None
    
    def _prioritize_path(self, paths, search_term):
        """
        Prioritize paths intelligently:
        1. Local user paths (NOT OneDrive)
        2. Exact folder name match
        3. Data drives (E:\, D:\)
        4. OneDrive (last resort)
        """
        if not paths:
            return None
        
        non_onedrive_paths = [p for p in paths if 'onedrive' not in p.lower()]
        onedrive_paths = [p for p in paths if 'onedrive' in p.lower()]
        
        # Priority 1: Local user home paths
        local_user_paths = [p for p in non_onedrive_paths if p.startswith(self.user_home)]
        if local_user_paths:
            exact = [p for p in local_user_paths if os.path.basename(p).lower() == search_term.lower()]
            if exact:
                return exact[0]
            return local_user_paths[0]
        
        # Priority 2: Data drives
        data_paths = [p for p in non_onedrive_paths if p.startswith(('E:\\', 'D:\\', 'F:\\'))]
        if data_paths:
            exact = [p for p in data_paths if os.path.basename(p).lower() == search_term.lower()]
            if exact:
                return exact[0]
            return data_paths[0]
        
        # Priority 3: Any other non-OneDrive path
        if non_onedrive_paths:
            return non_onedrive_paths[0]
        
        # Priority 4: OneDrive (last resort)
        if onedrive_paths:
            if config.DEBUG_MODE:
                print(f"Warning: Only OneDrive path found for '{search_term}'")
            return onedrive_paths[0]
        
        return None
    
    def _get_best_app(self, paths):
        """Get the best app path (prefer non-uninstaller shortcuts)"""
        if not paths:
            return None
        good_paths = [p for p in paths if 'uninstall' not in p.lower()]
        if good_paths:
            return good_paths[0]
        return paths[0]
    
    def rebuild_index(self, force=False):
        """Rebuild the entire index."""
        if not force and not self._needs_reindex():
            return
        
        if config.DEBUG_MODE or force:
            print("JARVIS: Indexing your PC...")
        
        start_time = datetime.now()
        
        self.folder_index = {}
        self.app_index = {}
        
        for root_path, max_depth, category in self.search_roots:
            if os.path.exists(root_path):
                self._index_folders(root_path, 0, max_depth, category)
        
        self._index_applications()
        self._save_index()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if config.DEBUG_MODE or force:
            print(f"JARVIS: Indexing complete! Found {len(self.folder_index)} folders and {len(self.app_index)} apps in {elapsed:.1f}s")
    
    def _index_folders(self, base_path, current_depth, max_depth, category):
        """Recursively index folders"""
        if current_depth > max_depth:
            return
        
        try:
            items = os.listdir(base_path)
        except (PermissionError, OSError):
            return
        
        for item in items:
            if item.startswith(('$', '.', '~')):
                continue
            
            item_lower = item.lower()
            
            if item_lower in self.skip_folders:
                continue
            
            item_path = os.path.join(base_path, item)
            
            if os.path.isdir(item_path):
                try:
                    os.listdir(item_path)
                    
                    if item_lower not in self.folder_index:
                        self.folder_index[item_lower] = []
                    
                    if item_path not in self.folder_index[item_lower]:
                        self.folder_index[item_lower].append(item_path)
                    
                    self._index_folders(item_path, current_depth + 1, max_depth, category)
                
                except (PermissionError, OSError):
                    continue
    
    def _index_applications(self):
        """Index all .lnk shortcuts in Start Menu"""
        start_menu_paths = [
            os.path.join(self.user_home, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
        ]
        
        for start_path in start_menu_paths:
            if not os.path.exists(start_path):
                continue
            
            for root, dirs, files in os.walk(start_path):
                for file in files:
                    if file.endswith('.lnk'):
                        app_name = file[:-4].lower()
                        app_path = os.path.join(root, file)
                        app_name_clean = app_name.replace('microsoft ', '').replace('ms ', '')
                        
                        for name in [app_name, app_name_clean]:
                            if name not in self.app_index:
                                self.app_index[name] = []
                            if app_path not in self.app_index[name]:
                                self.app_index[name].append(app_path)
    
    def _needs_reindex(self):
        """Check if index is older than 24 hours"""
        if not self.folder_index or not self.app_index:
            return True
        if not os.path.exists(self.index_file):
            return True
        try:
            mod_time = os.path.getmtime(self.index_file)
            age_hours = (datetime.now().timestamp() - mod_time) / 3600
            return age_hours > 24
        except:
            return True
    
    def _save_index(self):
        """Save index to JSON file"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump({
                    'folders': self.folder_index,
                    'apps': self.app_index,
                    'timestamp': datetime.now().timestamp(),
                    'version': '1.2'
                }, f, indent=2)
        except Exception as e:
            if config.DEBUG_MODE:
                print(f"Warning: Could not save index: {e}")
    
    def _load_index(self):
        """Load index from JSON file"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    self.folder_index = data.get('folders', {})
                    self.app_index = data.get('apps', {})
                    if config.DEBUG_MODE:
                        print(f"Loaded index: {len(self.folder_index)} folders, {len(self.app_index)} apps")
            except Exception as e:
                if config.DEBUG_MODE:
                    print(f"Could not load index: {e}")
    
    def get_stats(self):
        """Get indexing statistics"""
        age_hours = None
        if os.path.exists(self.index_file):
            try:
                mod_time = os.path.getmtime(self.index_file)
                age_hours = (datetime.now().timestamp() - mod_time) / 3600
            except:
                pass
        return {
            'folders': len(self.folder_index),
            'apps': len(self.app_index),
            'index_age_hours': age_hours
        }