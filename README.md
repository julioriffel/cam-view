# 🎥 CamView — DVR Viewer

A beautiful, high-performance desktop application for viewing live camera feeds from **Intelbras MHDX** DVRs (and compatible RTSP sources). Built with Python 3.14, PySide6 (Qt6), and OpenCV.

## ✨ Features

- **Multi-channel Grid View**: Dynamically scales to show up to 16 channels simultaneously (e.g., a 2×2 grid for 4 channels).
- **Fullscreen Mode**: Double-click any camera tile to focus on it in fullscreen; double-click again to return to the grid.
- **Auto-Login & Persistence**: Securely saves your login information and automatically connects on startup.
- **Real-time Metrics**: Live FPS counters, connection status indicators, and session uptime tracking.
- **Premium Dark UI**: A modern "glassmorphism" aesthetic with smooth transitions, custom gradient buttons, and floating overlays.
- **Low Latency**: Utilizes multi-threaded `cv2.CAP_FFMPEG` workers to grab and render frames asynchronously without blocking the GUI.

## 🚀 Requirements

- **Python 3.14+**
- **UV** (Lightning-fast Python package installer and resolver)
- Tested primarily on Linux. (Note: Qt6 on Linux requires `libxcb-cursor0`).

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/cam-wiew.git
   cd cam-wiew
   ```

2. **Sync dependencies using UV:**
   ```bash
   uv sync
   ```

3. **Install system dependencies (Linux only):**
   ```bash
   sudo apt-get install -y libxcb-cursor0
   ```

## 🎮 Usage

Launch the application using UV:

```bash
uv run camview
```
*(Or manually via `uv run python main.py`)*

### Connecting to your DVR
1. The app defaults to **Intelbras MHDX 1004** standard settings (IP: `192.168.1.3`, Port: `554`).
2. Enter your DVR **Username** and **Password**.
3. Choose your stream quality (Extra Stream is recommended for lower latency, Main Stream for Full HD).
4. Check **"Remember login info"** to save your credentials and skip the login screen on your next launch.
5. Click **"Connect to DVR"**.

## 🏗️ Architecture

- `main.py` — Application entry point and view controller.
- `src/core/connection.py` — RTSP URL construction and connection probing.
- `src/core/stream_worker.py` — `QThread` workers that grab OpenCV frames, apply FPS caps, and handle auto-reconnection logic.
- `src/core/config_store.py` — Persistent JSON storage for connection credentials (`~/.config/camview/settings.json`).
- `src/styles/theme.py` — Centralized Qt Style Sheets and color palettes.
- `src/views/` — Modular PySide6 window classes for Login and Grid Viewer interfaces.

## 📝 License

MIT License. Feel free to fork and modify!
