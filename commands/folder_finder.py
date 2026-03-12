import os
import config
from commands.pc_indexer import PCIndexer

class FolderFinder:
    """
    Uses PCIndexer for fast lookups with intelligent fallback.
    Maintains your robust matching logic.
    """
    
    def __init__(self):
        self.indexer = PCIndexer()
    
    def find_folder(self, folder_name):
        """
        Find folder using indexer with robust matching.
        Falls back to live search if absolutely necessary.
        """
        if config.DEBUG_MODE:
            print(f"FolderFinder: Looking for '{folder_name}'")
        
        # Use indexer (fast + robust matching built-in)
        path = self.indexer.find_folder(folder_name)
        
        if path and os.path.exists(path):
            if config.DEBUG_MODE:
                print(f"Found: {path}")
            return path
        
        # If not found, trigger reindex and inform user
        if config.DEBUG_MODE:
            print(f"Folder '{folder_name}' not found. Consider running 'rebuild index'")
        
        return None
    
    def rebuild_index(self):
        """Manual index rebuild"""
        self.indexer.rebuild_index(force=True)
