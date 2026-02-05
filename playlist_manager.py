import os, json, gc, sys
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class PlaylistEditor(ctk.CTkToplevel):
    def __init__(self, master, playlist_name, songs, save_callback):
        super().__init__(master)
        self.title(f"Editing: {playlist_name}")
        
        icon_path = resource_path("app.ico")
        if os.path.exists(icon_path):
            self.after(200, lambda: self.iconbitmap(icon_path))

        self.geometry("500x550")
        self.attributes("-topmost", True)
        
        self.playlist_name = playlist_name
        self.songs = songs
        self.save_callback = save_callback
        
        

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text=f"📂 Playlist: {self.playlist_name}", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(self, text="Tip: Drag & Drop untuk urutkan | Klik kanan untuk hapus", font=("Arial", 10), text_color="gray").pack()

        # Listbox untuk lagu dalam playlist
        self.list_box = tk.Listbox(
            self, bg="#1d1e1e", fg="#ffffff", selectbackground="#2ecc71",
            highlightthickness=0, font=("Arial", 11), borderwidth=0
        )
        self.list_box.pack(pady=10, padx=20, fill="both", expand=True)

        # Logic Drag & Drop
        self.list_box.bind('<Button-1>', self.on_start_drag)
        self.list_box.bind('<B1-Motion>', self.on_drag_motion)
        self.list_box.bind('<Button-3>', self.remove_song_context)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkButton(btn_frame, text="💾 Save Changes", fg_color="#2ecc71", hover_color="#27ae60", command=self.save).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="➕ Add from Main", fg_color="#3498db", command=self.add_from_main).pack(side="left", expand=True, padx=5)

        self.refresh_list()

    def refresh_list(self):
        self.list_box.delete(0, tk.END)
        for s in self.songs:
            self.list_box.insert(tk.END, f"  {os.path.basename(s)}")

    def on_start_drag(self, event): self.drag_index = self.list_box.nearest(event.y)
    
    def on_drag_motion(self, event):
        target = self.list_box.nearest(event.y)
        if target != self.drag_index:
            item = self.songs.pop(self.drag_index)
            self.songs.insert(target, item)
            self.refresh_list()
            self.drag_index = target
            self.list_box.selection_set(target)

    def remove_song_context(self, event):
        idx = self.list_box.nearest(event.y)
        if 0 <= idx < len(self.songs):
            self.songs.pop(idx)
            self.refresh_list()

    def add_from_main(self):
        # Mengambil pilihan dari playlist_box di MusicController (master.master)
        main_sel = self.master.master.playlist_box.curselection()
        if main_sel:
            for i in main_sel:
                path = self.master.master.playlist[i]
                if path not in self.songs: self.songs.append(path)
            self.refresh_list()

    def save(self):
        self.save_callback(self.playlist_name, self.songs)
        messagebox.showinfo("Sukses", "Playlist updated!")

class PlaylistManager(ctk.CTkToplevel):
    def __init__(self, master, load_callback):
        super().__init__(master)
        self.title("State Tree Playlist Manager")
        self.geometry("400x500")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        icon_path = resource_path("app.ico")
        if os.path.exists(icon_path): 
            self.after(200, lambda: self.iconbitmap(icon_path))
        
        self.load_callback = load_callback
        self.folder = "saved_playlists"
        if not os.path.exists(self.folder): os.makedirs(self.folder)

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="🌳 Playlist Tree", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.list_box = tk.Listbox(self, bg="#1d1e1e", fg="#ffffff", selectbackground="#f39c12", font=("Arial", 11), borderwidth=0)
        self.list_box.pack(pady=10, padx=20, fill="both", expand=True)
        self.list_box.bind("<Double-Button-1>", self.open_editor)

        create_frame = ctk.CTkFrame(self, fg_color="transparent")
        create_frame.pack(pady=5, padx=20, fill="x")
        self.name_entry = ctk.CTkEntry(create_frame, placeholder_text="Nama playlist...")
        self.name_entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(create_frame, text="➕ Create", width=70, command=self.create_new).pack(side="left")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15, fill="x", padx=20)
        ctk.CTkButton(btn_frame, text="📂 LOAD PLAYLIST", fg_color="#2ecc71", command=self.trigger_load).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="🗑 Delete", fg_color="#e74c3c", command=self.delete_playlist).pack(side="left", expand=True, padx=5)

        self.refresh_list()

    def refresh_list(self):
        self.list_box.delete(0, tk.END)
        if os.path.exists(self.folder):
            for f in os.listdir(self.folder):
                if f.endswith(".json"): self.list_box.insert(tk.END, f.replace(".json", ""))

    def create_new(self):
        name = self.name_entry.get().strip()
        if name:
            path = os.path.join(self.folder, f"{name}.json")
            if not os.path.exists(path):
                with open(path, "w") as f: json.dump([], f)
                self.refresh_list()
                self.name_entry.delete(0, tk.END)

    def open_editor(self, event):
        sel = self.list_box.curselection()
        if sel:
            name = self.list_box.get(sel[0])
            path = os.path.join(self.folder, f"{name}.json")
            with open(path, "r") as f: songs = json.load(f)
            PlaylistEditor(self, name, songs, self.save_playlist_data)

    def trigger_load(self):
        sel = self.list_box.curselection()
        if sel:
            name = self.list_box.get(sel[0])
            path = os.path.join(self.folder, f"{name}.json")
            with open(path, "r") as f: songs = json.load(f)
            self.load_callback(songs)

    def save_playlist_data(self, name, songs):
        path = os.path.join(self.folder, f"{name}.json")
        with open(path, "w") as f: json.dump(songs, f)

    def delete_playlist(self):
        sel = self.list_box.curselection()
        if sel:
            name = self.list_box.get(sel[0])
            if messagebox.askyesno("Konfirmasi", f"Hapus playlist '{name}'?"):
                os.remove(os.path.join(self.folder, f"{name}.json"))
                self.refresh_list()

    def destroy(self):
        gc.collect()
        super().destroy()