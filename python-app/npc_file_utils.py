"""
NPC File Path Utility
Utility for managing and searching for NPC.json files in both development and production modes
"""

import os
import sys


def get_npc_file_path():
    """
    Search for NPC.json file in the main project folder
    Main project folder is the current working directory or other folder
    Return a single file per project or others

    Returns:
        String: file path that found or should be used for creating new file
    """

    # Part that was fixed
    if hasattr(sys, "_MEIPASS"):
        # This is production mode - executable
        search_dir = os.path.dirname(sys.executable)
        print(f"[NPC File Utils] Production mode - searching in: {search_dir}")
        # In production usually has NPC.json (capital)
        possible_files = ["NPC.json", "npc.json"]
    else:
        # This is development mode - current project folder that's running files
        search_dir = os.path.abspath(".")
        print(f"[NPC File Utils] Development mode - searching in: {search_dir}")
        # In development usually has npc.json (lowercase)
        possible_files = ["npc.json", "NPC.json"]
    # --- End of fixed part ---

    # Search for existing files
    for filename in possible_files:
        full_path = os.path.join(search_dir, filename)
        if os.path.exists(full_path):
            print(f"[NPC File Utils] Found file: {full_path}")
            return full_path

    # If no file found, use an appropriate name based on mode
    if hasattr(sys, "_MEIPASS"):
        # Production mode uses capital
        default_path = os.path.join(search_dir, "NPC.json")
    else:
        # Development mode uses lowercase
        default_path = os.path.join(search_dir, "npc.json")

    print(f"[NPC File Utils] File not found, will use: {default_path}")
    return default_path


def get_game_info_from_npc_file():
    """
    Read current file and extract info from _game_info

    Returns:
        Dict: information or empty if file not found
    """
    import json

    npc_filepath = get_npc_file_path()
    try:
        with open(npc_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Return if this field exists, if not return empty
        return data.get("_game_info", {})
    except (json.JSONDecodeError, IOError) as e:
        # Cannot read file

        # Return empty if error occurred or file doesn't exist
        return {}


def ensure_npc_file_exists():
    """
    Check if file exists or not, if not create initial file
    """
    import json

    npc_path = get_npc_file_path()
    if not os.path.exists(npc_path):
        # Create initial file
        default_data = {
            "main_characters": [],
            "side_characters": [],
            "monsters": [],
            "locations": [],
            "_game_info": {
                "game_name": "Unknown Game",
                "version": "1.0"
            }
        }
        try:
            with open(npc_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4, ensure_ascii=False)
            print(f"[NPC File Utils] Created initial file at: {npc_path}")
            return True
        except Exception as e:
            print(f"[NPC File Utils] Cannot create initial file: {e}")
            return False
    return True
