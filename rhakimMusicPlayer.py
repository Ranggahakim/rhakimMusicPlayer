import os
import threading
import vlc
import customtkinter as ctk
from tkinter import filedialog
import syncedlyrics
import re

# --- CONFIGURATION ---
vlc_path = r'C:\Program Files\VideoLAN\VLC' 
if os.path.exists(vlc_path):
    os.add_dll_directory(vlc_path)

class FloatingCinema(ctk.CTkToplevel):
    def __init__(self, master, player, song_path):
        super().__init__(master)
        self.title("D-Music Floating")
        self.geometry("450x350")
        self.attributes("-topmost", True)
        
        self.player = player
        self.synced_lyrics = []
        
        # --- UI: Video Container ---
        self.video_frame = ctk.CTkFrame(self, fg_color="black")
        self.video_frame.pack(fill="both", expand=True)
        
        # --- UI: 3-Line Lyrics Label ---
        self.lbl_lyrics = ctk.CTkLabel(self, text="", 
                                      font=("Arial", 18, "bold"), text_color="#2ecc71", 
                                      wraplength=400, fg_color="#1a1a1a", justify="center")
        self.lbl_lyrics.pack(fill="x", pady=5)

        # Tempelkan VLC ke Frame
        self.player.set_hwnd(self.video_frame.winfo_id())
        
        # --- FEATURE: Click to Drag ---
        # Memungkinkan geser jendela tanpa judul bar
        self.video_frame.bind("<Button-1>", self.start_drag)
        self.video_frame.bind("<B1-Motion>", self.do_drag)
        self.lbl_lyrics.bind("<Button-1>", self.start_drag)
        self.lbl_lyrics.bind("<B1-Motion>", self.do_drag)
        
        # --- FEATURE: Smart Responsive Text ---
        self.bind("<Configure>", self.on_window_resize)
        
        self.update_song(song_path)
        self.sync_loop()

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def do_drag(self, event):
        x = self.winfo_x() + (event.x - self.drag_x)
        y = self.winfo_y() + (event.y - self.drag_y)
        self.geometry(f"+{x}+{y}")

    def on_window_resize(self, event):
        """Menghitung ukuran font berdasarkan rasio jendela agar tidak overflow"""
        if event.widget == self:
            # Ambil skala dari lebar dan tinggi (mana yang paling kecil)
            width_scale = event.width / 500
            height_scale = event.height / 400
            scale = min(width_scale, height_scale)
            
            # Font size dasar 18, disesuaikan dengan skala. Minimal 10, maksimal 30.
            new_size = max(10, min(30, int(18 * scale)))
            
            self.lbl_lyrics.configure(
                font=("Arial", new_size, "bold"),
                wraplength=event.width - 30
            )

    def update_song(self, song_path):
        song_name = os.path.basename(song_path)
        self.lbl_lyrics.configure(text="\nLoading Lyrics...\n")
        threading.Thread(target=self.fetch_lrc, args=(song_name,), daemon=True).start()

    def fetch_lrc(self, title):
        try:
            clean_title = os.path.splitext(title)[0]
            raw_lrc = syncedlyrics.search(clean_title)
            if raw_lrc:
                lines = []
                for line in raw_lrc.splitlines():
                    match = re.search(r'\[(\d+):(\d+\.\d+)\](.*)', line)
                    if match:
                        ms = int((int(match.group(1)) * 60 + float(match.group(2))) * 1000)
                        lines.append((ms, match.group(3).strip()))
                self.synced_lyrics = sorted(lines)
            else:
                self.synced_lyrics = [(0, f"♫ Instrumental / No Lyrics ♫\n{clean_title}")]
        except Exception:
            self.synced_lyrics = [(0, "Gagal mengambil lirik.\nPeriksa koneksi internet.")]

    def sync_loop(self):
        if self.winfo_exists():
            current_ms = self.player.get_time()
            curr_idx = -1
            for i, (ms, text) in enumerate(self.synced_lyrics):
                if current_ms >= ms: curr_idx = i
                else: break
            
            if curr_idx != -1:
                prev = self.synced_lyrics[curr_idx-1][1] if curr_idx > 0 else ""
                curr = self.synced_lyrics[curr_idx][1]
                nxt = self.synced_lyrics[curr_idx+1][1] if curr_idx < len(self.synced_lyrics)-1 else ""
                
                # Format 3 baris: redupkan yang atas dan bawah sedikit (opsional lewat warna atau simbol)
                self.lbl_lyrics.configure(text=f"{prev}\n▶ {curr} ◀\n{nxt}")
            
            self.after(100, self.sync_loop)

class MusicController(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("D-Music Controller")
        self.geometry("380x650")

        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
        
        self.playlist = []
        self.current_idx = 0
        self.cinema_window = None

        # --- UI: Playlist Area ---
        ctk.CTkButton(self, text="📁 Pilih Folder", command=self.load_folder).pack(pady=15)
        self.playlist_box = ctk.CTkTextbox(self, width=320, height=350)
        self.playlist_box.pack(pady=10)

        # --- UI: Progress Slider (DI ATAS BUTTONS) ---
        self.lbl_time = ctk.CTkLabel(self, text="00:00 / 00:00", font=("Arial", 10))
        self.lbl_time.pack()
        
        self.slider_progress = ctk.CTkSlider(self, from_=0, to=1000, command=self.seek_song)
        self.slider_progress.set(0)
        self.slider_progress.pack(pady=10, padx=30, fill="x")

        # --- UI: Navigation Buttons (Prev, Play, Next) ---
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(pady=10)

        self.btn_prev = ctk.CTkButton(self.nav_frame, text="⏮", width=60, command=self.prev_song)
        self.btn_prev.grid(row=0, column=0, padx=10)

        self.btn_play = ctk.CTkButton(self.nav_frame, text="⏸ PAUSE", width=120, command=self.toggle_play)
        self.btn_play.grid(row=0, column=1, padx=10)

        self.btn_next = ctk.CTkButton(self.nav_frame, text="⏭", width=60, command=self.next_song)
        self.btn_next.grid(row=0, column=2, padx=10)

        self.update_ui_loop()

    def load_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.playlist = [os.path.join(folder, f) for f in os.listdir(folder) 
                             if f.lower().endswith(('.mp4', '.mp3', '.m4a'))]
            self.update_listbox()

    def update_listbox(self):
        self.playlist_box.delete("0.0", "end")
        for f in self.playlist:
            self.playlist_box.insert("end", f"{os.path.basename(f)}\n")

    def play_current(self):
        if not self.playlist: return
        path = self.playlist[self.current_idx]
        media = self.instance.media_new(path)
        self.player.set_media(media)
        
        if self.cinema_window is None or not self.cinema_window.winfo_exists():
            self.cinema_window = FloatingCinema(self, self.player, path)
        else:
            self.cinema_window.update_song(path)
            self.player.set_hwnd(self.cinema_window.video_frame.winfo_id())

        self.player.play()
        self.btn_play.configure(text="⏸ PAUSE")

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.configure(text="▶ PLAY")
        else:
            if self.player.get_state() == vlc.State.NothingSpecial:
                self.play_current()
            else:
                self.player.play()
                self.btn_play.configure(text="⏸ PAUSE")

    def next_song(self):
        if not self.playlist: return
        self.current_idx = (self.current_idx + 1) % len(self.playlist)
        self.play_current()

    def prev_song(self):
        if not self.playlist: return
        self.current_idx = (self.current_idx - 1) % len(self.playlist)
        self.play_current()

    def seek_song(self, value):
        self.player.set_position(float(value) / 1000)

    def update_ui_loop(self):
        if self.player.is_playing():
            pos = self.player.get_position() * 1000
            if pos >= 0: self.slider_progress.set(pos)
            
            # Update durasi teks (MM:SS)
            curr = self.player.get_time() // 1000
            total = self.player.get_length() // 1000
            if total > 0:
                self.lbl_time.configure(text=f"{curr//60:02d}:{curr%60:02d} / {total//60:02d}:{total%60:02d}")
                
        self.after(500, self.update_ui_loop)

if __name__ == "__main__":
    app = MusicController()
    app.mainloop()