import os, gc
import tkinter as tk
import customtkinter as ctk

class QueueWindow(ctk.CTkToplevel):
    def __init__(self, master, queue_list, remove_callback, current_song):
        super().__init__(master)
        self.title("Play Queue")
        self.geometry("400x520")
        self.attributes("-topmost", True)
        
        try:
            from main import resource_path
            icon_path = resource_path("app.ico")
            if os.path.exists(icon_path): self.after(200, lambda: self.iconbitmap(icon_path))
        except: pass

        self.queue_list = queue_list
        self.remove_callback = remove_callback
        self.current_song = current_song

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="🎵 Music Queue", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.q_box = tk.Listbox(
            self, bg="#1d1e1e", fg="#ffffff", 
            selectbackground="#2ecc71", selectforeground="#000000",
            highlightthickness=0, font=("Arial", 11), borderwidth=0
        )
        self.q_box.pack(pady=5, padx=20, fill="both", expand=True)
        
        self.q_box.bind('<Button-1>', self.on_start_drag)
        self.q_box.bind('<B1-Motion>', self.on_drag_motion)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15, fill="x", padx=20)
        
        ctk.CTkButton(btn_frame, text="🗑 Remove", fg_color="#e74c3c", width=100, command=self.remove_item).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🧹 Clear", fg_color="#333", width=100, command=self.clear_all).pack(side="left", padx=5)
        
        self.update_list(self.current_song)

    def update_list(self, current_song):
        self.current_song = current_song
        self.q_box.delete(0, tk.END)
        
        self.q_box.insert(tk.END, f" ▶ {os.path.basename(self.current_song)} (Playing)")
        self.q_box.itemconfig(0, fg="#2ecc71")

        for path in self.queue_list:
            self.q_box.insert(tk.END, f"   {os.path.basename(path)}")

    def on_start_drag(self, event):
        idx = self.q_box.nearest(event.y)
        if idx == 0:
            self.drag_index = None
        else:
            self.drag_index = idx

    def on_drag_motion(self, event):
        if self.drag_index is None: return
        
        target_index = self.q_box.nearest(event.y)
        
        if target_index == 0: target_index = 1
        
        if target_index != self.drag_index:
            item = self.queue_list.pop(self.drag_index - 1)
            self.queue_list.insert(target_index - 1, item)
            
            self.update_list(self.current_song)
            self.drag_index = target_index
            self.q_box.selection_set(target_index)

    def remove_item(self):
        sel = self.q_box.curselection()
        if sel and sel[0] != 0:
            self.remove_callback(sel[0] - 1)
            self.update_list(self.current_song)

    def clear_all(self):
        self.queue_list.clear()
        self.update_list(self.current_song)

    def destroy(self):
        gc.collect()
        super().destroy()