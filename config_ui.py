"""
WakeUp Config UI — Visual editor for profiles.json
Run with: python config_ui.py
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from copy import deepcopy

CONFIG_PATH = Path(__file__).parent / "profiles.json"

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


# ------------------------------------------------------------------ #
#  View constants                                                      #
# ------------------------------------------------------------------ #

VIEW_HOME            = "home"
VIEW_NEW_MODE_CHOICE = "new_mode_choice"
VIEW_CAPTURE         = "capture"
VIEW_REVIEW          = "review"
VIEW_MODE_DETAIL     = "mode_detail"
VIEW_ADVANCED        = "advanced"


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
    e = ttk.Entry(parent, textvariable=var, width=40)
    e.grid(row=row, column=1, sticky="ew", pady=4)
    return var


def section_label(parent, text: str):
    tk.Label(parent, text=text, bg=BG, fg=FG2, font=FONT_SM).pack(anchor="w", pady=(10, 2))


def dark_text(parent, height=3, width=40) -> tk.Text:
    t = tk.Text(parent, height=height, width=width,
                bg=BG3, fg=FG, insertbackground=FG,
                font=FONT_SM, relief="flat", padx=8, pady=6,
                wrap="word", bd=1, highlightthickness=1,
                highlightbackground=BORDER, highlightcolor=ACCENT)
    return t


def icon_btn(parent, text, command, style="TButton", width=None):
    kw = {"text": text, "command": command, "style": style}
    if width:
        kw["width"] = width
    return ttk.Button(parent, **kw)


def card_frame(parent, **pack_kw) -> tk.Frame:
    """Styled card panel. Caller can pass pack kwargs."""
    f = tk.Frame(parent, bg=BG2, padx=16, pady=12)
    if pack_kw:
        f.pack(**pack_kw)
    return f


def section_heading(parent, text: str):
    """Large heading label for screen sections."""
    tk.Label(parent, text=text, bg=BG, fg=FG, font=FONT_H).pack(anchor="w", pady=(0, 8))


# ------------------------------------------------------------------ #
#  App edit dialog                                                     #
# ------------------------------------------------------------------ #

class AppDialog(tk.Toplevel):
    """Dialog for adding/editing a single app entry."""

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

        self.v_name    = labeled_entry(fields, "Display name",  0, self.data.get("name", ""))
        self.v_delay   = labeled_entry(fields, "Delay (s)",     2, str(self.data.get("delay", 0)))

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

        self.v_args    = labeled_entry(fields, "Arguments",     3,
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
        cb = ttk.Combobox(preset_frame, textvariable=self.v_preset,
                          values=PRESETS, state="readonly", width=22)
        cb.pack(side="left")
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
        args = args_raw.split() if args_raw else []

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
        self.destroy()


# ------------------------------------------------------------------ #
#  Main window                                                         #
# ------------------------------------------------------------------ #

class WakeUpConfigUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WakeUp — Config Editor")
        self.geometry("1060x720")
        self.minsize(860, 540)
        apply_theme(self)

        self.config_data: dict = {}
        self.profiles: dict   = {}
        self._dirty = False
        self._current_profile: str | None = None
        self._current_view: str = VIEW_HOME
        self._draft_apps: list[dict] | None = None

        self._build_ui()
        self._load()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------- #
    #  UI construction                                                   #
    # ---------------------------------------------------------------- #

    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────────
        topbar = tk.Frame(self, bg=BG2, height=52)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="WakeUp", bg=BG2, fg=FG,
                 font=FONT_H).pack(side="left", padx=(20, 4))
        tk.Label(topbar, text="Config Editor", bg=BG2, fg=FG2,
                 font=FONT).pack(side="left")

        self._unsaved_chip = tk.Label(topbar, text="● unsaved", bg=BG2,
                                      fg="#e8a838", font=FONT_SM)

        self.save_btn = icon_btn(topbar, "💾  Save", self._save, style="Accent.TButton")
        self.save_btn.pack(side="right", padx=12, pady=10)

        tk.Frame(topbar, bg=BORDER, width=1).pack(side="right", fill="y", pady=8)

        # ── main area ────────────────────────────────────────────────
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)

        # Left sidebar — mode list
        left = tk.Frame(main, bg=BG2, width=220)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="MODES", bg=BG2, fg=FG2,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(14, 6))

        list_frame = tk.Frame(left, bg=BG2)
        list_frame.pack(fill="both", expand=True, padx=6)

        self.profile_list = tk.Listbox(
            list_frame, bg=BG2, fg=FG, selectbackground=ACCENT2,
            selectforeground="#fff", relief="flat", bd=0,
            font=FONT, activestyle="none", highlightthickness=0,
            cursor="hand2")
        self.profile_list.pack(fill="both", expand=True)
        self.profile_list.bind("<<ListboxSelect>>", self._on_profile_select)

        list_btns = tk.Frame(left, bg=BG2)
        list_btns.pack(fill="x", padx=6, pady=8)
        icon_btn(list_btns, "+ New mode",
                 lambda: self._show_view(VIEW_NEW_MODE_CHOICE),
                 style="Accent.TButton").pack(fill="x")

        # Divider
        tk.Frame(main, bg=BORDER, width=1).pack(side="left", fill="y")

        # Right panel — view frame (cleared on view switch)
        self._view_frame = tk.Frame(main, bg=BG)
        self._view_frame.pack(side="left", fill="both", expand=True)

        self._show_view(VIEW_HOME)

    # ---------------------------------------------------------------- #
    #  View navigation                                                   #
    # ---------------------------------------------------------------- #

    def _show_view(self, view_name: str):
        for child in self._view_frame.winfo_children():
            child.destroy()
        self._current_view = view_name
        builder = getattr(self, f"_build_{view_name}", None)
        if builder:
            builder()

    # ---------------------------------------------------------------- #
    #  View builders                                                     #
    # ---------------------------------------------------------------- #

    def _build_home(self):
        container = tk.Frame(self._view_frame, bg=BG)
        container.pack(fill="both", expand=True, padx=32, pady=24)

        section_heading(container, "Your modes")

        if not self.profiles:
            empty = tk.Frame(container, bg=BG)
            empty.pack(fill="both", expand=True)
            tk.Label(empty, text="No modes yet", bg=BG, fg=FG2,
                     font=FONT_H2).pack(pady=(60, 8))
            tk.Label(empty, text="Create a mode to launch your apps and arrange windows.",
                     bg=BG, fg=FG2, font=FONT).pack()
            icon_btn(empty, "Create your first mode",
                     lambda: self._show_view(VIEW_NEW_MODE_CHOICE),
                     style="Accent.TButton").pack(pady=(20, 0))
            return

        for name, profile in self.profiles.items():
            apps = profile.get("apps", [])
            hotkey = profile.get("hotkey", "")
            info_parts = [f"{len(apps)} app{'s' if len(apps) != 1 else ''}"]
            if hotkey:
                info_parts.append(hotkey)
            info_text = "  ·  ".join(info_parts)

            card = card_frame(container, fill="x", pady=(0, 8))
            card.configure(cursor="hand2")

            tk.Label(card, text=name, bg=BG2, fg=FG, font=FONT_B,
                     cursor="hand2").pack(anchor="w")
            tk.Label(card, text=info_text, bg=BG2, fg=FG2, font=FONT_SM,
                     cursor="hand2").pack(anchor="w", pady=(2, 0))

            def _on_click(_e, n=name):
                self._current_profile = n
                self._show_view(VIEW_MODE_DETAIL)

            card.bind("<Button-1>", _on_click)
            for child in card.winfo_children():
                child.bind("<Button-1>", _on_click)

    def _build_new_mode_choice(self):
        container = tk.Frame(self._view_frame, bg=BG)
        container.pack(fill="both", expand=True, padx=32, pady=24)

        section_heading(container, "Create a new mode")

        cards = tk.Frame(container, bg=BG)
        cards.pack(fill="x", pady=(16, 0))

        # Capture card
        cap = card_frame(cards, fill="x", pady=(0, 12))
        cap.configure(cursor="hand2")
        tk.Label(cap, text="Capture current setup", bg=BG2, fg=FG,
                 font=FONT_B, cursor="hand2").pack(anchor="w")
        tk.Label(cap, text="Open your apps, arrange windows, then capture.\n"
                           "Fastest way to create a mode.",
                 bg=BG2, fg=FG2, font=FONT_SM, justify="left",
                 cursor="hand2").pack(anchor="w", pady=(4, 0))

        def _go_capture(_e=None):
            self._show_view(VIEW_CAPTURE)
        cap.bind("<Button-1>", _go_capture)
        for child in cap.winfo_children():
            child.bind("<Button-1>", _go_capture)

        # Manual card
        man = card_frame(cards, fill="x", pady=(0, 12))
        man.configure(cursor="hand2")
        tk.Label(man, text="Manual setup", bg=BG2, fg=FG,
                 font=FONT_B, cursor="hand2").pack(anchor="w")
        tk.Label(man, text="Start from scratch with full control over every detail.",
                 bg=BG2, fg=FG2, font=FONT_SM, justify="left",
                 cursor="hand2").pack(anchor="w", pady=(4, 0))

        def _go_manual(_e=None):
            name = self._unique_name("new-mode")
            self.profiles[name] = {
                "trigger_keywords": [], "hotkey": "", "message": "", "apps": []
            }
            self._current_profile = name
            self._refresh_profile_list(select=name)
            self._mark_dirty()
            self._show_view(VIEW_MODE_DETAIL)
        man.bind("<Button-1>", _go_manual)
        for child in man.winfo_children():
            child.bind("<Button-1>", _go_manual)

        # Back link
        back = tk.Label(container, text="← Back", bg=BG, fg=ACCENT,
                        font=FONT, cursor="hand2")
        back.pack(anchor="w", pady=(20, 0))
        back.bind("<Button-1>", lambda _e: self._show_view(VIEW_HOME))

    def _build_capture(self):
        tk.Label(self._view_frame, text="Capture screen — coming soon",
                 bg=BG, fg=FG2, font=FONT).pack(pady=60)

    def _build_review(self):
        tk.Label(self._view_frame, text="Review screen — coming soon",
                 bg=BG, fg=FG2, font=FONT).pack(pady=60)

    def _build_mode_detail(self):
        tk.Label(self._view_frame, text="Mode detail — coming soon",
                 bg=BG, fg=FG2, font=FONT).pack(pady=60)

    def _build_advanced(self):
        tk.Label(self._view_frame, text="Advanced editor — coming soon",
                 bg=BG, fg=FG2, font=FONT).pack(pady=60)

    # ---------------------------------------------------------------- #
    #  Load / Save                                                       #
    # ---------------------------------------------------------------- #

    def _load(self):
        if not CONFIG_PATH.exists():
            messagebox.showerror("Not found",
                f"profiles.json not found at:\n{CONFIG_PATH}\n\nStarting with empty config.")
            self.config_data = {"settings": {}, "profiles": {}}
        else:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.config_data = json.load(f)

        self.profiles = self.config_data.get("profiles", {})
        self._refresh_profile_list()
        self._dirty = False
        self._update_title()
        self._show_view(VIEW_HOME)

    def _save(self):
        self._flush_current_profile()
        self.config_data["profiles"] = self.profiles
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        self._dirty = False
        self._update_title()

    def _flush_current_profile(self):
        """Write form values back into self.profiles for the current profile.
        TODO: S4 will restore full flush logic when _build_mode_detail owns the form.
        """
        pass

    # ---------------------------------------------------------------- #
    #  Profile list actions                                              #
    # ---------------------------------------------------------------- #

    def _refresh_profile_list(self, select: str | None = None):
        self.profile_list.delete(0, "end")
        for name, profile in self.profiles.items():
            apps = profile.get("apps", [])
            hotkey = profile.get("hotkey", "")
            suffix = f"  ({len(apps)} apps" + (f", {hotkey}" if hotkey else "") + ")"
            self.profile_list.insert("end", f"  {name}{suffix}")
        if select:
            keys = list(self.profiles.keys())
            if select in keys:
                idx = keys.index(select)
                self.profile_list.select_clear(0, "end")
                self.profile_list.select_set(idx)

    def _on_profile_select(self, _event=None):
        sel = self.profile_list.curselection()
        if not sel:
            return
        name = list(self.profiles.keys())[sel[0]]
        self._current_profile = name
        self._show_view(VIEW_MODE_DETAIL)

    def _add_profile(self):
        self._show_view(VIEW_NEW_MODE_CHOICE)

    def _dupe_profile(self):
        if not self._current_profile:
            return
        src = self._current_profile
        name = self._unique_name(src + "-copy")
        self.profiles[name] = deepcopy(self.profiles[src])
        self._current_profile = name
        self._refresh_profile_list(select=name)
        self._mark_dirty()
        self._show_view(VIEW_MODE_DETAIL)

    def _delete_profile(self):
        if not self._current_profile:
            return
        if not messagebox.askyesno("Delete mode",
                f"Delete mode '{self._current_profile}'?", parent=self):
            return
        del self.profiles[self._current_profile]
        self._current_profile = None
        self._refresh_profile_list()
        self._mark_dirty()
        self._show_view(VIEW_HOME)

    def _unique_name(self, base: str) -> str:
        if base not in self.profiles:
            return base
        i = 2
        while f"{base}-{i}" in self.profiles:
            i += 1
        return f"{base}-{i}"

    # ---------------------------------------------------------------- #
    #  Dirty state                                                       #
    # ---------------------------------------------------------------- #

    def _mark_dirty(self, *_):
        if not self._dirty:
            self._dirty = True
            self._update_title()
            self._unsaved_chip.pack(side="right", padx=(0, 8))

    def _update_title(self):
        dot = " ●" if self._dirty else ""
        self.title(f"WakeUp — Config Editor{dot}")
        if not self._dirty:
            self._unsaved_chip.pack_forget()

    def _on_close(self):
        if self._dirty:
            ans = messagebox.askyesnocancel(
                "Unsaved changes", "Save changes before closing?", parent=self)
            if ans is None:
                return
            if ans:
                self._save()
        self.destroy()


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    app = WakeUpConfigUI()
    app.mainloop()
