import os, sys, json, random, threading, ctypes, gc
import vlc
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import pystray
from pystray import MenuItem as item
from dotenv import load_dotenv
from pypresence import Presence
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Internal Modules
from ui_components import FloatingCinema
from downloader import DownloadWindow

load_dotenv()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

vlc_path = r'C:\Program Files\VideoLAN\VLC' 
if os.path.exists(vlc_path):
    os.add_dll_directory(vlc_path)

class PlaylistHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
    def on_any_event(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.mp4', '.mp3', '.m4a')):
            self.callback()

class MusicController(ctk.CTk):
    SETTINGS_FILE = "settings.json"

    def __init__(self):
        super().__init__()
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('rhakim.musicplayer.v2')

        self.title("rhakim Music Player")
        self.geometry("450x850")
        
        icon_path = resource_path("app.ico")
        if os.path.exists(icon_path): self.iconbitmap(icon_path)
        
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        
        # VLC Engine
        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
        self.equalizer = vlc.AudioEqualizer()
        self.player.set_equalizer(self.equalizer)
        
        # States
        self.all_songs, self.playlist = [], []
        self.current_idx = 0
        self.cinema_window = None
        self.is_shuffle = False
        self.repeat_mode = "none" # none, one, all
        self.observer = None
        self.tray_icon = None

        self.setup_rpc()
        self.setup_ui()
        self.load_recent_folder()
        threading.Thread(target=self.create_tray_icon, daemon=True).start()

    def setup_rpc(self):
        client_id = os.getenv("DISCORD_CLIENT_ID")
        try:
            if client_id:
                self.rpc = Presence(client_id); self.rpc.connect()
            else: self.rpc = None
        except: self.rpc = None

    def setup_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(self.header, text="📁", width=40, command=self.open_folder_dialog).pack(side="left", padx=5)
        ctk.CTkButton(self.header, text="📺", width=40, fg_color="#2ecc71", command=self.ensure_window).pack(side="left", padx=5)
        ctk.CTkButton(self.header, text="📥", width=40, fg_color="#e74c3c", command=self.open_download_window).pack(side="left", padx=5)
        
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_playlist)
        ctk.CTkEntry(self.header, placeholder_text="Cari lagu...", textvariable=self.search_var).pack(side="left", fill="x", expand=True)

        # EQ & Modes
        self.top_ctrl = ctk.CTkFrame(self, fg_color="transparent")
        self.top_ctrl.pack(pady=5, padx=20, fill="x")
        
        self.eq_menu = ctk.CTkOptionMenu(self.top_ctrl, values=["Flat", "Bass Boost", "Rock", "Pop"], 
                                         command=self.apply_eq_preset, width=100, fg_color="#27ae60")
        self.eq_menu.pack(side="left", padx=5)

        self.btn_shuffle = ctk.CTkButton(self.top_ctrl, text="🔀 OFF", width=70, fg_color="#333", command=self.toggle_shuffle)
        self.btn_shuffle.pack(side="left", padx=5)
        
        self.btn_repeat = ctk.CTkButton(self.top_ctrl, text="🔁 OFF", width=70, fg_color="#333", command=self.toggle_repeat)
        self.btn_repeat.pack(side="left", padx=5)

        # Listbox
        self.playlist_box = tk.Listbox(self, bg="#1d1e1e", fg="#ffffff", selectbackground="#2ecc71", 
                                      selectforeground="#000000", font=("Arial", 11), borderwidth=0)
        self.playlist_box.pack(pady=5, padx=20, fill="both", expand=True)
        self.playlist_box.bind("<Double-Button-1>", self.on_playlist_double_click)

        # Volume
        self.vol_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.vol_frame.pack(fill="x", padx=30)
        ctk.CTkLabel(self.vol_frame, text="🔈").pack(side="left")
        self.slider_vol = ctk.CTkSlider(self.vol_frame, from_=0, to=100, command=self.set_volume)
        self.slider_vol.set(70); self.slider_vol.pack(side="left", fill="x", expand=True, padx=5)

        # Progress
        self.slider_progress = ctk.CTkSlider(self, from_=0, to=1000, command=self.seek_song)
        self.slider_progress.pack(pady=10, padx=30, fill="x")

        # Navigation Buttons
        self.nav = ctk.CTkFrame(self, fg_color="transparent")
        self.nav.pack(pady=10)
        ctk.CTkButton(self.nav, text="⏮", width=60, font=("Arial", 20), command=self.prev_song).grid(row=0, column=0, padx=10)
        self.btn_play = ctk.CTkButton(self.nav, text="▶ PLAY", width=120, font=("Arial", 14, "bold"), command=self.toggle_play)
        self.btn_play.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.nav, text="⏭", width=60, font=("Arial", 20), command=self.next_song).grid(row=0, column=2, padx=10)

        self.update_ui_loop()

    def apply_eq_preset(self, preset):
        ps = {"Flat": [0]*10, "Bass Boost": [8,6,4,0,0,0,0,0,0,0], "Rock": [5,3,-1,-3,-1,2,5,6,6,6], "Pop": [-2,-1,2,5,4,-1,-2,-2,-2,-2]}
        for i, v in enumerate(ps.get(preset, ps["Flat"])): self.equalizer.set_amp_at_index(float(v), i)
        self.player.set_equalizer(self.equalizer)

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        self.btn_shuffle.configure(text=f"🔀 {'ON' if self.is_shuffle else 'OFF'}", fg_color="#2ecc71" if self.is_shuffle else "#333")

    def toggle_repeat(self):
        modes = ["none", "one", "all"]
        self.repeat_mode = modes[(modes.index(self.repeat_mode)+1)%3]
        color = "#2ecc71" if self.repeat_mode != "none" else "#333"
        self.btn_repeat.configure(text=f"🔁 {self.repeat_mode.upper()}", fg_color=color)

    def play_current(self):
        if not self.playlist: return
        self.ensure_window()
        path = self.playlist[self.current_idx]
        self.player.set_media(self.instance.media_new(path))
        if self.cinema_window: self.cinema_window.update_song(path)
        self.player.play(); self.btn_play.configure(text="⏸ PAUSE")
        if self.rpc: self.rpc.update(details=f"🎵 {os.path.basename(path)}", state="Coding Mode", large_image="logo")

    def next_song(self):
        if not self.playlist: return
        self.current_idx = random.randint(0, len(self.playlist)-1) if self.is_shuffle else (self.current_idx + 1) % len(self.playlist)
        self.play_current()

    def prev_song(self):
        if not self.playlist: return
        self.current_idx = (self.current_idx - 1) % len(self.playlist); self.play_current()

    def toggle_play(self):
        if self.player.is_playing(): self.player.pause(); self.btn_play.configure(text="▶ PLAY")
        else: self.ensure_window(); self.player.play(); self.btn_play.configure(text="⏸ PAUSE")

    def update_ui_loop(self):
        if self.player.is_playing():
            pos = self.player.get_position() * 1000
            if pos >= 0: self.slider_progress.set(pos)
        if self.player.get_state() == vlc.State.Ended:
            if self.repeat_mode == "one": self.play_current()
            else: self.next_song()
        self.after(500, self.update_ui_loop)

    def start_folder_watcher(self, path):
        if self.observer: self.observer.stop()
        self.observer = Observer()
        self.observer.schedule(PlaylistHandler(lambda: self.after(0, self.process_playlist, path)), path)
        self.observer.start()

    def process_playlist(self, path):
        self.all_songs = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.mp4', '.mp3', '.m4a'))]
        self.filter_playlist()

    def filter_playlist(self, *args):
        q = self.search_var.get().lower()
        self.playlist = [f for f in self.all_songs if q in os.path.basename(f).lower()]
        self.playlist_box.delete(0, tk.END)
        for f in self.playlist: self.playlist_box.insert(tk.END, f"  {os.path.basename(f)}")

    def load_recent_folder(self):
        if os.path.exists(self.SETTINGS_FILE):
            with open(self.SETTINGS_FILE, "r") as f:
                p = json.load(f).get("last_folder")
                if p and os.path.exists(p): self.process_playlist(p); self.start_folder_watcher(p)

    def open_folder_dialog(self):
        f = filedialog.askdirectory()
        if f: 
            with open(self.SETTINGS_FILE, "w") as sf: json.dump({"last_folder": f}, sf)
            self.process_playlist(f); self.start_folder_watcher(f)

    def open_download_window(self):
        p = ""
        if os.path.exists(self.SETTINGS_FILE):
            with open(self.SETTINGS_FILE, "r") as f: p = json.load(f).get("last_folder", "")
        if not hasattr(self, 'dl_win') or not self.dl_win.winfo_exists():
            self.dl_win = DownloadWindow(self, lambda: self.process_playlist(p))
        else: self.dl_win.focus()

    def ensure_window(self):
        if not self.playlist: return
        if not self.cinema_window or not self.cinema_window.winfo_exists():
            self.cinema_window = FloatingCinema(self, self.player, self.playlist[self.current_idx])
            self.player.set_hwnd(self.cinema_window.video_frame.winfo_id())
        else: self.cinema_window.deiconify()

    def create_tray_icon(self):
        path = resource_path("app.ico")
        img = Image.open(path) if os.path.exists(path) else Image.new('RGB',(64,64),(46,204,113))
        menu = pystray.Menu(item('Show', self.show_from_tray, default=True), item('Exit', self.quit_app))
        self.tray_icon = pystray.Icon("rhakimPlayer", img, "rhakim Music Player", menu); self.tray_icon.run()

    def quit_app(self):
        if self.observer: self.observer.stop()
        if self.tray_icon: self.tray_icon.stop()
        self.destroy(); sys.exit()

    def hide_to_tray(self): self.withdraw(); gc.collect()
    def show_from_tray(self): self.after(0, self.deiconify)
    def set_volume(self, v): self.player.audio_set_volume(int(v))
    def seek_song(self, v): self.player.set_position(float(v)/1000)
    def on_playlist_double_click(self, e):
        sel = self.playlist_box.curselection()
        if sel: self.current_idx = sel[0]; self.play_current()

if __name__ == "__main__":
    MusicController().mainloop()