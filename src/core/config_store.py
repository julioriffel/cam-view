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
