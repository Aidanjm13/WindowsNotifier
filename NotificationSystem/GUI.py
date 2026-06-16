import tkinter as tk
from tkinter import ttk, messagebox
import threading
from filehandling import create_file, get_entries, get_next_id, add_entry, update_entry, delete_entry
import random
import notifier
import time

# ── Background loop ───────────────────────────────────────────────────────────

def run_loop(stop_event, log_fn, interval, range_val, randomized_order, sound):
    
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
        notifier.show_notification(entry["title"], entry["content"], silent=not sound)
        count += 1
    log_fn("Loop stopped.")

# ── GUI ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Notification System")
        self.geometry("820x560")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        self.stop_event = None
        self.loop_thread = None

        create_file()
        self._build_ui()
        self._refresh_list()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#2a2a3e", foreground="#cdd6f4",
                        fieldbackground="#2a2a3e", rowheight=26)
        style.configure("Treeview.Heading",
                        background="#313244", foreground="#cba6f7", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#45475a")])

        # Left panel — list
        left = tk.Frame(self, bg="#1e1e2e")
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)

        tk.Label(left, text="Notifications", bg="#1e1e2e", fg="#cba6f7",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        cols = ("id", "title", "content")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for col, w in zip(cols, (40, 180, 300)):
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btn_row = tk.Frame(left, bg="#1e1e2e")
        btn_row.pack(fill="x", pady=(6, 0))
        self._btn(btn_row, "New", self._new_entry).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "Delete", self._delete_entry, danger=True).pack(side="left")

        # Right panel — entry form + loop settings + controls
        right = tk.Frame(self, bg="#1e1e2e", width=240)
        right.pack(side="right", fill="y", padx=(6, 12), pady=12)
        right.pack_propagate(False)

        # Entry fields (saved to CSV)
        tk.Label(right, text="Edit Notification", bg="#1e1e2e", fg="#cba6f7",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.entry_vars = {}
        self._field(right, self.entry_vars, "title",   "Title",   "str")
        self._field(right, self.entry_vars, "content", "Content", "text")
        self._btn(right, "Save Entry", self._save_entry).pack(fill="x", pady=(8, 0))

        # Divider
        tk.Frame(right, bg="#45475a", height=1).pack(fill="x", pady=10)

        # Loop settings (not saved to CSV)
        tk.Label(right, text="Loop Settings", bg="#1e1e2e", fg="#cba6f7",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.loop_vars = {}
        self._field(right, self.loop_vars, "interval",         "Interval (Time Between Entries)",   "interval")
        self._field(right, self.loop_vars, "range",            "Range (Randomized Interval Deviation)",      "range")

        self._field(right, self.loop_vars, "randomized_order", "Randomized Entry Order", "bool")
        self._field(right, self.loop_vars, "sound",            "Plays Notification Sound",            "bool")

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

    def _field(self, parent, var_dict, field, label, kind):
        tk.Label(parent, text=label, bg="#1e1e2e", fg="#a6adc8",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 1))

        if kind == "bool":
            var = tk.BooleanVar()
            tk.Checkbutton(parent, variable=var, bg="#1e1e2e",
                           activebackground="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", relief="flat").pack(anchor="w")
            var_dict[field] = var

        elif kind == "text":
            widget = tk.Text(parent, height=3, bg="#2a2a3e", fg="#cdd6f4",
                             insertbackground="#cdd6f4", relief="flat",
                             font=("Segoe UI", 9), bd=4)
            widget.pack(fill="x")
            var_dict[field] = widget

        elif kind == "interval":
            var = tk.StringVar(value = "30")
            vcmd = (self.register(self._int_only), "%P")
            tk.Entry(parent, textvariable=var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="#cdd6f4", relief="flat",
                     font=("Segoe UI", 9), bd=4,
                     validate="key", validatecommand=vcmd).pack(fill="x")
            var_dict[field] = var

        elif kind == "range":
            var = tk.StringVar(value = "0")
            vcmd = (self.register(self._int_only), "%P")
            tk.Entry(parent, textvariable=var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="#cdd6f4", relief="flat",
                     font=("Segoe UI", 9), bd=4,
                     validate="key", validatecommand=vcmd).pack(fill="x")
            var_dict[field] = var

        else:
            var = tk.StringVar()
            tk.Entry(parent, textvariable=var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="#cdd6f4", relief="flat",
                     font=("Segoe UI", 9), bd=4).pack(fill="x")
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

    # ── List ──────────────────────────────────────────────────────────────────

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for e in get_entries():
            self.tree.insert("", "end", iid=str(e["id"]),
                             values=(e["id"], e["title"], e["content"]))

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        self._selected_id = int(sel[0])
        entry = next((e for e in get_entries() if e["id"] == self._selected_id), None)
        if not entry:
            return
        self.entry_vars["title"].set(entry["title"])
        content_widget = self.entry_vars["content"]
        content_widget.delete("1.0", "end")
        content_widget.insert("1.0", entry["content"])

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def _new_entry(self):
        next_id = get_next_id()
        add_entry("New Entry", "")
        self._refresh_list()
        self.tree.selection_set(str(next_id))
        self._on_select(None)

    def _save_entry(self):
        if self._selected_id is None:
            messagebox.showwarning("No selection", "Select an entry to save.")
            return
        title = self.entry_vars["title"].get().strip()
        content = self.entry_vars["content"].get("1.0", "end").strip()
        update_entry(self._selected_id, title, content)
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

    # ── Loop ─────────────────────────────────────────────────────────────────

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
        except ValueError:
            messagebox.showerror("Invalid input", "Interval and Range must be integers.")
            return
        randomized_order = self.loop_vars["randomized_order"].get()
        sound = self.loop_vars["sound"].get()

        self.stop_event = threading.Event()
        self.loop_thread = threading.Thread(
            target=run_loop,
            args=(self.stop_event, self._log, interval, range_val, randomized_order, sound),
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


if __name__ == "__main__":
    App().mainloop()