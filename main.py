import os
from dotenv import load_dotenv
import time
import vlc
import json
import random
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from ui_components import FloatingCinema
from pypresence import Presence

load_dotenv()

# --- SETUP VLC ---
vlc_path = r'C:\Program Files\VideoLAN\VLC' 
if os.path.exists(vlc_path):
    os.add_dll_directory(vlc_path)

class MusicController(ctk.CTk):
    SETTINGS_FILE = "settings.json"

    def __init__(self):
        super().__init__()
        self.title("rhakim Music Controller")
        self.geometry("450x800")

        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
        
        self.all_songs = []
        self.playlist = []
        self.current_idx = 0
        self.cinema_window = None
        self.is_shuffle = False
        self.repeat_mode = "none" # "none", "one", "all"

        client_id = os.getenv("DISCORD_CLIENT_ID")
        # Discord RPC (Ganti CLIENT_ID dengan milikmu nanti)
        print(client_id)
        try:
            self.rpc = Presence(client_id) # Contoh ID
            self.rpc.connect()
            print("Mantap! Discord RPC Berhasil Konek.")
        except:
            self.rpc = None
            print("DISCORD ENGGA KONEK!")

        self.setup_ui()
        self.load_recent_folder()

    def setup_ui(self):
        # Header: Folder & Show Video
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(self.header, text="📁", width=40, command=self.open_folder_dialog).pack(side="left", padx=5)
        ctk.CTkButton(self.header, text="📺", width=40, fg_color="#2ecc71", command=self.ensure_window).pack(side="left", padx=5)
        
        # Search Bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_playlist)
        ctk.CTkEntry(self.header, placeholder_text="Cari lagu...", textvariable=self.search_var).pack(side="left", fill="x", expand=True)

        # Playlist Listbox
        self.playlist_box = tk.Listbox(self, bg="#1d1e1e", fg="#ffffff", selectbackground="#2ecc71", 
                                      selectforeground="#000000", font=("Arial", 11), borderwidth=0)
        self.playlist_box.pack(pady=5, padx=20, fill="both", expand=True)
        self.playlist_box.bind("<Double-Button-1>", self.on_playlist_double_click)

        # Volume & Modes Frame
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

        # Progress & Time
        self.lbl_time = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_time.pack()
        self.slider_progress = ctk.CTkSlider(self, from_=0, to=1000, command=self.seek_song)
        self.slider_progress.set(0)
        self.slider_progress.pack(pady=10, padx=30, fill="x")

        # Playback Nav
        self.nav = ctk.CTkFrame(self, fg_color="transparent")
        self.nav.pack(pady=10)
        ctk.CTkButton(self.nav, text="⏮", width=60, command=self.prev_song).grid(row=0, column=0, padx=10)
        self.btn_play = ctk.CTkButton(self.nav, text="▶ PLAY", width=120, command=self.toggle_play)
        self.btn_play.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.nav, text="⏭", width=60, command=self.next_song).grid(row=0, column=2, padx=10)

        self.update_ui_loop()

    def set_volume(self, val):
        self.player.audio_set_volume(int(val))

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
            self.cinema_window.focus()

    def play_current(self):
        if not self.playlist: return
        self.ensure_window()
        path = self.playlist[self.current_idx]
        song_name = os.path.basename(path)
        media = self.instance.media_new(path)
        self.player.set_media(media)
        if self.cinema_window and self.cinema_window.winfo_exists():
            self.cinema_window.update_song(path)
        self.player.play()
        self.btn_play.configure(text="⏸ PAUSE")
        self.update_listbox()
        if self.rpc: 
            try: 
                self.rpc.update(
                    details=f"🎵 {song_name}", # Baris pertama: Judul Lagu
                    state="Enjoying the MV",     # Baris kedua: Status tambahan
                    large_image="logo",          # Nama file icon yang kamu upload di Discord Dev Portal
                    large_text="rhakim Music Player",
                    start=time.time()            # Menampilkan durasi 'elapsed' (sudah berapa lama diputar)
                )
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
        if 0 <= self.current_idx < len(self.playlist):
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.selection_set(self.current_idx)

    def on_playlist_double_click(self, event):
        sel = self.playlist_box.curselection()
        if sel: self.current_idx = sel[0]; self.play_current()

    def update_ui_loop(self):
        if self.player.is_playing():
            pos = self.player.get_position() * 1000
            if pos >= 0: self.slider_progress.set(pos)
            curr = self.player.get_time() // 1000
            total = self.player.get_length() // 1000
            if total > 0: self.lbl_time.configure(text=f"{curr//60:02d}:{curr%60:02d} / {total//60:02d}:{total%60:02d}")
        if self.player.get_state() == vlc.State.Ended:
            if self.repeat_mode == "one": self.play_current()
            else: self.next_song()
        self.after(500, self.update_ui_loop)

    def open_folder_dialog(self):
        f = filedialog.askdirectory()
        if f: self.save_settings(f); self.process_playlist(f)

    def process_playlist(self, path):
        self.all_songs = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.mp4', '.mp3', '.m4a'))]
        self.filter_playlist()

    def load_recent_folder(self):
        if os.path.exists(self.SETTINGS_FILE):
            with open(self.SETTINGS_FILE, "r") as f:
                path = json.load(f).get("last_folder")
                if path and os.path.exists(path): self.process_playlist(path)

    def save_settings(self, path):
        with open(self.SETTINGS_FILE, "w") as f: json.dump({"last_folder": path}, f)

    def seek_song(self, val): self.player.set_position(float(val)/1000)

if __name__ == "__main__":
    MusicController().mainloop()