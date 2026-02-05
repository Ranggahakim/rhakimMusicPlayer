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
from queue_manager import QueueWindow
from downloader import DownloadWindow

load_dotenv()

def resource_path(relative_path):
    """ Dapatkan path absolut untuk dev dan PyInstaller """
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
        # Agar icon muncul benar di taskbar
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('rhakim.musicplayer.v2')

        self.title("rhakim Music Player")
        self.geometry("450x880") # Sedikit lebih tinggi untuk kontrol RPC
        
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
        self.repeat_mode = "none" 
        self.observer = None
        self.tray_icon = None

        # --- DISCORD RPC STATE ---
        self.rpc_presets = ["Coding", "Chill", "Gaming", "Sad", "Depress", "Energic"]
        self.custom_status_var = ctk.StringVar(value="Chill")

        self.queue = []

        self.setup_rpc()
        self.setup_ui()
        self.load_recent_folder()
        threading.Thread(target=self.create_tray_icon, daemon=True).start()

    def setup_rpc(self):
        # Gunakan Client ID asli kamu di sini sebagai cadangan
        client_id = os.getenv("DISCORD_CLIENT_ID") or "YOUR_HARDCODED_ID_HERE"
        try:
            if client_id:
                self.rpc = Presence(client_id)
                self.rpc.connect()
            else: self.rpc = None
        except: self.rpc = None

    def setup_ui(self):
        # Header (Folder, Cinema, Download)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(self.header, text="📁", width=40, command=self.open_folder_dialog).pack(side="left", padx=5)
        ctk.CTkButton(self.header, text="📺", width=40, fg_color="#2ecc71", command=self.ensure_window).pack(side="left", padx=5)
        ctk.CTkButton(self.header, text="📥", width=40, fg_color="#e74c3c", command=self.open_download_window).pack(side="left", padx=5)
        ctk.CTkButton(self.header, text="🔢", width=40, fg_color="#9b59b6", command=self.open_queue_window).pack(side="left", padx=5)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_playlist)
        ctk.CTkEntry(self.header, placeholder_text="Cari lagu...", textvariable=self.search_var).pack(side="left", fill="x", expand=True)

        # --- AUDIO EQUALIZER ---
        self.eq_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.eq_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(self.eq_frame, text="EQ:").pack(side="left", padx=5)
        self.eq_menu = ctk.CTkOptionMenu(self.eq_frame, values=["Flat", "Bass Boost", "Rock", "Pop"], 
                                         command=self.apply_eq_preset, width=100, fg_color="#27ae60")
        self.eq_menu.pack(side="left", padx=5)

        # --- DISCORD RPC CONTROLS ---
        self.rpc_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.rpc_frame.pack(pady=5, padx=20, fill="x")
        
        self.rpc_menu = ctk.CTkOptionMenu(self.rpc_frame, values=self.rpc_presets, 
                                          command=self.change_rpc_mode, width=100, fg_color="#7289da")
        self.rpc_menu.pack(side="left", padx=5)
        
        self.rpc_entry = ctk.CTkEntry(self.rpc_frame, textvariable=self.custom_status_var, placeholder_text="Custom status...")
        self.rpc_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkButton(self.rpc_frame, text="Set", width=40, command=self.update_rpc_status).pack(side="left", padx=2)

        # Playlist Box
        self.playlist_box = tk.Listbox(self, bg="#1d1e1e", fg="#ffffff", selectbackground="#2ecc71", 
                                      selectforeground="#000000", font=("Arial", 11), borderwidth=0)
        self.playlist_box.pack(pady=5, padx=20, fill="both", expand=True)
        self.playlist_box.bind("<Double-Button-1>", self.on_playlist_double_click)

        # Mode & Volume
        self.btm_ctrl = ctk.CTkFrame(self, fg_color="transparent")
        self.btm_ctrl.pack(pady=5, padx=20, fill="x")
        
        self.btn_shuffle = ctk.CTkButton(self.btm_ctrl, text="🔀 OFF", width=70, fg_color="#333", command=self.toggle_shuffle)
        self.btn_shuffle.pack(side="left", padx=5)
        self.btn_repeat = ctk.CTkButton(self.btm_ctrl, text="🔁 OFF", width=70, fg_color="#333", command=self.toggle_repeat)
        self.btn_repeat.pack(side="left", padx=5)

        self.slider_vol = ctk.CTkSlider(self.btm_ctrl, from_=0, to=100, width=120, command=self.set_volume)
        self.slider_vol.set(70); self.slider_vol.pack(side="right", padx=5)

        # Progress & Nav
        self.slider_progress = ctk.CTkSlider(self, from_=0, to=1000, command=self.seek_song)
        self.slider_progress.pack(pady=10, padx=30, fill="x")

        self.nav = ctk.CTkFrame(self, fg_color="transparent")
        self.nav.pack(pady=10)
        ctk.CTkButton(self.nav, text="⏮", width=60, font=("Arial", 20), command=self.prev_song).grid(row=0, column=0, padx=10)
        self.btn_play = ctk.CTkButton(self.nav, text="▶ PLAY", width=120, font=("Arial", 14, "bold"), command=self.toggle_play)
        self.btn_play.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.nav, text="⏭", width=60, font=("Arial", 20), command=self.next_song).grid(row=0, column=2, padx=10)

        # Binding Klik Kanan (Button-3 adalah klik kanan di Windows)
        self.playlist_box.bind("<Button-3>", self.show_context_menu)
        
        # Buat Menu Klik Kanan (Context Menu)
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", borderwidth=0)
        self.context_menu.add_command(label="➕ Add to Queue", command=self.add_to_queue)

        self.update_ui_loop()

    # --- DISCORD RPC LOGIC ---
    def change_rpc_mode(self, choice):
        self.custom_status_var.set(choice)
        self.update_rpc_status()

    def update_rpc_status(self):
        if not self.rpc or not self.winfo_exists(): return
        try:
            song = os.path.basename(self.playlist[self.current_idx]) if self.playlist else "Silence"
            status = self.custom_status_var.get()
            self.rpc.update(details=f"🎵 {song}", state=status, large_image="logo", large_text="rhakim Music Player")
        except: pass

    # --- AUDIO LOGIC ---
    def apply_eq_preset(self, p):
        ps = {"Flat": [0]*10, "Bass Boost": [8,6,4,0,0,0,0,0,0,0], "Rock": [5,3,-1,-3,-1,2,5,6,6,6], "Pop": [-2,-1,2,5,4,-1,-2,-2,-2,-2]}
        for i, v in enumerate(ps.get(p, ps["Flat"])): self.equalizer.set_amp_at_index(float(v), i)
        self.player.set_equalizer(self.equalizer)

    def play_current(self):
        if not self.playlist: return
        self.ensure_window()
        path = self.playlist[self.current_idx]
        self.player.set_media(self.instance.media_new(path))
        if self.cinema_window: self.cinema_window.update_song(path)
        self.player.play(); self.btn_play.configure(text="⏸ PAUSE")
        self.update_listbox()
        self.update_rpc_status()

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        self.btn_shuffle.configure(text=f"🔀 {'ON' if self.is_shuffle else 'OFF'}", fg_color="#2ecc71" if self.is_shuffle else "#333")

    def toggle_repeat(self):
        m = ["none", "one", "all"]
        self.repeat_mode = m[(m.index(self.repeat_mode)+1)%3]
        self.btn_repeat.configure(text=f"🔁 {self.repeat_mode.upper()}", fg_color="#2ecc71" if self.repeat_mode != "none" else "#333")

    def next_song(self):
        if not self.playlist: return
        
        # --- LOGIKA ANTREAN (CEK DISINI) ---
        if self.queue:
            # Ambil lagu paling atas dari antrean
            next_path = self.queue.pop(0) 
            
            # Update index agar sinkron dengan playlist utama
            if next_path in self.playlist:
                self.current_idx = self.playlist.index(next_path)
            
            # Update jendela antrean kalau lagi kebuka
            if hasattr(self, 'q_win') and self.q_win.winfo_exists():
                self.q_win.update_list()
                
            self.play_current()
            return # Selesai, jangan lanjut ke shuffle/normal

        # --- LOGIKA NORMAL (Kalau antrean kosong) ---
        if self.is_shuffle:
            self.current_idx = random.randint(0, len(self.playlist)-1)
        else:
            self.current_idx = (self.current_idx + 1) % len(self.playlist)
        self.play_current()

    def prev_song(self):
        if not self.playlist: return
        self.current_idx = (self.current_idx - 1) % len(self.playlist); self.play_current()

    def toggle_play(self):
        if self.player.is_playing(): self.player.pause(); self.btn_play.configure(text="▶ PLAY")
        else: self.ensure_window(); self.player.play(); self.btn_play.configure(text="⏸ PAUSE")

    def update_ui_loop(self):
        # Cek apakah jendela masih ada sebelum lanjut
        if not self.winfo_exists(): 
            return
            
        if self.player.is_playing():
            pos = self.player.get_position() * 1000
            if pos >= 0: self.slider_progress.set(pos)
            
        if self.player.get_state() == vlc.State.Ended:
            if self.repeat_mode == "one": self.play_current()
            else: self.next_song()
            
        # Gunakan try-except untuk menangkap error saat closing
        try:
            self.after(500, self.update_ui_loop)
        except:
            pass

    # --- FILE & SYSTEM LOGIC ---
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
        self.update_listbox()

    def update_listbox(self):
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
        # Sembunyikan window utama segera agar terasa 'instan' bagi user
        self.withdraw() 
        
        # 1. Matikan Folder Watcher agar tidak memicu event baru
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=1)
            except: pass

        # 2. Hancurkan jendela tambahan secara eksplisit
        windows = [getattr(self, 'cinema_window', None), 
                   getattr(self, 'dl_win', None), 
                   getattr(self, 'q_win', None)]
        
        for win in windows:
            if win and win.winfo_exists():
                try: win.destroy()
                except: pass

        # 3. Matikan Tray Icon & RPC
        if self.tray_icon:
            self.tray_icon.stop()
        if self.rpc:
            try: self.rpc.close()
            except: pass

        # 4. Hentikan loop Tkinter
        self.quit()
        
        # 5. Tombol Nuklir: Pastikan semua thread (VLC/Pystray) mati total
        # Ini mencegah proses 'gentayangan' di Task Manager
        os._exit(0)

    def hide_to_tray(self): self.withdraw(); gc.collect()
    def show_from_tray(self): self.after(0, self.deiconify)
    def set_volume(self, v): self.player.audio_set_volume(int(v))
    def seek_song(self, v): self.player.set_position(float(v)/1000)
    def on_playlist_double_click(self, e):
        sel = self.playlist_box.curselection()
        if sel: self.current_idx = sel[0]; self.play_current()

    def open_queue_window(self):
        if hasattr(self, 'q_win') and self.q_win.winfo_exists():
            self.q_win.focus()
        else:
            self.q_win = QueueWindow(self, self.queue, self.remove_from_queue)

    def remove_from_queue(self, index):
        if 0 <= index < len(self.queue):
            self.queue.pop(index)

    def add_to_queue(self):
        sel = self.playlist_box.curselection()
        if sel:
            path = self.playlist[sel[0]]
            self.queue.append(path)
            # Jika jendela antrean sedang terbuka, langsung update listnya
            if hasattr(self, 'q_win') and self.q_win.winfo_exists():
                self.q_win.update_list()
    
    def show_context_menu(self, event):
        # Ambil index lagu yang paling dekat dengan posisi kursor
        idx = self.playlist_box.nearest(event.y)
        
        # Select lagu tersebut secara otomatis
        self.playlist_box.selection_clear(0, tk.END)
        self.playlist_box.selection_set(idx)
        
        # Munculkan menu di koordinat mouse
        self.context_menu.post(event.x_root, event.y_root)

    def add_to_queue(self):
        sel = self.playlist_box.curselection()
        if sel:
            path = self.playlist[sel[0]]
            self.queue.append(path)
            
            # Print di terminal buat mastiin masuk
            print(f"Added to Queue: {os.path.basename(path)}")
            
            # Kalau Jendela Antrean (QueueWindow) lagi dibuka, langsung update list-nya
            if hasattr(self, 'q_win') and self.q_win.winfo_exists():
                self.q_win.update_list()

if __name__ == "__main__":
    MusicController().mainloop()