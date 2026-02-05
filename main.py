import os
import vlc
import json
import random
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import pystray
from pystray import MenuItem as item
from dotenv import load_dotenv
from pypresence import Presence
from ui_components import FloatingCinema
import ctypes
import sys

# --- LIBRARY BARU ---
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def resource_path(relative_path):
    """ Dapatkan path absolut ke resource, berfungsi untuk dev dan PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Load environment variables
load_dotenv()

vlc_path = r'C:\Program Files\VideoLAN\VLC' 
if os.path.exists(vlc_path):
    os.add_dll_directory(vlc_path)

# --- HANDLER UNTUK FOLDER WATCHER ---
class PlaylistHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
    def on_any_event(self, event):
        if event.is_directory: return
        if event.src_path.lower().endswith(('.mp4', '.mp3', '.m4a')):
            self.callback()

class MusicController(ctk.CTk):
    SETTINGS_FILE = "settings.json"

    def __init__(self):
        super().__init__()
        myappid = 'rhakim.musicplayer.v2' # ID unik agar icon taskbar muncul
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.title("rhakim Music Player")
        self.geometry("450x850") # Sedikit lebih tinggi untuk EQ menu

        icon_path = resource_path("app.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.tray_icon = None
        
        # --- INIT VLC & EQUALIZER ---
        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
        self.equalizer = vlc.AudioEqualizer()
        self.player.set_equalizer(self.equalizer)
        
        self.all_songs = []
        self.playlist = []
        self.current_idx = 0
        self.cinema_window = None
        self.is_shuffle = False
        self.repeat_mode = "none" 
        self.observer = None # Untuk Watcher

        # Discord RPC
        client_id = os.getenv("DISCORD_CLIENT_ID")
        try:
            if client_id:
                self.rpc = Presence(client_id)
                self.rpc.connect()
            else: self.rpc = None
        except: self.rpc = None

        self.setup_ui()
        self.load_recent_folder()
        
        # --- START SYSTEM TRAY ---
        threading.Thread(target=self.create_tray_icon, daemon=True).start()

    def setup_ui(self):
        # Header & Search
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(self.header, text="📁", width=40, command=self.open_folder_dialog).pack(side="left", padx=5)
        ctk.CTkButton(self.header, text="📺", width=40, fg_color="#2ecc71", command=self.ensure_window).pack(side="left", padx=5)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_playlist)
        ctk.CTkEntry(self.header, placeholder_text="Cari lagu...", textvariable=self.search_var).pack(side="left", fill="x", expand=True)

        # --- UI EQUALIZER PRESET ---
        self.eq_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.eq_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(self.eq_frame, text="EQ Preset:").pack(side="left", padx=5)
        self.eq_menu = ctk.CTkOptionMenu(self.eq_frame, values=["Flat", "Bass Boost", "Rock", "Pop"], 
                                         command=self.apply_eq_preset, width=120, fg_color="#27ae60")
        self.eq_menu.pack(side="left", padx=5)

        # Playlist
        self.playlist_box = tk.Listbox(self, bg="#1d1e1e", fg="#ffffff", selectbackground="#2ecc71", 
                                      selectforeground="#000000", font=("Arial", 11), borderwidth=0)
        self.playlist_box.pack(pady=5, padx=20, fill="both", expand=True)
        self.playlist_box.bind("<Double-Button-1>", self.on_playlist_double_click)

        # Volume & Modes
        self.ctrl_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_panel.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self.ctrl_panel, text="🔈").pack(side="left")
        self.slider_vol = ctk.CTkSlider(self.ctrl_panel, from_=0, to=100, width=120, command=self.set_volume)
        self.slider_vol.set(70)
        self.slider_vol.pack(side="left", padx=5)
        
        self.btn_shuffle = ctk.CTkButton(self.ctrl_panel, text="🔀 OFF", width=60, command=self.toggle_shuffle)
        self.btn_shuffle.pack(side="left", padx=5)
        self.btn_repeat = ctk.CTkButton(self.ctrl_panel, text="🔁 OFF", width=60, command=self.toggle_repeat)
        self.btn_repeat.pack(side="left", padx=5)

        # Progress
        self.lbl_time = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_time.pack()
        self.slider_progress = ctk.CTkSlider(self, from_=0, to=1000, command=self.seek_song)
        self.slider_progress.set(0)
        self.slider_progress.pack(pady=10, padx=30, fill="x")

        # Nav
        self.nav = ctk.CTkFrame(self, fg_color="transparent")
        self.nav.pack(pady=10)
        ctk.CTkButton(self.nav, text="⏮", width=60, command=self.prev_song).grid(row=0, column=0, padx=10)
        self.btn_play = ctk.CTkButton(self.nav, text="▶ PLAY", width=120, command=self.toggle_play)
        self.btn_play.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.nav, text="⏭", width=60, command=self.next_song).grid(row=0, column=2, padx=10)

        self.update_ui_loop()

    # --- LOGIKA EQUALIZER ---
    def apply_eq_preset(self, preset):
        bands = {
            "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "Bass Boost": [8, 6, 4, 0, 0, 0, 0, 0, 0, 0],
            "Rock": [5, 3, -1, -3, -1, 2, 5, 6, 6, 6],
            "Pop": [-2, -1, 2, 5, 4, -1, -2, -2, -2, -2]
        }
        values = bands.get(preset, bands["Flat"])
        for i, val in enumerate(values):
            self.equalizer.set_amp_at_index(float(val), i)
        self.player.set_equalizer(self.equalizer)
        print(f"EQ Preset Applied: {preset}")

    # --- LOGIKA FOLDER WATCHER ---
    def start_folder_watcher(self, path):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        event_handler = PlaylistHandler(callback=lambda: self.after(0, self.process_playlist, path))
        self.observer = Observer()
        self.observer.schedule(event_handler, path, recursive=False)
        self.observer.start()

    def create_tray_icon(self):
        icon_path = resource_path("app.ico")
        img = Image.open(icon_path) if os.path.exists(icon_path) else Image.new('RGB', (64, 64), color=(46, 204, 113))
        menu = pystray.Menu(
            item('Show Player', self.show_from_tray, default=True),
            item('Play/Pause', self.toggle_play),
            item('Next', self.next_song),
            item('Exit', self.quit_app)
        )
        self.tray_icon = pystray.Icon("rhakimMusicPlayer", img, "rhakim Music Player", menu)
        self.tray_icon.run()

    def hide_to_tray(self):
        self.withdraw()
        if self.cinema_window: self.cinema_window.withdraw()

    def show_from_tray(self):
        self.after(0, self.deiconify)
        if self.cinema_window: self.after(0, self.cinema_window.deiconify)

    def quit_app(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        if self.tray_icon: self.tray_icon.stop()
        self.quit()

    def set_volume(self, val): self.player.audio_set_volume(int(val))
    
    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        self.btn_shuffle.configure(text=f"🔀 {'ON' if self.is_shuffle else 'OFF'}", fg_color="#2ecc71" if self.is_shuffle else "#3b3b3b")

    def toggle_repeat(self):
        modes = ["none", "one", "all"]
        self.repeat_mode = modes[(modes.index(self.repeat_mode) + 1) % 3]
        self.btn_repeat.configure(text=f"🔁 {self.repeat_mode.upper()}")

    def ensure_window(self):
        if not self.playlist: return
        path = self.playlist[self.current_idx]
        if self.cinema_window is None or not self.cinema_window.winfo_exists():
            self.cinema_window = FloatingCinema(self, self.player, path)
            self.cinema_window.update()
            self.player.set_hwnd(self.cinema_window.video_frame.winfo_id())
        else:
            self.cinema_window.deiconify()

    def play_current(self):
        if not self.playlist: return
        self.ensure_window()
        path = self.playlist[self.current_idx]
        media = self.instance.media_new(path)
        self.player.set_media(media)
        if self.cinema_window: self.cinema_window.update_song(path)
        self.player.play()
        self.btn_play.configure(text="⏸ PAUSE")
        self.update_listbox()
        if self.rpc: 
            try: self.rpc.update(details=f"🎵 {os.path.basename(path)}", state="Enjoying the MV", large_image="logo")
            except: pass

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.configure(text="▶ PLAY")
        else:
            self.ensure_window()
            self.player.play()
            self.btn_play.configure(text="⏸ PAUSE")

    def next_song(self):
        if not self.playlist: return
        if self.is_shuffle: self.current_idx = random.randint(0, len(self.playlist)-1)
        else: self.current_idx = (self.current_idx + 1) % len(self.playlist)
        self.play_current()

    def prev_song(self):
        if not self.playlist: return
        self.current_idx = (self.current_idx - 1) % len(self.playlist)
        self.play_current()

    def filter_playlist(self, *args):
        q = self.search_var.get().lower()
        self.playlist = [f for f in self.all_songs if q in os.path.basename(f).lower()]
        self.update_listbox()

    def update_listbox(self):
        self.playlist_box.delete(0, tk.END)
        for f in self.playlist: self.playlist_box.insert(tk.END, f"  {os.path.basename(f)}")

    def on_playlist_double_click(self, event):
        sel = self.playlist_box.curselection()
        if sel: self.current_idx = sel[0]; self.play_current()

    def update_ui_loop(self):
        if self.player.is_playing():
            pos = self.player.get_position() * 1000
            if pos >= 0: self.slider_progress.set(pos)
        if self.player.get_state() == vlc.State.Ended:
            if self.repeat_mode == "one": self.play_current()
            else: self.next_song()
        self.after(500, self.update_ui_loop)

    def open_folder_dialog(self):
        f = filedialog.askdirectory()
        if f: 
            self.save_settings(f)
            self.process_playlist(f)
            self.start_folder_watcher(f)

    def process_playlist(self, path):
        self.all_songs = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.mp4', '.mp3', '.m4a'))]
        self.filter_playlist()

    def load_recent_folder(self):
        if os.path.exists(self.SETTINGS_FILE):
            with open(self.SETTINGS_FILE, "r") as f:
                path = json.load(f).get("last_folder")
                if path and os.path.exists(path): 
                    self.process_playlist(path)
                    self.start_folder_watcher(path)

    def save_settings(self, path):
        with open(self.SETTINGS_FILE, "w") as f: json.dump({"last_folder": path}, f)

    def seek_song(self, val): self.player.set_position(float(val)/1000)

if __name__ == "__main__":
    MusicController().mainloop()