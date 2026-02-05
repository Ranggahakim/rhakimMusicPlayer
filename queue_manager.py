import os, gc
import tkinter as tk
import customtkinter as ctk

class QueueWindow(ctk.CTkToplevel):
    def __init__(self, master, queue_list, remove_callback):
        super().__init__(master)
        self.title("Play Queue - Drag to Reorder")
        self.geometry("400x520")
        self.attributes("-topmost", True)
        self.queue_list = queue_list
        self.remove_callback = remove_callback

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="🎵 Music Queue", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(self, text="Tip: Klik & geser untuk urutkan", font=("Arial", 10), text_color="gray").pack()
        
        # Listbox Setup
        self.q_box = tk.Listbox(
            self, bg="#1d1e1e", fg="#ffffff", 
            selectbackground="#2ecc71", selectforeground="#000000",
            highlightthickness=0, font=("Arial", 11), borderwidth=0
        )
        self.q_box.pack(pady=5, padx=20, fill="both", expand=True)
        
        # --- BINDING DRAG & DROP ---
        self.q_box.bind('<Button-1>', self.on_start_drag)
        self.q_box.bind('<B1-Motion>', self.on_drag_motion)

        # Controls
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15, fill="x", padx=20)
        
        ctk.CTkButton(btn_frame, text="🗑 Remove", fg_color="#e74c3c", width=100, command=self.remove_item).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🧹 Clear", fg_color="#333", width=100, command=self.clear_all).pack(side="left", padx=5)
        
        self.update_list()

    def update_list(self):
        self.q_box.delete(0, tk.END)
        for path in self.queue_list:
            self.q_box.insert(tk.END, f"  {os.path.basename(path)}")

    # --- LOGIKA DRAG & DROP ---
    def on_start_drag(self, event):
        # Ambil index awal saat mouse ditekan
        self.drag_index = self.q_box.nearest(event.y)

    def on_drag_motion(self, event):
        # Ambil index target saat mouse digeser
        target_index = self.q_box.nearest(event.y)
        
        if target_index != self.drag_index:
            # 1. Geser di List Data (self.queue_list)
            # Karena ini reference ke self.queue di main.py, datanya otomatis sinkron!
            item = self.queue_list.pop(self.drag_index)
            self.queue_list.insert(target_index, item)
            
            # 2. Update tampilan visual Listbox
            self.update_list()
            
            # 3. Tetap pilih item yang sedang digeser
            self.drag_index = target_index
            self.q_box.selection_clear(0, tk.END)
            self.q_box.selection_set(target_index)

    def remove_item(self):
        sel = self.q_box.curselection()
        if sel:
            self.remove_callback(sel[0])
            self.update_list()

    def clear_all(self):
        while len(self.queue_list) > 0:
            self.remove_callback(0)
        self.update_list()

    def destroy(self):
        gc.collect()
        super().destroy()