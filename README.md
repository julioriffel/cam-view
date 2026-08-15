# 🍌 🎥 CamView — DVR Viewer

A beautiful, high-performance desktop application for viewing live camera feeds from **Intelbras MHDX** DVRs (and compatible RTSP sources). Built with Python 3.14, PySide6 (Qt6), OpenCV, and local ONNX AI.

Protected by our friendly neighborhood **Nano Banana** security guard! 🍌🛡️

---

## ✨ Features

- **Multi-channel Grid View**: Dynamically scales to show up to 16 channels simultaneously (e.g., a 2×2 grid for 4 channels).
- **Fullscreen Mode**: Double-click any camera tile to focus on it in fullscreen; double-click again to return to the grid.
- **Auto-Login & State Persistence**: Securely saves login credentials, per-channel quality states (HD/SD/OFF), and active tracking toggles across app restarts.
- **Premium Dark UI**: Modern frosted-glass aesthetic with smooth transitions, custom gradient buttons, and floating overlays.
- **Low Latency Multi-threading**: Utilizes asynchronous `cv2.CAP_FFMPEG` `QThread` workers with zero GUI blocking.

---

### 🎛️ Per-Channel Control
- Dynamically switch individual camera feeds between **HD** (Main Stream), **SD** (Extra Stream), or **OFF** (to conserve CPU and network bandwidth) without interrupting other active streams.

---

### 🧠 Smart Vision & AI Object Recognition
- **100% Local CPU Inference**: Powered by OpenCV's native DNN engine and lightweight YOLO ONNX model (~4MB) with zero heavy external ML dependencies.
- **Smart Target Categorization**:
  - 🚶 **People**: Highlighted in vibrant Cyan (`Person 94%`)
  - 🚗 **Vehicles**: Highlighted in Amber/Orange (`Car 88%`, `Motorcycle 95%`, `Truck`, `Bus`, `Bicycle`)
  - 🐾 **Animals**: Highlighted in Green (`Dog 89%`, `Cat 85%`, `Bird`)
- **Zero False-Alarm Snapshots**: Option to **only save snapshots when recognized objects are detected**, ignoring shadows, trees, or rain entirely.
- **Hybrid Motion-Gating**: Only runs AI inference when motion occurs, keeping CPU usage ultra-low across all channels.

---

### 📊 AI Object Event Database & Analytics Screen (`Ctrl+E`)
- **Local SQLite Storage (`events.db`)**: Records all AI detections (People, Vehicles, Animals) with timestamp, channel, confidence score, and associated snapshot file.
- **Smart 10-Second Rate Limiting**: Debounces detection logging per `(channel, category)` pair to record clean, meaningful event timelines rather than repetitive frame spam.
- **Visual Analytics Dashboard**:
  - **KPI Metric Cards**: Total Detections, People count, Vehicle count, Animal count.
  - **Channel Frequency Matrix**: Comparative grid displaying detection counts across every camera channel.
  - **Interactive Search & Log Viewer**: Filter by channel, category, and date range (`Today`, `Last 24h`, `Last 7d`, `All Time`).
  - **Click-to-Open Snapshot**: Double-clicking any event row opens the captured `.jpg` image in your system viewer.
- **📤 Multi-Row Export**: Export filtered or selected event logs as structured **JSON (`.json`)** or spreadsheet **CSV (`.csv`)**, with optional automatic bundling of all associated snapshot image files.

---

### 🔔 System Tray & Desktop Notifications
- **Background Surveillance (Default True)**: Closing the window (`[X]`) docks CamView directly to the system tray so surveillance runs continuously in the background without taskbar clutter.
- **Native Desktop Alerts**: Receives instant notifications when movement or AI targets (Person, Vehicle, Animal) appear.
- **Click-to-Open Referrer Snapshot**: Clicking a notification opens the exact `.jpg` snapshot in your default image viewer and brings CamView to the front.
- **Nano Banana Tray Menu**: Right-click the tray icon for quick access to Restore, Events & Stats, Settings, and Quit.

---

### 🌐 Live Bandwidth & Network Health Monitor
- **Real-time Throughput**: Continuous aggregate bitrate counter in the status bar (e.g. `450.0 KB/s` or `2.35 MB/s`).
- **Connection Latency**: Live frame acquisition and decode delay indicator in milliseconds (`~24 ms`).
- **Packet Loss & Jitter Tracking**: Dynamic health status badge (`🟢 0 Drops (Stable)` / `🟡 Recovered` / `🔴 Jitter`).

---

### 🏃 Advanced Motion Tracking & Snapshots
- Smart MOG2 background subtraction draws green bounding boxes around moving objects and saves snapshots to disk.
- **Configurable Snapshot Trigger & Interval**: Toggle automatic snapshot capture on/off and set cooldown intervals (from 0.5s to 60.0s).
- **Insect-Proof Algorithm**: Built-in logic ignores false positives from flying bugs and rain in night vision by utilizing:
  1. Morphological Noise Filtering (Erases thin streaks)
  2. Dynamic Size Thresholding
  3. Temporal Debouncing (Requires motion persistence across multiple frames)

---

### ⚙️ Tabbed Settings Dialog
- Compact, organized multi-tab configuration interface:
  - **🏃 Motion**: Noise filtering, minimum area, persistence, snapshot cooldown.
  - **🧠 Smart Vision**: AI enable toggle, confidence slider, target categories, snapshot filter.
  - **🔔 Alerts & Tray**: Desktop notifications toggle, minimize-to-tray toggle, notification cooldown.
  - **💾 Storage**: Snapshot directory selector.
- Dynamically updates live running streams without requiring reconnection!

---

## 🚀 Requirements

- **Python 3.14+**
- **UV** (Lightning-fast Python package installer and resolver)
- Tested primarily on Linux. (Note: Qt6 on Linux requires `libxcb-cursor0`).

---

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

---

## 🎮 Usage & Makefile Shortcuts

You can run and build the project using either `make` shortcuts or `uv` directly:

```bash
# Display all available shortcuts
make help

# Run in development mode
make run
# or: uv run python main.py
```

### Keyboard Shortcuts
- **`Ctrl+1`**, **`Ctrl+2`**... **`Ctrl+9`**: Toggle motion tracking on/off for specific camera channels.
- **`Ctrl+E`**: Open the AI Object Detection History & Statistics Dashboard.

---

## 📦 Building Standalone Executables

CamView includes build tools powered by **PyInstaller** to produce self-contained standalone executable binaries for **Linux**, **Windows**, and **macOS**. The bundled executables include all UI assets, Qt dynamic plugins, OpenCV engines, and AI models—meaning end users **do not need Python installed**.

### ⚡ Quick Build (Current OS)

```bash
# Install dependencies including build tools
make install

# Compile a standalone single-file binary for your current OS
make build
```
The compiled binary will be placed in the `dist/` directory.

---

### 🐧 Linux Build

Run on any Linux distribution (Ubuntu, Debian, Fedora, Arch, etc.):

```bash
make build-linux
# Output: dist/CamView-Linux-x86_64 (or dist/CamView)
```

To run the binary directly:
```bash
./dist/CamView
```

> **Note for Linux**: If running on minimal desktop environments, ensure `libxcb-cursor0` is installed (`sudo apt-get install -y libxcb-cursor0`).

---

### 🪟 Windows Build (`.exe`)

#### Option A — Native Build (on Windows)
In PowerShell or CMD with [uv](https://docs.astral.sh/uv/) installed:
```powershell
uv sync --all-extras
uv run python build.py --onefile
# Output: dist\CamView.exe
```

#### Option B — Automated GitHub Actions CI/CD (Recommended for cross-compiling)
CamView includes a GitHub Actions workflow (`.github/workflows/build.yml`). Simply push your code or trigger a workflow dispatch on GitHub to automatically compile native `.exe` binaries on Microsoft Windows runners and download the build artifact.

---

### 🍏 macOS Build (`.app` Bundle)

#### Option A — Native Build (on macOS)
```bash
make install
make build-macos
# Output: dist/CamView.app
```

Launch with:
```bash
open dist/CamView.app
```

#### Option B — Automated GitHub Actions CI/CD
GitHub Actions will automatically run the build matrix on macOS runners and package the resulting `.app` bundle into downloadable artifacts.

---

### 🛠️ Advanced Build Options

The `build.py` script offers customizable build flags:

```bash
# Single-file binary (default)
uv run python build.py --onefile

# Directory distribution (faster launch, libraries alongside binary)
uv run python build.py --onedir

# Debug build (leaves console terminal open to inspect RTSP/OpenCV logs)
uv run python build.py --onefile --debug

# Custom executable name
uv run python build.py --onefile --name "MyCamView"
```

---

### 📋 Makefile Cheatsheet

| Target | Description |
|---|---|
| `make help` | Display formatted list of all available commands |
| `make install` | Install all runtime and build dependencies via UV |
| `make run` | Launch CamView in development mode from source |
| `make build` | Compile single-file standalone executable for the current OS |
| `make build-dir` | Compile directory distribution for current OS |
| `make build-debug` | Compile executable with terminal console attached for debugging |
| `make build-linux` | Compile Linux standalone binary (`dist/CamView`) |
| `make build-windows` | Compile Windows executable (`dist/CamView.exe`) |
| `make build-macos` | Compile macOS `.app` bundle |
| `make check` | Run Python syntax and compilation check across all files |
| `make clean` | Remove `build/`, `dist/`, and Python cache artifacts |

---

## 🏗️ Architecture

- `main.py` — Application entry point and view controller.
- `src/core/connection.py` — RTSP URL construction and config data schemas.
- `src/core/stream_worker.py` — OpenCV `QThread` workers handling grabbing, rendering, and computer vision tracking.
- `src/core/ai_detector.py` — Lightweight CPU-based YOLOv5n ONNX inference engine via `cv2.dnn`.
- `src/core/event_db.py` — Thread-safe SQLite database manager for detection events and statistical aggregations.
- `src/core/config_store.py` — Persistent JSON settings storage (`~/.config/camview/settings.json`).
- `src/views/viewer_window.py` — Main multi-channel surveillance grid, status bar health monitor, and tray manager.
- `src/views/events_window.py` — Interactive search, KPI summary cards, channel matrix, and JSON/CSV exporter.
- `src/views/settings_dialog.py` — Tabbed settings dialog for motion, AI, alerts, and storage.
- `src/views/login_window.py` — DVR connection and auto-login screen.

---

## 💡 Future Roadmap & Feature Ideas
Check out [FUTURE_RESOURCES.md](file:///home/julio/projects/cam-wiew/FUTURE_RESOURCES.md) for proposed future features including Telegram alerts, short MP4 ring-buffer clip recording, ROI detection zones, and WebRTC streaming.

---

## 📝 License

MIT License. Feel free to fork and modify!
