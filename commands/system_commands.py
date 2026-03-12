import os
import re
import subprocess
import config
from commands.app_finder import AppFinder
from commands.folder_finder import FolderFinder
from commands.file_search import FileSearch  # ✅ NEW

class SystemCommands:
    def __init__(self):
        self.common_paths = config.COMMON_PATHS
        self.app_finder = AppFinder()
        self.folder_finder = FolderFinder()
        self.file_search = FileSearch()  # ✅ NEW
        
        # Context tracking
        self.current_folder = None
        self.navigation_history = []

    def _is_accessible(self, path):
        """
        Check if a folder actually exists AND is accessible.
        os.path.exists() returns True for junction points like
        'C:\\Documents and Settings' but they throw PermissionError.
        """
        try:
            os.listdir(path)
            return True
        except (PermissionError, OSError):
            return False

    def _resolve_drive(self, target):
        """
        Detect if target refers to a drive letter.
        Handles: 'd_drive', 'd drive', 'd:', 'D', 'drive d', etc.
        """
        if not target:
            return None
        
        t = target.lower().strip()
        
        patterns = [
            r'^([a-z])_drive$',    # d_drive
            r'^([a-z])\s*drive$',  # d drive / ddrive
            r'^drive\s*([a-z])$',  # drive d
            r'^([a-z]):/?$',       # d: or d:/
            r'^([a-z])$',          # just a single letter like "d"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, t)
            if match:
                letter = match.group(1).upper()
                drive_path = f"{letter}:\\"
                if os.path.exists(drive_path):
                    return drive_path
        
        return None

    def open_folder(self, target, path=None):
        """Open a folder in Windows Explorer with context awareness"""
        folder_path = None
        
        try:
            # Layer 1: Use provided path directly if valid and accessible
            if path and self._is_accessible(path):
                subprocess.Popen(f'explorer "{path}"')
                self._update_context(path)
                return f"Opening {target}."
            
            # Layer 2: Check if target is a drive letter
            drive_path = self._resolve_drive(target)
            if drive_path:
                subprocess.Popen(f'explorer "{drive_path}"')
                self._update_context(drive_path)
                return f"Opening {drive_path}."
            
            # Layer 3: Check if target is inside current folder (context awareness)
            if self.current_folder:
                context_path = self._search_in_current_folder(target)
                if context_path and self._is_accessible(context_path):
                    subprocess.Popen(f'explorer "{context_path}"')
                    self._update_context(context_path)
                    return f"Opening {target} in current folder at {context_path}."
            
            # Layer 4: Check common paths (fast lookup)
            if target:
                folder_path = self.common_paths.get(target.lower())
                if folder_path and self._is_accessible(folder_path):
                    subprocess.Popen(f'explorer "{folder_path}"')
                    self._update_context(folder_path)
                    return f"Opening {target}."
            
            # Layer 5: Global folder search via FolderFinder
            found_folder = self.folder_finder.find_folder(target)
            if found_folder and self._is_accessible(found_folder):
                subprocess.Popen(f'explorer "{found_folder}"')
                self._update_context(found_folder)
                return f"Found and opening {target} at {found_folder}."
            
            return f"I couldn't find '{target}'."
                
        except Exception as e:
            if config.DEBUG_MODE:
                print(f"Error opening folder: {e}")
                print(f"Target: {target}, Path: {folder_path}")
            return "There was an error opening that folder."
    
    def _search_in_current_folder(self, target):
        """
        Search for a subfolder inside the current folder.
        Enables: 'I'm in Pictures, open screenshots' functionality.
        """
        if not self.current_folder or not self._is_accessible(self.current_folder):
            return None
        
        target_lower = target.lower()
        
        try:
            items = os.listdir(self.current_folder)
            
            for item in items:
                item_lower = item.lower()
                item_path = os.path.join(self.current_folder, item)
                
                if os.path.isdir(item_path):
                    # Exact match
                    if item_lower == target_lower:
                        return item_path
                    # Partial match
                    if target_lower in item_lower or item_lower in target_lower:
                        return item_path
        
        except (PermissionError, OSError):
            pass
        
        return None
    
    def _update_context(self, folder_path):
        """Update current location and history"""
        if folder_path and self._is_accessible(folder_path):
            if self.current_folder:
                self.navigation_history.append(self.current_folder)
            self.current_folder = folder_path
            
            if config.DEBUG_MODE:
                print(f"Context updated: Now in {folder_path}")
    
    def go_back(self):
        """Go back to previous folder"""
        if not self.navigation_history:
            return "No previous folder to go back to."
        
        previous_folder = self.navigation_history.pop()
        
        if self._is_accessible(previous_folder):
            subprocess.Popen(f'explorer "{previous_folder}"')
            self.current_folder = previous_folder
            return f"Going back to {previous_folder}."
        else:
            return "Previous folder no longer exists."
    
    def go_up(self):
        """Go to parent folder"""
        if not self.current_folder:
            return "No current folder to go up from."
        
        parent_folder = os.path.dirname(self.current_folder)
        
        if self._is_accessible(parent_folder):
            subprocess.Popen(f'explorer "{parent_folder}"')
            self._update_context(parent_folder)
            return f"Going up to {parent_folder}."
        else:
            return "Cannot go up from here."
    
    def show_current_location(self):
        """Show where user currently is"""
        if self.current_folder:
            return f"You are currently in: {self.current_folder}"
        else:
            return "No folder opened yet."
    
    def list_current_folder(self):
        """List contents of current folder"""
        if not self.current_folder or not self._is_accessible(self.current_folder):
            return "No current folder to list."
        
        try:
            items = os.listdir(self.current_folder)
            folders = [item for item in items if os.path.isdir(os.path.join(self.current_folder, item))]
            files = [item for item in items if os.path.isfile(os.path.join(self.current_folder, item))]
            
            result = f"\nCurrent folder: {self.current_folder}\n"
            result += f"\nFolders ({len(folders)}):\n"
            for folder in sorted(folders)[:20]:
                result += f"  📁 {folder}\n"
            
            if len(folders) > 20:
                result += f"  ... and {len(folders) - 20} more\n"
            
            result += f"\nFiles ({len(files)}):\n"
            for file in sorted(files)[:10]:
                result += f"  📄 {file}\n"
            
            if len(files) > 10:
                result += f"  ... and {len(files) - 10} more\n"
            
            return result
        
        except Exception as e:
            return f"Error listing folder: {e}"

    def open_file_by_name(self, file_name, file_type=None, search_paths=None):
        """
        ✅ NEW: Search for a file by name and open it with its default app.
        Works for Word, PDF, PPT, Excel, images, etc.
        """
        if config.DEBUG_MODE:
            print(f"Opening file: '{file_name}' (type: {file_type})")

        # Search in current folder first if one is open
        if self.current_folder:
            result = self.file_search.find_file(
                file_name,
                search_paths=[self.current_folder],
                file_type=file_type
            )
            if result:
                os.startfile(result)
                return f"Opening {os.path.basename(result)}."

        # Then search common locations
        result = self.file_search.find_file(
            file_name,
            search_paths=search_paths,
            file_type=file_type
        )

        if result:
            os.startfile(result)
            return f"Opening {os.path.basename(result)}."

        return f"I couldn't find a file named '{file_name}'."

    def open_file(self, target, path=None):
        """Open a file with default application via exact path"""
        try:
            if path and os.path.exists(path):
                os.startfile(path)
                return f"Opening {target}."
            else:
                return f"I couldn't find '{target}'."
                
        except Exception as e:
            if config.DEBUG_MODE:
                print(f"Error opening file: {e}")
            return "There was an error opening that file."
    
    def open_app(self, target):
        """Launch an application"""
        apps = {
            "chrome":      {"type": "path", "cmd": r"C:\Program Files\Google\Chrome\Application\chrome.exe"},
            "notepad":     {"type": "exe",  "cmd": "notepad.exe"},
            "calculator":  {"type": "exe",  "cmd": "calc.exe"},
            "explorer":    {"type": "exe",  "cmd": "explorer.exe"},
            "cmd":         {"type": "exe",  "cmd": "cmd.exe"},
            "vscode":      {"type": "exe",  "cmd": "code"},
            "outlook":     {"type": "start","cmd": "outlookmail:"},
            "paint":       {"type": "exe",  "cmd": "mspaint.exe"},
            "mspaint":     {"type": "exe",  "cmd": "mspaint.exe"},
            "whatsapp":    {"type": "start","cmd": "whatsapp:"},
            "spotify":     {"type": "start","cmd": "spotify:"},
        }
        
        try:
            target_lower = target.lower()
            
            if target_lower in apps:
                app_info = apps[target_lower]
                app_type = app_info["type"]
                app_cmd  = app_info["cmd"]
                
                if app_type == "exe":
                    subprocess.Popen(app_cmd, shell=True)
                elif app_type == "start":
                    subprocess.Popen(f"start {app_cmd}", shell=True)
                elif app_type == "path":
                    subprocess.Popen(f'"{app_cmd}"', shell=True)
                
                return f"Launching {target}."
            
            # Fallback: Search for app via AppFinder
            found_app = self.app_finder.find_app(target)
            if found_app:
                os.startfile(found_app)
                return f"Found and launching {target}."
            
            return f"I couldn't find '{target}'."
                
        except Exception as e:
            if config.DEBUG_MODE:
                print(f"Error launching app: {e}")
            return f"I couldn't launch {target}."