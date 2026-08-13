"""Persistent configuration storage for DVR connection settings.

Saves and loads DVRConfig to a JSON file in the user's config directory.
"""

import json
from pathlib import Path
from src.core.connection import DVRConfig

# Store config in ~/.config/camview/
CONFIG_DIR = Path.home() / '.config' / 'camview'
CONFIG_FILE = CONFIG_DIR / 'settings.json'


def save_config(config: DVRConfig) -> None:
    """Save DVR configuration to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        'host': config.host,
        'port': config.port,
        'username': config.username,
        'password': config.password,
        'channels': config.channels,
        'subtype': config.subtype,
        'save_folder': config.save_folder,
        'tracking_filter_enabled': config.tracking_filter_enabled,
        'tracking_min_area': config.tracking_min_area,
        'tracking_persistence': config.tracking_persistence,
    }
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')


def load_config() -> DVRConfig | None:
    """Load saved DVR configuration from disk. Returns None if no config exists."""
    if not CONFIG_FILE.exists():
        return None
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        return DVRConfig(
            host=data.get('host', '192.168.1.3'),
            port=data.get('port', 554),
            username=data.get('username', 'admin'),
            password=data.get('password', ''),
            channels=data.get('channels', 4),
            subtype=data.get('subtype', 1),
            save_folder=data.get('save_folder', str(Path.home() / 'imagens')),
            tracking_filter_enabled=data.get('tracking_filter_enabled', True),
            tracking_min_area=data.get('tracking_min_area', 1500),
            tracking_persistence=data.get('tracking_persistence', 5),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def has_saved_config() -> bool:
    """Check if a saved configuration exists."""
    return CONFIG_FILE.exists()


def delete_config() -> None:
    """Delete saved configuration."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
