# 🚀 CamView — Future Resources & Roadmap

This document outlines proposed architecture, features, and capabilities planned for future releases of CamView.

---

## 📑 Roadmap Overview

```
                   ┌─────────────────────────────────────────┐
                   │          🧠 CamView Core Engine         │
                   └────────────────────┬────────────────────┘
                                        │
     ┌──────────────────┬───────────────┴───────────────┬──────────────────┐
     ▼                  ▼                               ▼                  ▼
📲 Remote Alerts   🎥 Clip Recorder               📐 ROI Zones       🌐 Web / Mobile
(Telegram/Discord) (MP4 Ring-Buffer)             (Polygon Masks)     (Local WebRTC)
```

---

## 🌟 Proposed Features & Resources

### 1. 📲 Remote Messenger Alerts (Telegram & Webhooks)
* **Goal**: Receive instant surveillance alerts on your mobile phone wherever you are.
* **Capabilities**:
  - **Telegram Bot Integration**: Automatically sends photo snapshots and object summaries (e.g., *"🚨 Person detected on Front Gate — Channel 1"*) directly to your Telegram chat.
  - **Interactive Telegram Actions**: Inline keyboard buttons:
    - `📸 Live Snapshot`: Queries DVR and sends a fresh real-time photo.
    - `🔕 Silence 30m`: Temporarily pauses alerts during garden maintenance or deliveries.
    - `📹 Request 10s Clip`: Sends a short video clip of the detection event.
  - **Home Assistant & MQTT**: Publish MQTT event topics (`camview/ch1/person`) to trigger smart lights, sirens, or door locks.

---

### 2. 🎥 Pre- & Post-Event Video Clip Recording (MP4 Ring Buffer)
* **Goal**: Record short, contextual `.mp4` video clips around detection events instead of only static images.
* **Architecture**:
  - Maintain a rolling **5-second circular in-memory frame buffer** in `StreamWorker`.
  - When a verified AI target (Person, Vehicle, Animal) is recognized:
    - Keep the 5 seconds prior to the event (pre-roll).
    - Record the following 10–15 seconds (post-roll).
    - Encode and write directly to an H.264 `.mp4` file in your storage folder.
  - **Benefit**: Never miss how an intruder or vehicle entered the camera's field of view.

---

### 3. 📐 Custom Detection Zones (ROI & Polygonal Exclusion Masks)
* **Goal**: Eliminate false alarms from public areas, neighbor yards, or wind-blown vegetation.
* **Capabilities**:
  - **Interactive ROI Editor**: Click and drag vertices directly over the camera feed tile to draw custom trigger polygons (e.g., Driveway, Front Door).
  - **Exclusion Zones (Masking)**: Red-out busy public sidewalks or moving tree branches so motion within those areas is ignored by the detector.
  - **Per-Zone Alert Rules**: Trigger high-priority alerts only when people cross into specific restricted zones.

---

### 4. 🕒 Interactive Visual Timeline & Playback Scrubber
* **Goal**: Rapidly browse historical events across all channels on an interactive timeline.
* **Capabilities**:
  - Horizontal timeline bar color-coded by detection type:
    - 🟦 Solid Blue: Continuous stream history
    - 🟨 Yellow: Generic motion detected
    - 🟦 Vibrant Cyan: Person recognized
    - 🟧 Amber / Orange: Vehicle recognized
    - 🟩 Green: Animal recognized
  - Hover over timeline ticks to view thumbnail previews.
  - Click any timestamp to play back the recorded video clip.

---

### 5. 🔍 Local Face & License Plate (ANPR/LPR) Recognition
* **Goal**: Whitelist known household members and vehicles to distinguish authorized arrivals from strangers.
* **Capabilities**:
  - **Face Recognition**: Lightweight embedded ArcFace / MobileFaceNet model to tag recognized family members.
  - **License Plate OCR**: Lightweight PaddleOCR / LPRNet reader to identify vehicle plate numbers arriving in the driveway.
  - **Custom Notification Filters**: Silence alerts for known family members and trigger distinct chime alerts for unfamiliar guests.

---

### 6. 🎙️ Two-Way Audio Intercom & Deterrent Siren
* **Goal**: Listen in on camera microphones and transmit voice audio back to camera speakers.
* **Capabilities**:
  - **Audio Stream Ingestion**: Decode RTSP G.711 / AAC audio streams alongside video.
  - **Push-to-Talk (PTT)**: Hold a microphone button in the toolbar to transmit live voice audio over RTSP backchannel or DVR audio port.
  - **One-Click Siren**: Trigger an alarm chime or synthesized voice warning ("You are on security camera") directly through the DVR/camera output.

---

### 7. 🌐 Local Web Dashboard & Phone Streaming (WebRTC / HLS)
* **Goal**: View your camera feeds from any smartphone, tablet, or browser on your local Wi-Fi network without installing software.
* **Architecture**:
  - Embedded lightweight asynchronous web server (`FastAPI` / `aiohttp`).
  - Low-latency **WebRTC / go2rtc** stream relay for ultra-smooth 60fps mobile browser playback.
  - Mobile-responsive web UI for checking live cameras and browsing the SQLite event history on phones.

---

### 8. ⚡ Hardware Acceleration & Embedded Optimization
* **Goal**: Maximize energy efficiency and support low-power microcomputers (e.g. Raspberry Pi 5, Intel NUC).
* **Capabilities**:
  - **Hardware Video Decoding**: Enable NVIDIA NVDEC (`cuvid`), Intel VA-API, and Linux V4L2/DRM hardware acceleration in OpenCV FFMPEG.
  - **OpenVINO / TensorRT Inference**: Optional GPU/NPU acceleration backends for near-instant AI inference with 0% CPU footprint.

---

## 🛠️ Prioritization Matrix

| Feature | Complexity | Impact | Resource Requirements |
| :--- | :---: | :---: | :--- |
| **📲 Telegram Bot Alerts** | Medium | ⭐⭐⭐⭐⭐ | Python `aiohttp` / `python-telegram-bot` |
| **🎥 MP4 Clip Ring-Buffer** | Medium | ⭐⭐⭐⭐⭐ | OpenCV `VideoWriter` / `ffmpeg` |
| **📐 Custom ROI Polygons** | Low-Medium | ⭐⭐⭐⭐ | PySide6 Canvas Overlay |
| **🕒 Visual Timeline Scrubber** | Medium-High | ⭐⭐⭐⭐ | SQLite Time-series queries |
| **🌐 Local WebRTC Server** | High | ⭐⭐⭐⭐ | `aiortc` / `fastapi` |
| **🔍 License Plate (LPR)** | High | ⭐⭐⭐ | Local OCR Engine |

---

*Contributions and feedback on these feature proposals are warmly welcomed!*
