import os
import vlc
import customtkinter as ctk
from tkinter import filedialog
from ui_components import FloatingCinema

# --- SETUP VLC ---
vlc_path = r'C:\Program Files\VideoLAN\VLC' 
if os.path.exists(vlc_path):
    os.add_dll_directory(vlc_path)

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

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkButton(self, text="📁 Pilih Folder", command=self.load_folder).pack(pady=15)
        self.playlist_box = ctk.CTkTextbox(self, width=320, height=350)
        self.playlist_box.pack(pady=10)

        self.lbl_time = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.lbl_time.pack()
        
        self.slider_progress = ctk.CTkSlider(self, from_=0, to=1000, command=self.seek_song)
        self.slider_progress.set(0)
        self.slider_progress.pack(pady=10, padx=30, fill="x")

        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(pady=10)
        
        ctk.CTkButton(self.nav_frame, text="⏮", width=60, command=self.prev_song).grid(row=0, column=0, padx=10)
        self.btn_play = ctk.CTkButton(self.nav_frame, text="▶ PLAY", width=120, command=self.toggle_play)
        self.btn_play.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.nav_frame, text="⏭", width=60, command=self.next_song).grid(row=0, column=2, padx=10)

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
            
            curr = self.player.get_time() // 1000
            total = self.player.get_length() // 1000
            if total > 0:
                self.lbl_time.configure(text=f"{curr//60:02d}:{curr%60:02d} / {total//60:02d}:{total%60:02d}")
        self.after(500, self.update_ui_loop)

if __name__ == "__main__":
    app = MusicController()
    app.mainloop()