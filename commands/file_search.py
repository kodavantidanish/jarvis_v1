import os
import config

# Supported file extensions by category
FILE_EXTENSIONS = {
    "word":       [".docx", ".doc"],
    "excel":      [".xlsx", ".xls", ".csv"],
    "powerpoint": [".pptx", ".ppt"],
    "pdf":        [".pdf"],
    "image":      [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "video":      [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "audio":      [".mp3", ".wav", ".flac", ".aac"],
    "text":       [".txt", ".md", ".log"],
    "zip":        [".zip", ".rar", ".7z"],
    "code":       [".py", ".js", ".html", ".css", ".json"],
}

# Flatten all extensions into one set for generic search
ALL_EXTENSIONS = {ext for exts in FILE_EXTENSIONS.values() for ext in exts}

# Default search locations
DEFAULT_SEARCH_PATHS = [
    os.path.expanduser("~\\Downloads"),   # ✅ Downloads first — most common
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Desktop"),
    os.path.expanduser("~\\Pictures"),
    os.path.expanduser("~\\Videos"),
    os.path.expanduser("~\\Music"),
]

class FileSearch:
    def __init__(self):
        pass

    def find_file(self, file_name, search_paths=None, file_type=None):
        """
        Search for a file by name across common locations.
        - file_name: name or partial name to search for
        - search_paths: list of folders to search (defaults to common user folders)
        - file_type: optional filter like 'word', 'pdf', 'image' etc.
        Returns the full path if found, else None.
        """
        if config.DEBUG_MODE:
            print(f"FileSearch: Looking for '{file_name}' (type: {file_type})")

        paths = search_paths or DEFAULT_SEARCH_PATHS
        name_lower = file_name.lower()

        # Determine which extensions to allow
        if file_type:
            allowed_exts = FILE_EXTENSIONS.get(file_type.lower(), ALL_EXTENSIONS)
        else:
            allowed_exts = ALL_EXTENSIONS

        exact_matches = []    # ✅ Exact filename matches (highest priority)
        partial_matches = []  # Partial filename matches (fallback)

        for base_path in paths:
            if not os.path.exists(base_path):
                continue

            for root, dirs, files in os.walk(base_path):
                # Skip inaccessible folders
                dirs[:] = [d for d in dirs if self._is_accessible(os.path.join(root, d))]

                for file in files:
                    file_lower = file.lower()
                    file_base, ext = os.path.splitext(file_lower)

                    # Check extension is allowed
                    if ext not in allowed_exts:
                        continue

                    full_path = os.path.join(root, file)

                    # ✅ FIX: Separate exact vs partial matches
                    if file_base == name_lower:
                        # Exact match — highest priority
                        exact_matches.append(full_path)
                        if config.DEBUG_MODE:
                            print(f"FileSearch: Exact match - {full_path}")
                    elif name_lower in file_base:
                        # Partial match — lower priority
                        partial_matches.append(full_path)
                        if config.DEBUG_MODE:
                            print(f"FileSearch: Found - {full_path}")

        # ✅ FIX: Return exact match first, then fall back to partial
        if exact_matches:
            return exact_matches[0]

        if partial_matches:
            return partial_matches[0]

        if config.DEBUG_MODE:
            print(f"FileSearch: No results for '{file_name}'")

        return None

    def find_files_by_type(self, file_type, search_paths=None):
        """
        List all files of a given type across common locations.
        e.g. find_files_by_type('pdf') returns all PDFs
        """
        paths = search_paths or DEFAULT_SEARCH_PATHS
        allowed_exts = FILE_EXTENSIONS.get(file_type.lower(), [])
        results = []

        for base_path in paths:
            if not os.path.exists(base_path):
                continue

            for root, dirs, files in os.walk(base_path):
                dirs[:] = [d for d in dirs if self._is_accessible(os.path.join(root, d))]

                for file in files:
                    _, ext = os.path.splitext(file.lower())
                    if ext in allowed_exts:
                        results.append(os.path.join(root, file))

        return results

    def _is_accessible(self, path):
        """Check if folder is actually accessible (avoids Windows junction errors)"""
        try:
            os.listdir(path)
            return True
        except (PermissionError, OSError):
            return False