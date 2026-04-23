import shlex
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from copy import deepcopy

PRESETS = [
    "full",
    "left-half", "right-half", "top-half", "bottom-half",
    "top-left", "top-right", "bottom-left", "bottom-right",
    "left-third", "center-third", "right-third",
    "left-two-thirds", "right-two-thirds",
]

# ------------------------------------------------------------------ #
#  Theme                                                               #
# ------------------------------------------------------------------ #

BG       = "#1e1e1e"
BG2      = "#262626"
BG3      = "#303030"
ACCENT   = "#00b4d8"
ACCENT2  = "#0077a8"
FG       = "#e8e8e8"
FG2      = "#a0a0a0"
RED      = "#e05555"
GREEN    = "#4caf7d"
BORDER   = "#383838"
FONT     = ("Segoe UI", 10)
FONT_SM  = ("Segoe UI", 9)
FONT_B   = ("Segoe UI", 10, "bold")
FONT_H   = ("Segoe UI", 14, "bold")
FONT_H2  = ("Segoe UI", 12, "bold")


def apply_theme(root: tk.Tk):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",            background=BG,  foreground=FG,  font=FONT,  borderwidth=0)
    style.configure("TFrame",       background=BG)
    style.configure("TLabel",       background=BG,  foreground=FG,  font=FONT)
    style.configure("TLabelframe",  background=BG,  foreground=FG2, font=FONT_SM)
    style.configure("TLabelframe.Label", background=BG, foreground=FG2, font=FONT_SM)
    style.configure("TEntry",       fieldbackground=BG3, foreground=FG, insertcolor=FG, borderwidth=1, relief="flat")
    style.map("TEntry",             fieldbackground=[("focus", BG3)])

    style.configure("TButton",      background=BG3, foreground=FG,  relief="flat", padding=(10, 5))
    style.map("TButton",            background=[("active", BORDER), ("pressed", BORDER)])

    style.configure("Accent.TButton", background=ACCENT, foreground="#000", font=FONT_B, relief="flat", padding=(12, 6))
    style.map("Accent.TButton",     background=[("active", ACCENT2), ("pressed", ACCENT2)])

    style.configure("Danger.TButton", background=RED, foreground="#fff", font=FONT_B, relief="flat", padding=(10, 5))
    style.map("Danger.TButton",     background=[("active", "#b03030"), ("pressed", "#b03030")])

    style.configure("Treeview",
        background=BG2, foreground=FG, fieldbackground=BG2,
        rowheight=28, font=FONT_SM, borderwidth=0)
    style.configure("Treeview.Heading",
        background=BG3, foreground=FG2, font=FONT_SM, relief="flat")
    style.map("Treeview",
        background=[("selected", ACCENT2)],
        foreground=[("selected", "#fff")])

    style.configure("TScrollbar",   background=BG3, troughcolor=BG, arrowcolor=FG2,
                    borderwidth=0, relief="flat")
    style.map("TScrollbar",         background=[("active", BORDER)])

    style.configure("TCombobox",    fieldbackground=BG3, background=BG3, foreground=FG,
                    arrowcolor=FG2, borderwidth=1, relief="flat")
    style.map("TCombobox",          fieldbackground=[("readonly", BG3)],
                                    selectbackground=[("readonly", BG3)],
                                    selectforeground=[("readonly", FG)])


# ------------------------------------------------------------------ #
#  Helper widgets                                                      #
# ------------------------------------------------------------------ #

def labeled_entry(parent, label: str, row: int, default: str = "") -> tk.StringVar:
    tk.Label(parent, text=label, bg=BG, fg=FG2, font=FONT_SM).grid(
        row=row, column=0, sticky="w", padx=(0, 12), pady=4)
    var = tk.StringVar(value=default)
    ttk.Entry(parent, textvariable=var, width=40).grid(row=row, column=1, sticky="ew", pady=4)
    return var


def dark_text(parent, height=3, width=40) -> tk.Text:
    return tk.Text(parent, height=height, width=width,
                   bg=BG3, fg=FG, insertbackground=FG,
                   font=FONT_SM, relief="flat", padx=8, pady=6,
                   wrap="word", highlightthickness=1,
                   highlightbackground=BORDER, highlightcolor=ACCENT)


def icon_btn(parent, text, command, style="TButton", width=None):
    kw = {"text": text, "command": command, "style": style}
    if width:
        kw["width"] = width
    return ttk.Button(parent, **kw)


def card_frame(parent, **pack_kw) -> tk.Frame:
    f = tk.Frame(parent, bg=BG2, padx=16, pady=12)
    if pack_kw:
        f.pack(**pack_kw)
    return f


def section_heading(parent, text: str):
    tk.Label(parent, text=text, bg=BG, fg=FG, font=FONT_H).pack(anchor="w", pady=(0, 8))


# ------------------------------------------------------------------ #
#  App edit dialog                                                     #
# ------------------------------------------------------------------ #

class AppDialog(tk.Toplevel):
    def __init__(self, parent, app_data: dict | None = None):
        super().__init__(parent)
        self.result: dict | None = None
        self.data = deepcopy(app_data) if app_data else {}

        self.title("Edit App" if app_data else "Add App")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        # ---- fields ----
        fields = tk.Frame(self, bg=BG)
        fields.pack(fill="x", padx=24, pady=(20, 0))
        fields.columnconfigure(1, weight=1)

        self.v_name  = labeled_entry(fields, "Display name", 0, self.data.get("name", ""))
        self.v_delay = labeled_entry(fields, "Delay (s)",    2, str(self.data.get("delay", 0)))

        # Path row with Browse button
        tk.Label(fields, text="Executable path", bg=BG, fg=FG2, font=FONT_SM).grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=4)
        path_frame = tk.Frame(fields, bg=BG)
        path_frame.grid(row=1, column=1, sticky="ew", pady=4)
        path_frame.columnconfigure(0, weight=1)
        self.v_path = tk.StringVar(value=self.data.get("path", ""))
        ttk.Entry(path_frame, textvariable=self.v_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(path_frame, text="Browse…", command=self._browse, width=9).grid(
            row=0, column=1, padx=(6, 0))

        self.v_args = labeled_entry(fields, "Arguments", 3,
                                    " ".join(str(a) for a in self.data.get("args", [])))

        # Monitor
        tk.Label(fields, text="Monitor", bg=BG, fg=FG2, font=FONT_SM).grid(
            row=4, column=0, sticky="w", padx=(0, 12), pady=4)
        mon_frame = tk.Frame(fields, bg=BG)
        mon_frame.grid(row=4, column=1, sticky="w", pady=4)
        window = self.data.get("window", {})
        self.v_monitor = tk.StringVar(value=str(window.get("monitor", 0)))
        ttk.Spinbox(mon_frame, textvariable=self.v_monitor,
                    from_=0, to=5, width=4,
                    background=BG3, foreground=FG).pack(side="left")
        tk.Label(mon_frame, text="  (0 = primary, 1 = secondary, …)",
                 bg=BG, fg=FG2, font=FONT_SM).pack(side="left")

        # Preset
        tk.Label(fields, text="Window preset", bg=BG, fg=FG2, font=FONT_SM).grid(
            row=5, column=0, sticky="w", padx=(0, 12), pady=4)
        preset_frame = tk.Frame(fields, bg=BG)
        preset_frame.grid(row=5, column=1, sticky="w", pady=4)
        self.v_preset = tk.StringVar(value=window.get("preset", "full"))
        ttk.Combobox(preset_frame, textvariable=self.v_preset,
                     values=PRESETS, state="readonly", width=22).pack(side="left")
        self.v_maximize = tk.BooleanVar(value=window.get("maximize", False))
        tk.Checkbutton(preset_frame, text=" Maximize",
                       variable=self.v_maximize,
                       bg=BG, fg=FG, selectcolor=BG3,
                       activebackground=BG, activeforeground=FG,
                       font=FONT_SM).pack(side="left", padx=(12, 0))

        # ---- buttons ----
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=24, pady=(16, 20))
        icon_btn(btn_row, "Cancel", self.destroy).pack(side="right", padx=(6, 0))
        icon_btn(btn_row, "Save app", self._save, style="Accent.TButton").pack(side="right")

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 60, parent.winfo_rooty() + 60))

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select executable",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.v_path.set(path)

    def _save(self):
        name = self.v_name.get().strip()
        path = self.v_path.get().strip()
        if not name or not path:
            messagebox.showwarning("Missing fields", "Name and path are required.", parent=self)
            return
        try:
            delay = float(self.v_delay.get().strip() or "0")
        except ValueError:
            messagebox.showwarning("Invalid", "Delay must be a number.", parent=self)
            return

        args_raw = self.v_args.get().strip()
        args = shlex.split(args_raw) if args_raw else []

        self.result = {
            "name": name,
            "path": path,
            "args": args,
            "delay": delay,
            "window": {
                "monitor": int(self.v_monitor.get()),
                "preset": self.v_preset.get(),
                "maximize": self.v_maximize.get(),
            }
        }
        # Preserve browser block — advanced dialog doesn't edit it but must not drop it.
        if "browser" in self.data:
            self.result["browser"] = deepcopy(self.data["browser"])
        self.destroy()
