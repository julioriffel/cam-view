"""
RTSP connection manager for Intelbras MHDX DVRs.

Provides helpers to build properly-encoded RTSP URLs and to verify
connectivity by grabbing a single frame from a given channel.
"""

import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass
class DVRConfig:
    """Configuration for a single DVR connection."""

    host: str = '192.168.1.3'
    port: int = 554
    username: str = 'admin'
    password: str = ''
    channels: int = 4
    subtype: int = 1  # 0=main, 1=extra
    save_folder: str = str(Path.home() / 'imagens')
    tracking_filter_enabled: bool = True
    tracking_min_area: int = 1500
    tracking_persistence: int = 5
    snapshot_on_motion: bool = True
    snapshot_interval: float = 2.0


def build_rtsp_url(config: DVRConfig, channel: int, subtype_override: int = None) -> str:
    """Build RTSP URL for Intelbras MHDX DVR.

    Format: rtsp://user:password@host:port/cam/realmonitor?channel=N&subtype=S
    Special characters in password are URL-encoded.
    """
    subtype = subtype_override if subtype_override is not None else config.subtype
    encoded_password = urllib.parse.quote(config.password, safe='')
    return (
        f"rtsp://{config.username}:{encoded_password}"
        f"@{config.host}:{config.port}"
        f"/cam/realmonitor?channel={channel}&subtype={subtype}"
    )


def test_connection(
    config: DVRConfig,
    channel: int = 1,
    timeout_ms: int = 5000,
) -> tuple[bool, str]:
    """Test RTSP connection by attempting to grab a single frame.

    Returns (success: bool, message: str).
    """
    url = build_rtsp_url(config, channel)
    try:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)

        if not cap.isOpened():
            return False, 'Failed to open RTSP stream. Check IP, port, and credentials.'

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return False, 'Connected but failed to read frame. Check channel configuration.'

        return True, f'Connection successful! Frame size: {frame.shape[1]}x{frame.shape[0]}'
    except Exception as e:
        return False, f'Connection error: {str(e)}'
