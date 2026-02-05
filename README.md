# 🎶 rhakim Music Player

A professional-grade, feature-rich music and MV player built with Python. Designed specifically for power users and developers who want a seamless, high-quality media experience while working.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![VLC](https://img.shields.io/badge/VLC-Engine-orange?style=for-the-badge&logo=vlc-mediaplayer)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## ✨ Key Features

- **📺 Floating Cinema Mode**: A borderless, always-on-top video window optimized for Music Videos.
- **🎤 Karaoke-Style Lyrics**: Real-time synced lyrics with a 3-line display (Previous, Current, Next). Includes manual offset adjustment (+/-) for perfect timing.
- **📥 Built-in MV Downloader**: Integrated YouTube downloader using `yt-dlp`. Optimized for 360p/480p to save disk space and RAM.
- **🎛 Audio Equalizer**: 10-band hardware equalizer with custom presets (Bass Boost, Rock, Pop, and Flat).
- **🔄 Smart Folder Watcher**: Real-time file system monitoring. Playlist updates automatically when new media is added to the folder.
- **🎮 Discord Rich Presence**: Share your current vibe on Discord with integrated RPC.
- **📥 System Tray Integration**: Minimizes to the system tray with a functional context menu to keep your taskbar clean.



## 🚀 Installation

1. **Prerequisites**:
   - Install [VLC Media Player](https://www.videolan.org/vlc/) (64-bit version is required).
   - Python 3.10 or higher.

2. **Clone Repository**:
   ```bash
   git clone [https://github.com/yourusername/rhakimMusicPlayer.git](https://github.com/yourusername/rhakimMusicPlayer.git)
   cd rhakimMusicPlayer

3. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt


4. **Environment Setup**:
Create a `.env` file in the root directory:
    ```env
    DISCORD_CLIENT_ID=your_discord_app_id_here

## ⌨️ Control Guide

| Action | Control / UI Element |
| --- | --- |
| **Open Folder** | 📁 Button |
| **Toggle Cinema** | 📺 Button |
| **Download MV** | 📥 Button |
| **Adjust Lyrics Offset** | `+` / `-` in Cinema Drag Bar |
| **Search Playlist** | Search Entry (Top) |
| **Tray Menu** | Right-Click Tray Icon |

## 🛠 Tech Stack

* **GUI Framework**: CustomTkinter (Modern Dark UI)
* **Multimedia Engine**: LibVLC via `python-vlc`
* **Lyrics Engine**: `syncedlyrics` (LRC format)
* **Downloader**: `yt-dlp` (YouTube Engine)
* **File Monitoring**: `watchdog` (Event-driven)

---

Developed with ❤️ by **[rhakim](https://github.com/Ranggahakim)**
