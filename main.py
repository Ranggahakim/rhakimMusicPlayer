import os
import vlc
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from ui_components import FloatingCinema

# --- SETUP VLC ---
vlc_path = r'C:\Program Files\VideoLAN\VLC' 
if os.path.exists(vlc_path):
    os.add_dll_directory(vlc_path)

class MusicController(ctk.CTk):
    SETTINGS_FILE = "settings.json"

    def __init__(self):
        super().__init__()
        self.title("rhakim Music Player")
        self.geometry("400x750")

        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
        
        self.all_songs = []
        self.playlist = []
        self.current_idx = 0
        self.cinema_window = None

        self.setup_ui()
        self.load_recent_folder()

    def setup_ui(self):
        # 1. Bagian Atas: Folder, Search, & Show Video
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(pady=10, padx=20, fill="x")

        # Tombol Pilih Folder
        ctk.CTkButton(self.top_frame, text="📁", width=40, command=self.open_folder_dialog).pack(side="left", padx=(0, 5))
        
        # Tombol Manual Show Video (Fitur Baru)
        self.btn_show_vid = ctk.CTkButton(self.top_frame, text="📺", width=40, fg_color="#2ecc71", hover_color="#27ae60", command=self.ensure_window)
        self.btn_show_vid.pack(side="left", padx=(0, 10))
        
        # Search Bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_playlist)
        self.search_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Cari lagu...", textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)

        # 2. Playlist Box (Listbox)
        self.playlist_box = tk.Listbox(
            self, bg="#1d1e1e", fg="#ffffff", selectbackground="#2ecc71", 
            selectforeground="#000000", font=("Arial", 11), borderwidth=0, highlightthickness=0
        )
        self.playlist_box.pack(pady=5, padx=20, fill="both", expand=True)
        self.playlist_box.bind("<Double-Button-1>", self.on_playlist_double_click)

        # 3. Info & Slider
        self.lbl_time = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_time.pack()
        self.slider_progress = ctk.CTkSlider(self, from_=0, to=1000, command=self.seek_song)
        self.slider_progress.set(0)
        self.slider_progress.pack(pady=10, padx=30, fill="x")

        # 4. Navigasi
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(pady=10)
        ctk.CTkButton(self.nav_frame, text="⏮", width=60, command=self.prev_song).grid(row=0, column=0, padx=10)
        self.btn_play = ctk.CTkButton(self.nav_frame, text="▶ PLAY", width=120, command=self.toggle_play)
        self.btn_play.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.nav_frame, text="⏭", width=60, command=self.next_song).grid(row=0, column=2, padx=10)

        self.update_ui_loop()

    # --- LOGIKA RE-OPEN WINDOW ---
    def ensure_window(self):
        """Menampilkan kembali floating window tanpa membuat ulang jika sudah ada"""
        if not self.playlist: return
        
        path = self.playlist[self.current_idx]
        
        # 1. Jika jendela BELUM PERNAH dibuat
        if self.cinema_window is None:
            self.cinema_window = FloatingCinema(self, self.player, path)
            # Pastikan ID jendela terdaftar di VLC
            self.cinema_window.update() 
            self.player.set_hwnd(self.cinema_window.video_frame.winfo_id())
            
        # 2. Jika jendela SUDAH ADA (mungkin sedang 'withdraw' atau terbuka)
        else:
            # Munculkan kembali dari persembunyian
            self.cinema_window.deiconify() 
            self.cinema_window.focus()
            
            # Opsional: Re-attach HWND jaga-jaga kalau VLC 'lupa'
            self.player.set_hwnd(self.cinema_window.video_frame.winfo_id())

    def toggle_play(self):
        """Fungsi play yang sekarang jauh lebih aman"""
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.configure(text="▶ PLAY")
        else:
            self.ensure_window() # Panggil logika deiconify/create
            self.player.play()
            self.btn_play.configure(text="⏸ PAUSE")

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.configure(text="▶ PLAY")
        else:
            # Otomatis munculkan window kalau user klik Play
            self.ensure_window()
            self.player.play()
            self.btn_play.configure(text="⏸ PAUSE")

    def play_current(self):
        if not self.playlist: return
        self.ensure_window() 
        
        path = self.playlist[self.current_idx]
        media = self.instance.media_new(path)
        self.player.set_media(media)
        
        if self.cinema_window and self.cinema_window.winfo_exists():
            self.cinema_window.update_song(path)
            self.player.set_hwnd(self.cinema_window.video_frame.winfo_id())

        self.player.play()
        self.btn_play.configure(text="⏸ PAUSE")
        self.update_listbox()

    # --- LOGIKA FILTER & HELPER (TETAP SAMA) ---
    def filter_playlist(self, *args):
        query = self.search_var.get().lower()
        self.playlist = [f for f in self.all_songs if query in os.path.basename(f).lower()]
        self.update_listbox()

    def update_listbox(self):
        self.playlist_box.delete(0, tk.END)
        for f in self.playlist:
            self.playlist_box.insert(tk.END, f"  {os.path.basename(f)}")
        if 0 <= self.current_idx < len(self.playlist):
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.selection_set(self.current_idx)

    def next_song(self):
        if not self.playlist: return
        self.current_idx = (self.current_idx + 1) % len(self.playlist)
        self.play_current()

    def prev_song(self):
        if not self.playlist: return
        self.current_idx = (self.current_idx - 1) % len(self.playlist)
        self.play_current()

    def on_playlist_double_click(self, event):
        selection = self.playlist_box.curselection()
        if selection:
            self.current_idx = selection[0]
            self.play_current()

    def seek_song(self, value):
        self.player.set_position(float(value) / 1000)

    def update_ui_loop(self):
        if self.player.is_playing():
            pos = self.player.get_position() * 1000
            if pos >= 0: self.slider_progress.set(pos)
            curr = self.player.get_time() // 1000
            total = self.player.get_length() // 1000
            if total > 0:
                self.lbl_time.configure(text=f"{curr//60:02d}:{curr%60:02d} / {total//60:02d}:{total%60:02d}")
        
        if self.player.get_state() == vlc.State.Ended:
            self.next_song()
        self.after(500, self.update_ui_loop)

    def open_folder_dialog(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_settings(folder)
            self.process_playlist(folder)

    def process_playlist(self, folder_path):
        self.all_songs = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                          if f.lower().endswith(('.mp4', '.mp3', '.m4a'))]
        self.filter_playlist()

    def load_recent_folder(self):
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    last_path = data.get("last_folder")
                    if last_path and os.path.exists(last_path):
                        self.process_playlist(last_path)
            except Exception: pass

    def save_settings(self, folder_path):
        with open(self.SETTINGS_FILE, "w") as f:
            json.dump({"last_folder": folder_path}, f)

if __name__ == "__main__":
    app = MusicController()
    app.mainloop()