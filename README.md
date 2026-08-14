# 🍌 🎥 CamView — DVR Viewer

A beautiful, high-performance desktop application for viewing live camera feeds from **Intelbras MHDX** DVRs (and compatible RTSP sources). Built with Python 3.14, PySide6 (Qt6), and OpenCV.

Protected by our friendly neighborhood **Nano Banana** security guard! 🍌🛡️

## ✨ Features

- **Multi-channel Grid View**: Dynamically scales to show up to 16 channels simultaneously (e.g., a 2×2 grid for 4 channels).
- **Fullscreen Mode**: Double-click any camera tile to focus on it in fullscreen; double-click again to return to the grid.
- **Auto-Login & Persistence**: Securely saves your login information and automatically connects on startup.
- **Premium Dark UI**: A modern "glassmorphism" aesthetic with smooth transitions, custom gradient buttons, and floating overlays.
- **Low Latency**: Utilizes multi-threaded `cv2.CAP_FFMPEG` workers to grab and render frames asynchronously without blocking the GUI.

### 🎛️ Per-Channel Control
- Dynamically switch individual camera feeds between **HD** (Main Stream), **SD** (Extra Stream), or **OFF** (to save system resources) without interrupting other streams.

### 🏃 Advanced Motion Tracking & Snapshots
- Smart MOG2 background subtraction draws green bounding boxes around moving objects and saves snapshots to your disk.
- **Configurable Snapshot Trigger & Interval**: Toggle automatic snapshot capture on/off and set the exact cooldown interval (from 0.5 to 60 seconds) between snapshots during continuous movement.
- **Insect-Proof Algorithm**: Built-in logic ignores false positives from flying bugs and rain in night vision by utilizing:
  1. Morphological Noise Filtering (Erases thin streaks)
  2. Dynamic Size Thresholding
  3. Temporal Debouncing (Requires motion persistence across multiple frames)

### ⚙️ Real-time Settings Adjustments
- Tweak the motion tracking and snapshot parameters on the fly via the **Settings Dialog**.
- Adjust minimum object size, persistence frames, snapshot interval, and save folder dynamically. The changes apply to all live feeds instantly without reconnecting!
- Your settings and snapshot folder preferences are saved persistently.

## 🚀 Requirements

- **Python 3.14+**
- **UV** (Lightning-fast Python package installer and resolver)
- Tested primarily on Linux. (Note: Qt6 on Linux requires `libxcb-cursor0`).

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/julioriffel/cam-view.git
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
uv run python main.py
```

### Keyboard Shortcuts
- **`Ctrl+1`**, **`Ctrl+2`**...: Toggle motion tracking on/off for specific channels.

## 🏗️ Architecture

- `main.py` — Application entry point and view controller.
- `src/core/connection.py` — RTSP URL construction and config data schemas.
- `src/core/stream_worker.py` — OpenCV `QThread` workers handling grabbing, rendering, and computer vision tracking.
- `src/core/config_store.py` — Persistent JSON storage (`~/.config/camview/settings.json`).
- `src/views/` — Modular PySide6 window classes (`ViewerWindow`, `LoginWindow`, `TrackingSettingsDialog`).

## 📝 License

MIT License. Feel free to fork and modify!
