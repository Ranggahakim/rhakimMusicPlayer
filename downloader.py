import os, threading, gc, yt_dlp
import customtkinter as ctk
from tkinter import filedialog, messagebox

class DownloadWindow(ctk.CTkToplevel):
    def __init__(self, parent, refresh_callback):
        super().__init__(parent)
        self.title("MV Downloader (480p)")
        self.geometry("500x320")
        self.refresh_callback = refresh_callback
        self.attributes('-topmost', True)
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="YouTube Link:", font=("Arial", 13, "bold")).pack(pady=(20, 5))
        self.url_entry = ctk.CTkEntry(self, placeholder_text="Paste link YouTube...", width=420)
        self.url_entry.pack(pady=5)

        ctk.CTkLabel(self, text="Save to Folder:", font=("Arial", 12)).pack(pady=(15, 5))
        f_frame = ctk.CTkFrame(self, fg_color="transparent")
        f_frame.pack(fill="x", padx=40)
        
        self.folder_path = ctk.StringVar(value=os.getcwd())
        ctk.CTkEntry(f_frame, textvariable=self.folder_path, width=320).pack(side="left", padx=5)
        ctk.CTkButton(f_frame, text="📁", width=40, command=self.browse).pack(side="left")

        self.btn_dl = ctk.CTkButton(self, text="🚀 DOWNLOAD MV", fg_color="#e74c3c", 
                                    hover_color="#c0392b", command=self.start_dl)
        self.btn_dl.pack(pady=25)

    def browse(self):
        f = filedialog.askdirectory()
        if f: self.folder_path.set(f)

    def start_dl(self):
        url = self.url_entry.get().strip()
        if not url: return messagebox.showwarning("!", "Link kosong, Bree.")
        self.btn_dl.configure(state="disabled", text="⏳ Downloading...")
        threading.Thread(target=self.run_dl, args=(url,), daemon=True).start()

    def run_dl(self, url):
        opts = {
            'format': 'best[height<=480][ext=mp4]/best[height<=480]', 
            'outtmpl': f'{self.folder_path.get()}/%(title)s.%(ext)s',
            'noplaylist': True, 'quiet': True
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
            if self.refresh_callback: self.after(0, self.refresh_callback)
            self.after(0, lambda: messagebox.showinfo("Done", "MV Berhasil masuk list!"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Err", f"Gagal: {e}"))
        finally:
            self.after(0, self.reset_ui)
            gc.collect() # Bersihkan sisa download dari RAM

    def reset_ui(self):
        self.btn_dl.configure(state="normal", text="🚀 DOWNLOAD MV")
        self.url_entry.delete(0, 'end')