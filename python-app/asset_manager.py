import tkinter as tk
from PIL import ImageTk, Image
import os
import logging


class AssetManager:
    _icon_cache = {}

    @staticmethod
    def get_asset_path(file_name: str) -> str:
        """Finds the correct path for an asset file."""
        # Check assets directory first
        assets_path = os.path.join("assets", file_name)
        if os.path.exists(assets_path):
            return assets_path
        
        # Fallback to current directory
        if os.path.exists(file_name):
            return file_name

        raise FileNotFoundError(f"Asset '{file_name}' not found in assets/ or current directory.")

    @staticmethod
    def load_icon(file_name: str, size: tuple = (20, 20)):
        """Loads an icon, resizes it, and caches it."""
        cache_key = (file_name, size)
        if cache_key in AssetManager._icon_cache:
            return AssetManager._icon_cache[cache_key]

        try:
            path = AssetManager.get_asset_path(file_name)
            img = Image.open(path).resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            AssetManager._icon_cache[cache_key] = photo
            return photo
        except Exception as e:
            logging.error(f"Failed to load icon '{file_name}': {e}")
            # Return a blank image as a fallback
            blank_img = Image.new("RGBA", size, (0, 0, 0, 0))
            return ImageTk.PhotoImage(blank_img)
