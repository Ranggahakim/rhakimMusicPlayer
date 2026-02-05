import os
import threading
import vlc
import customtkinter as ctk
import syncedlyrics
import re
from tkinter import font as tkfont

class FloatingCinema(ctk.CTkToplevel):
    def __init__(self, master, player, song_path):
        super().__init__(master)
        self.overrideredirect(True)
        self.geometry("500x400")
        self.attributes("-topmost", True)
        
        self._drag_data = {"x": 0, "y": 0}
        self.player = player
        self.synced_lyrics = []
        self.base_font_family = "Arial"
        self.lyric_offset = 0.0 # Dalam detik

        # Container Utama
        self.main_container = ctk.CTkFrame(self, fg_color="black", border_width=1, border_color="#2ecc71")
        self.main_container.pack(fill="both", expand=True)

        # Video Frame
        self.video_frame = ctk.CTkFrame(self.main_container, fg_color="black")
        self.video_frame.pack(fill="both", expand=True)
        self.player.set_hwnd(self.video_frame.winfo_id())

        # Drag Bar & Offset Controls
        self.drag_bar = ctk.CTkFrame(self.main_container, height=35, fg_color="#111111")
        self.drag_bar.place(relx=0, rely=0, relwidth=1)
        
        # Lyric Offset UI
        self.offset_ctrl = ctk.CTkFrame(self.drag_bar, fg_color="transparent")
        self.offset_ctrl.pack(side="left", padx=10)
        ctk.CTkButton(self.offset_ctrl, text="-", width=20, height=20, command=lambda: self.adjust_offset(-0.5)).pack(side="left", padx=2)
        self.lbl_offset = ctk.CTkLabel(self.offset_ctrl, text="0.0s", font=("Arial", 10), text_color="#2ecc71")
        self.lbl_offset.pack(side="left", padx=2)
        ctk.CTkButton(self.offset_ctrl, text="+", width=20, height=20, command=lambda: self.adjust_offset(0.5)).pack(side="left", padx=2)

        self.drag_label = ctk.CTkLabel(self.drag_bar, text="DRAG AREA", font=("Arial", 8), text_color="#333333")
        self.drag_label.place(relx=0.5, rely=0.5, anchor="center")

        # Lirik Label (Overlay)
        self.lbl_lyrics = ctk.CTkLabel(self.main_container, text="", 
                                      font=(self.base_font_family, 20, "bold"), 
                                      text_color="#2ecc71", fg_color="transparent",
                                      wraplength=0, justify="center")
        self.lbl_lyrics.place(relx=0.5, rely=0.9, anchor="s", relwidth=0.9)

        # Buttons
        self.btn_close = ctk.CTkButton(self.main_container, text="✕", width=25, height=25,
                                      fg_color="transparent", hover_color="#e74c3c",
                                      command=self.withdraw)
        self.btn_close.place(relx=1.0, x=-5, y=5, anchor="ne")

        self.resize_grip = ctk.CTkLabel(self.main_container, text="◢", text_color="#2ecc71", cursor="size_nw_se")
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")
        
        # Bindings
        self.drag_bar.bind("<Button-1>", self.on_drag_start)
        self.drag_bar.bind("<B1-Motion>", self.on_drag_motion)
        self.lbl_lyrics.bind("<Button-1>", self.on_drag_start)
        self.lbl_lyrics.bind("<B1-Motion>", self.on_drag_motion)
        self.resize_grip.bind("<B1-Motion>", self.do_resize)
        self.bind("<Configure>", self.adjust_font_size)
        
        self.update_song(song_path)
        self.sync_loop()

    def adjust_offset(self, val):
        self.lyric_offset += val
        self.lbl_offset.configure(text=f"{self.lyric_offset:+.1f}s")

    def update_song(self, song_path):
        self.synced_lyrics = []
        self.lbl_lyrics.configure(text="• • •")
        threading.Thread(target=self.fetch_lrc, args=(song_path,), daemon=True).start()

    def fetch_lrc(self, full_path):
        try:
            base_path = os.path.splitext(full_path)[0]
            local_lrc_path = base_path + ".lrc"
            raw_lrc = ""
            if os.path.exists(local_lrc_path):
                with open(local_lrc_path, 'r', encoding='utf-8') as f: raw_lrc = f.read()
            else:
                raw_lrc = syncedlyrics.search(os.path.basename(base_path))
            if raw_lrc:
                lines = []
                for line in raw_lrc.splitlines():
                    match = re.search(r'\[(\d+):(\d+\.\d+)\](.*)', line)
                    if match:
                        ms = int((int(match.group(1)) * 60 + float(match.group(2))) * 1000)
                        lines.append((ms, match.group(3).strip()))
                self.synced_lyrics = sorted(lines)
            else:
                self.synced_lyrics = [(0, "Lirik tidak ditemukan")]
        except:
            self.synced_lyrics = [(0, "Gagal memuat lirik")]

    def sync_loop(self):
        if self.winfo_exists():
            current_ms = self.player.get_time() + (self.lyric_offset * 1000)
            curr_idx = -1
            for i, (ms, text) in enumerate(self.synced_lyrics):
                if current_ms >= ms: curr_idx = i
                else: break
            if curr_idx != -1:
                prev = self.synced_lyrics[curr_idx-1][1] if curr_idx > 0 else ""
                curr = self.synced_lyrics[curr_idx][1]
                nxt = self.synced_lyrics[curr_idx+1][1] if curr_idx < len(self.synced_lyrics)-1 else ""
                new_text = f"{prev}\n▶ {curr} ◀\n{nxt}"
                if self.lbl_lyrics.cget("text") != new_text:
                    self.lbl_lyrics.configure(text=new_text)
                    self.adjust_font_size()
            self.after(100, self.sync_loop)

    def on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def on_drag_motion(self, event):
        deltax = event.x - self._drag_data["x"]
        deltay = event.y - self._drag_data["y"]
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def do_resize(self, event):
        new_width = max(200, event.x_root - self.winfo_x())
        new_height = max(150, event.y_root - self.winfo_y())
        self.geometry(f"{new_width}x{new_height}")

    def adjust_font_size(self, event=None):
        current_text = self.lbl_lyrics.cget("text")
        if not current_text.strip(): return
        lines = current_text.split('\n')
        longest_line = max(lines, key=len) if lines else ""
        target_width = self.winfo_width() * 0.85
        target_height = self.winfo_height() * 0.3
        current_size = 22 
        while current_size > 8:
            test_font = tkfont.Font(family=self.base_font_family, size=current_size, weight="bold")
            if test_font.measure(longest_line) <= target_width and (test_font.metrics('linespace') * len(lines)) <= target_height:
                break
            current_size -= 1
        self.lbl_lyrics.configure(font=(self.base_font_family, current_size, "bold"))