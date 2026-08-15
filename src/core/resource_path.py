"""
Resource path resolver for CamView.

Handles path resolution for assets, icons, and data files across development
mode and PyInstaller frozen executable modes (both --onefile and --onedir).
"""

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Return base directory whether running in frozen binary or development mode."""
    if getattr(sys, "frozen", False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS for --onefile
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        # For --onedir mode, base directory is adjacent to executable
        return Path(sys.executable).resolve().parent
    # In development mode, base directory is project root
    return Path(__file__).resolve().parent.parent.parent


def get_asset_path(filename: str = "icon.jpg") -> Path:
    """Get absolute path to an asset file.

    Searches across standard bundling locations:
    1. <base_dir>/src/assets/<filename>
    2. <base_dir>/assets/<filename>
    3. <base_dir>/<filename>
    4. Fallback to development source tree path

    Args:
        filename: Name of the asset file (e.g. 'icon.jpg')

    Returns:
        Path to the asset file (may be checked with .exists()).
    """
    base = get_base_dir()

    candidates = [
        base / "src" / "assets" / filename,
        base / "assets" / filename,
        base / filename,
        Path(__file__).resolve().parent.parent / "assets" / filename,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Return primary canonical path even if not found yet
    return candidates[0]


def get_resource_path(relative_path: str) -> Path:
    """Resolve a relative resource path to an absolute path.

    Args:
        relative_path: Relative path such as 'src/assets/icon.jpg' or 'assets/icon.jpg'.

    Returns:
        Resolved absolute Path.
    """
    base = get_base_dir()
    candidate = base / relative_path
    if candidate.exists():
        return candidate

    # Fallback to checking from project root
    dev_root = Path(__file__).resolve().parent.parent.parent
    dev_candidate = dev_root / relative_path
    if dev_candidate.exists():
        return dev_candidate

    return candidate
