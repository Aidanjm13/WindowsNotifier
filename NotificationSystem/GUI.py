import tkinter as tk
from tkinter import ttk, messagebox
import threading
from filehandling import create_file, get_entries, get_next_id, add_entry, update_entry, delete_entry
import random
import notifier
import time

# ── Background loop ───────────────────────────────────────────────────────────

def run_loop(app, stop_event, log_fn, interval, range_val, randomized_order, sound,
             width, height, allowed_positions, duration_ms):
    count = 0
    entries = get_entries()
    if randomized_order:
        random.shuffle(entries)
    log_fn(f"Settings — interval={interval}, range={range_val}, randomized={randomized_order}, sound={sound}")
    while not stop_event.is_set():
        log_fn(f"Loop tick {count}")
        wait = random.uniform(interval - range_val, interval + range_val)
        time.sleep(wait)
        entry = entries[count % len(entries)]
        position = random.choice(allowed_positions)

        app.after(0, app.show_entry_window, entry, sound, width, height, position, duration_ms)

        count += 1
    log_fn("Loop stopped.")

# ── GUI ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Notification System")
        self.geometry("820x700")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        self.stop_event = None
        self.loop_thread = None

        self.selected_positions = {
            "top-left": True, "top": True, "top-right": True,
            "left": True, "center": False, "right": True,
            "bottom-left": True, "bottom": True, "bottom-right": True,
        }

        create_file()
        self._build_ui()
        self._refresh_list()

    #creates base UI design
    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        #base style
        style.configure("Treeview",
                        background="#2a2a3e", foreground="#cdd6f4",
                        fieldbackground="#2a2a3e", rowheight=26)
        #header style
        style.configure("Treeview.Heading",
                        background="#313244", foreground="#cba6f7", font=("Segoe UI", 9, "bold"))
        
        #when selected switch to this color
        style.map("Treeview", background=[("selected", "#45475a")])


        #left side of application: the scroll view with notifications
        left = tk.Frame(self, bg="#1e1e2e") #frame color same as background to blend in
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)

        tk.Label(left, text="Notifications", bg="#1e1e2e", fg="#cba6f7",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        cols = ("App Name", "Title", "Content")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for col, w in zip(cols, (40, 40, 160)):
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btn_row = tk.Frame(left, bg="#1e1e2e")
        btn_row.pack(fill="x", pady=(6, 0))
        self._btn(btn_row, "New", self._new_entry).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "Delete", self._delete_entry, danger=True).pack(side="left")


        #right side notification edits, loop settings and controls
        right = tk.Frame(self, bg="#1e1e2e", width=240)
        right.pack(side="right", fill="y", padx=(6, 12), pady=12)
        right.pack_propagate(False)

        # Entry fields (saved to CSV)
        tk.Label(right, text="Edit Notification", bg="#1e1e2e", fg="#cba6f7",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.entry_vars = {}
        self._field(right, self.entry_vars, "appname",   "App Name",   "str")
        self._field(right, self.entry_vars, "title",   "Title",   "str")
        self._field(right, self.entry_vars, "content", "Content", "text")
        self._btn(right, "Save Entry", self._save_entry).pack(fill="x", pady=(8, 0))

        # Divider
        tk.Frame(right, bg="#45475a", height=1).pack(fill="x", pady=10)

        # Loop settings (not saved to CSV)
        tk.Label(right, text="Loop Settings", bg="#1e1e2e", fg="#cba6f7",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.loop_vars = {}
        self._field(right,self.loop_vars,"interval","Interval between Notifications","int","20")
        self._field(right,self.loop_vars,"range","Random Range","int","0")

        self._field(right,self.loop_vars,"length","Display Time","int","3")
        self._field(right,self.loop_vars,"height","Display Height (pixels)","int","120")
        self._field(right,self.loop_vars,"width","Display Width (pixels)","int","320")

        self._field(right, self.loop_vars,"randomized_order","Randomized Entry Order", "bool")
        self._field(right, self.loop_vars,"sound","Plays Notification Sound","bool")

        self._field(right, self.loop_vars,"location","Configure Location Options","button","Show")

        # Divider
        tk.Frame(right, bg="#45475a", height=1).pack(fill="x", pady=10)

        # Start / Stop
        ctrl = tk.Frame(right, bg="#1e1e2e")
        ctrl.pack(fill="x", pady=(0, 8))
        self.start_btn = self._btn(ctrl, "▶  Start", self._start_loop, accent=True)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.stop_btn = self._btn(ctrl, "■  Stop", self._stop_loop, danger=True)
        self.stop_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn.configure(state="disabled")

        # Log
        tk.Label(right, text="Log", bg="#1e1e2e", fg="#cba6f7",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.log_box = tk.Text(right, height=6, bg="#2a2a3e", fg="#a6e3a1",
                               font=("Consolas", 8), state="disabled",
                               relief="flat", bd=0)
        self.log_box.pack(fill="both", expand=True)

        self._selected_id = None

    #defines row input fields for options
    def _field(self, parent, var_dict, field, label, kind, set_val = "0"):
        row = tk.Frame(parent, bg="#1e1e2e")
        row.pack(fill="x", pady=(8,2))

        tk.Label(row, text=label, bg="#1e1e2e", fg="#a6adc8",
                 font=("Segoe UI", 8)).pack(side="left")

        if kind == "bool":
            var = tk.BooleanVar()
            tk.Checkbutton(row, variable=var, bg="#1e1e2e",
                           activebackground="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", relief="flat").pack(side="right")
            var_dict[field] = var

        elif kind == "text":
            widget = tk.Text(row, height=3, bg="#2a2a3e", fg="#cdd6f4",
                             insertbackground="#cdd6f4", relief="flat",
                             font=("Segoe UI", 9), bd=4, width=28)
            widget.pack(side="right")
            var_dict[field] = widget

        elif kind == "int":
            var = tk.StringVar(value = set_val)
            vcmd = (self.register(self._int_only), "%P")
            tk.Entry(row, textvariable=var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="#cdd6f4", relief="flat",
                     font=("Segoe UI", 9), bd=4,
                     validate="key", validatecommand=vcmd, width="4").pack(side="right")
            var_dict[field] = var
        
        elif kind == "button":
            self._btn(row, set_val, lambda: self._on_button_click(field)).pack(side="right")
            var_dict[field] = None

        else:
            var = tk.StringVar()
            tk.Entry(row, textvariable=var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="#cdd6f4", relief="flat",
                     font=("Segoe UI", 9), bd=4, width=28).pack(side="right")
            var_dict[field] = var

    def _int_only(self, value):
        return value == "" or value.lstrip("-").isdigit()

    def _btn(self, parent, text, cmd, danger=False, accent=False):
        if danger:
            bg, fg, abg = "#f38ba8", "#1e1e2e", "#e06c75"
        elif accent:
            bg, fg, abg = "#a6e3a1", "#1e1e2e", "#89dceb"
        else:
            bg, fg, abg = "#313244", "#cdd6f4", "#45475a"
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg, activebackground=abg,
                         relief="flat", font=("Segoe UI", 9), padx=8, pady=4)

    #Functions for handling list features

    #refresh all rows in the list based on saved file, store ids in iid
    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for e in get_entries():
            self.tree.insert("", "end", iid=str(e["id"]),
                             values=(e["appName"], e["title"], e["content"]))

    #what happens when you select a row
    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        self._selected_id = sel[0]
        entry = next((e for e in get_entries() if e["id"] == self._selected_id), None)
        if not entry:
            return
        self.entry_vars["appname"].set(entry["appName"])
        self.entry_vars["title"].set(entry["title"])
        content_widget = self.entry_vars["content"]
        content_widget.delete("1.0", "end")
        content_widget.insert("1.0", entry["content"])

    # List CRUD
    def _new_entry(self):
        next_id = get_next_id()
        add_entry("AppName", "Title", "Content")
        self._refresh_list()
        self.tree.selection_set(str(next_id))
        self._on_select(None)

    def _save_entry(self):
        if self._selected_id is None:
            messagebox.showwarning("No selection", "Select an entry to save.")
            return
        appname = self.entry_vars["appname"].get().strip()
        title = self.entry_vars["title"].get().strip()
        content = self.entry_vars["content"].get("1.0", "end").strip()
        update_entry(self._selected_id, appname, title, content)
        self._refresh_list()
        self.tree.selection_set(str(self._selected_id))

    def _delete_entry(self):
        if self._selected_id is None:
            messagebox.showwarning("No selection", "Select an entry to delete.")
            return
        if not messagebox.askyesno("Delete", "Delete this entry?"):
            return
        delete_entry(self._selected_id)
        self._selected_id = None
        self._refresh_list()


    def _on_button_click(self, field):
        if field == "location":
            self._open_location_picker()
        elif field == "color":
            self._open_color_picker()

    def _open_location_picker(self):
        popup = tk.Toplevel(self)
        popup.title("Popup Positions")
        popup.geometry("260x300")
        popup.configure(bg="#1e1e2e")
        popup.transient(self)
        popup.grab_set()  # modal — user must close this before returning to main window

        tk.Label(popup, text="Select allowed popup positions",
                bg="#1e1e2e", fg="#cba6f7", font=("Segoe UI", 10, "bold")).pack(pady=(10, 6))

        # Layout positions in a 3x3 grid matching their real screen locations
        grid_frame = tk.Frame(popup, bg="#1e1e2e")
        grid_frame.pack(pady=6)

        layout = [
            ["top-left", "top", "top-right"],
            ["left", "center", "right"],
            ["bottom-left", "bottom", "bottom-right"],
        ]

        self._location_vars = {}
        for r, row in enumerate(layout):
            for c, pos in enumerate(row):
                var = tk.BooleanVar(value=self.selected_positions.get(pos, False))
                self._location_vars[pos] = var
                cb = tk.Checkbutton(
                    grid_frame, text=pos, variable=var,
                    bg="#2a2a3e", fg="#cdd6f4", selectcolor="#313244",
                    activebackground="#2a2a3e", activeforeground="#cdd6f4",
                    relief="flat", font=("Segoe UI", 8), width=10, anchor="w"
                )
                cb.grid(row=r, column=c, padx=3, pady=3)

        def save_and_close():
            # Persist checkbox states back into self.selected_positions
            for pos, var in self._location_vars.items():
                self.selected_positions[pos] = var.get()

            if not any(self.selected_positions.values()):
                messagebox.showwarning("No positions selected",
                                        "Select at least one position, defaulting to center.")
                self.selected_positions["center"] = True

            popup.destroy()

        self._btn(popup, "Save", save_and_close, accent=True).pack(pady=(12, 10))

    #running notification loop
    def _log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _start_loop(self):
        if self.loop_thread and self.loop_thread.is_alive():
            return
        try:
            interval = int(self.loop_vars["interval"].get())
            range_val = int(self.loop_vars["range"].get())
            window_width = int(self.loop_vars["width"].get())
            window_height = int(self.loop_vars["height"].get())
            duration_ms = int(self.loop_vars["length"].get()) * 1000
        except ValueError:
            messagebox.showerror("Invalid input", "Interval, Range, Width, Height, and Display Time must be integers.")
            return
        randomized_order = self.loop_vars["randomized_order"].get()
        sound = self.loop_vars["sound"].get()

        allowed_positions = [pos for pos, enabled in self.selected_positions.items() if enabled]
        if not allowed_positions:
            allowed_positions = ["center"]

        self.stop_event = threading.Event()
        self.loop_thread = threading.Thread(
            target=run_loop,
            args=(self, self.stop_event, self._log, interval, range_val,
                randomized_order, sound, window_width, window_height,
                allowed_positions, duration_ms),
            daemon=True)
        self.loop_thread.start()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._log("Loop started.")

    def _stop_loop(self):
        if self.stop_event:
            self.stop_event.set()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def show_entry_window(self, entry, sound, width=320, height=120, position="bottom-right", duration_ms=4000):
        """Runs on the main thread — safe to touch widgets here."""
        win = tk.Toplevel(self)

        # Remove the title bar / border entirely (no close button, no drag bar)
        win.overrideredirect(True)

        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()

        positions = {
            "top-left":      (0, 0),
            "top-right":     (screen_width - width, 0),
            "bottom-left":   (0, screen_height - height),
            "bottom-right":  (screen_width - width, screen_height - height),
            "top":           ((screen_width - width) // 2, 0),
            "bottom":        ((screen_width - width) // 2, screen_height - height),
            "left":          (0, (screen_height - height) // 2),
            "right":         (screen_width - width, (screen_height - height) // 2),
            "center":        ((screen_width - width) // 2, (screen_height - height) // 2),
        }
        x, y = positions.get(position, (0, 0))
        win.geometry(f"{width}x{height}+{x}+{y}")

        # ── Notification-style layout ──────────────────────────────────────
        bg = "#2b2b2b"       # Windows 10/11 dark-mode toast background
        fg_title = "#ffffff"
        fg_app = "#a0a0a0"
        fg_content = "#d0d0d0"

        win.configure(bg=bg)

        outer = tk.Frame(win, bg=bg, highlightbackground="#454545",
                        highlightthickness=1, bd=0)
        outer.pack(fill="both", expand=True)

        padding = tk.Frame(outer, bg=bg)
        padding.pack(fill="both", expand=True, padx=12, pady=10)

        # App name — pushed to the top right
        app_name = entry.get("appName", "Notification")
        tk.Label(padding, text=app_name, bg=bg, fg=fg_app,
                font=("Segoe UI", 8)).pack(anchor="e")

        # Title — bold, left aligned
        tk.Label(padding, text=entry["title"], bg=bg, fg=fg_title,
                font=("Segoe UI", 10, "bold"), anchor="w", justify="left",
                wraplength=width - 30).pack(anchor="w", pady=(4, 2), fill="x")

        # Content — normal weight, left aligned
        tk.Label(padding, text=entry["content"], bg=bg, fg=fg_content,
                font=("Segoe UI", 9), anchor="w", justify="left",
                wraplength=width - 30).pack(anchor="w", fill="x")

        # ── Topmost handling ─────────────────────────────────────────────
        win.attributes("-topmost", True)
        win.lift()
        win.after(duration_ms, win.destroy)


if __name__ == "__main__":
    App().mainloop()