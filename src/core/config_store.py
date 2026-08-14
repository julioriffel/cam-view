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
        'snapshot_on_motion': config.snapshot_on_motion,
        'snapshot_interval': config.snapshot_interval,
        'ai_enabled': config.ai_enabled,
        'ai_confidence_threshold': config.ai_confidence_threshold,
        'ai_detect_person': config.ai_detect_person,
        'ai_detect_vehicles': config.ai_detect_vehicles,
        'ai_detect_animals': config.ai_detect_animals,
        'ai_filter_snapshots': config.ai_filter_snapshots,
        'notifications_enabled': config.notifications_enabled,
        'minimize_to_tray': config.minimize_to_tray,
        'notification_cooldown': config.notification_cooldown,
        'channel_states': config.channel_states,
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
            snapshot_on_motion=data.get('snapshot_on_motion', True),
            snapshot_interval=float(data.get('snapshot_interval', 2.0)),
            ai_enabled=data.get('ai_enabled', True),
            ai_confidence_threshold=float(data.get('ai_confidence_threshold', 0.45)),
            ai_detect_person=data.get('ai_detect_person', True),
            ai_detect_vehicles=data.get('ai_detect_vehicles', True),
            ai_detect_animals=data.get('ai_detect_animals', False),
            ai_filter_snapshots=data.get('ai_filter_snapshots', True),
            notifications_enabled=data.get('notifications_enabled', True),
            minimize_to_tray=data.get('minimize_to_tray', True),
            notification_cooldown=float(data.get('notification_cooldown', 5.0)),
            channel_states=data.get('channel_states', {}),
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
