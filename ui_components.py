import os, threading, re, syncedlyrics, gc
import vlc
import customtkinter as ctk
from tkinter import font as tkfont

class FloatingCinema(ctk.CTkToplevel):
    def __init__(self, master, player, song_path):
        super().__init__(master)
        self.overrideredirect(True)
        self.geometry("500x450") # Sedikit lebih tinggi biar 3 baris lega
        self.attributes("-topmost", True)
        
        self.player, self._drag_data = player, {"x": 0, "y": 0}
        self.synced_lyrics, self.lyric_offset = [], 0.0

        # UI Construction
        self.main = ctk.CTkFrame(self, fg_color="black", border_width=1, border_color="#2ecc71")
        self.main.pack(fill="both", expand=True)

        self.video_frame = ctk.CTkFrame(self.main, fg_color="black")
        self.video_frame.pack(fill="both", expand=True)
        self.player.set_hwnd(self.video_frame.winfo_id())

        # Drag & Control Bar
        self.bar = ctk.CTkFrame(self.main, height=35, fg_color="#111111")
        self.bar.place(relx=0, rely=0, relwidth=1)
        
        self.ctrl = ctk.CTkFrame(self.bar, fg_color="transparent")
        self.ctrl.pack(side="left", padx=10)
        ctk.CTkButton(self.ctrl, text="-", width=20, command=lambda: self.adj_off(-0.5)).pack(side="left", padx=2)
        self.lbl_off = ctk.CTkLabel(self.ctrl, text="0.0s", font=("Arial", 10), text_color="#2ecc71")
        self.lbl_off.pack(side="left", padx=2)
        ctk.CTkButton(self.ctrl, text="+", width=20, command=lambda: self.adj_off(0.5)).pack(side="left", padx=2)

        # Label Lirik (Dibuat lebih besar buat nampung 3 baris)
        self.lbl_lyr = ctk.CTkLabel(self.main, text="", font=("Arial", 18, "bold"), 
                                    text_color="#2ecc71", fg_color="transparent", 
                                    justify="center", wraplength=450)
        self.lbl_lyr.place(relx=0.5, rely=0.92, anchor="s", relwidth=0.95)

        # Close & Resize
        ctk.CTkButton(self.main, text="✕", width=25, height=25, fg_color="transparent", 
                      hover_color="#e74c3c", command=self.close_cinema).place(relx=1.0, x=-5, y=5, anchor="ne")
        
        self.sz = ctk.CTkLabel(self.main, text="◢", text_color="#2ecc71", cursor="size_nw_se")
        self.sz.place(relx=1.0, rely=1.0, anchor="se")
        
        for w in [self.bar, self.lbl_lyr]:
            w.bind("<Button-1>", self.start_drag)
            w.bind("<B1-Motion>", self.drag)
        self.sz.bind("<B1-Motion>", self.resize)
        
        self.update_song(song_path)
        self.sync_loop()

    def adj_off(self, v):
        self.lyric_offset += v
        self.lbl_off.configure(text=f"{self.lyric_offset:+.1f}s")

    def update_song(self, path):
        self.synced_lyrics = []
        self.lbl_lyr.configure(text="• • •")
        threading.Thread(target=self.fetch_lrc, args=(path,), daemon=True).start()

    def fetch_lrc(self, path):
        base = os.path.splitext(path)[0]
        lrc_path = base + ".lrc"
        try:
            if os.path.exists(lrc_path):
                with open(lrc_path, 'r', encoding='utf-8') as f: raw = f.read()
            else:
                raw = syncedlyrics.search(os.path.basename(base))
                if raw: 
                    with open(lrc_path, 'w', encoding='utf-8') as f: f.write(raw)
            
            if raw:
                lines = []
                for l in raw.splitlines():
                    m = re.search(r'\[(\d+):(\d+\.\d+)\](.*)', l)
                    if m: lines.append((int((int(m.group(1))*60 + float(m.group(2)))*1000), m.group(3).strip()))
                self.synced_lyrics = sorted(lines)
        except: self.synced_lyrics = [(0, "Lirik tidak tersedia")]

    def sync_loop(self):
        if self.winfo_exists():
            t = self.player.get_time() + (self.lyric_offset * 1000)
            
            # Cari index lirik sekarang
            curr_idx = -1
            for i, (ms, text) in enumerate(self.synced_lyrics):
                if t >= ms: curr_idx = i
                else: break

            if curr_idx != -1:
                # Logika Karaoke: Ambil baris SEBELUM, SEKARANG, dan SESUDAH
                prev_text = self.synced_lyrics[curr_idx-1][1] if curr_idx > 0 else ""
                curr_text = self.synced_lyrics[curr_idx][1]
                next_text = self.synced_lyrics[curr_idx+1][1] if curr_idx < len(self.synced_lyrics)-1 else ""
                
                # Gabungkan dengan pemisah newline dan marker khusus buat yang lagi jalan
                display_text = f"{prev_text}\n▶ {curr_text} ◀\n{next_text}"
                
                if self.lbl_lyr.cget("text") != display_text:
                    self.lbl_lyr.configure(text=display_text)
                    self.adjust_font_size()
                    
            self.after(150, self.sync_loop)

    def start_drag(self, e): self._drag_data.update({"x": e.x, "y": e.y})
    def drag(self, e):
        x = self.winfo_x() + (e.x - self._drag_data["x"])
        y = self.winfo_y() + (e.y - self._drag_data["y"])
        self.geometry(f"+{x}+{y}")
    def resize(self, e):
        self.geometry(f"{max(200, e.x_root - self.winfo_x())}x{max(150, e.y_root - self.winfo_y())}")

    def adjust_font_size(self):
        # Optimasi font biar gak nabrak pas 3 baris muncul
        lines = self.lbl_lyr.cget("text").split('\n')
        longest = max(lines, key=len) if lines else ""
        size = 20
        while size > 9:
            f = tkfont.Font(family="Arial", size=size, weight="bold")
            if f.measure(longest) < (self.winfo_width() * 0.9): break
            size -= 1
        self.lbl_lyr.configure(font=("Arial", size, "bold"))

    def close_cinema(self):
        self.withdraw()
        gc.collect()