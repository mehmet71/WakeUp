"""
WakeUp Config UI — Visual editor for profiles.json
Run with: python config_ui.py
"""

import json
import os
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

BG       = "#1a1a1a"
BG2      = "#242424"
BG3      = "#2e2e2e"
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
FONT_H   = ("Segoe UI", 13, "bold")


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

        pad = dict(padx=20, pady=6)

        # ---- fields ----
        fields = tk.Frame(self, bg=BG)
        fields.pack(fill="x", padx=24, pady=(20, 0))
        fields.columnconfigure(1, weight=1)

        self.v_name    = labeled_entry(fields, "Display name",  0, self.data.get("name", ""))
        self.v_hotkey  = labeled_entry(fields, "Delay (s)",     2, str(self.data.get("delay", 0)))

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
            delay = float(self.v_hotkey.get().strip() or "0")
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
        self.geometry("960x660")
        self.minsize(800, 500)
        apply_theme(self)

        self.config_data: dict = {}
        self.profiles: dict   = {}
        self._dirty = False
        self._current_profile: str | None = None

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

        tk.Label(topbar, text="WakeUp  Config Editor",
                 bg=BG2, fg=FG, font=FONT_H).pack(side="left", padx=20)

        self.save_btn = icon_btn(topbar, "💾  Save", self._save, style="Accent.TButton")
        self.save_btn.pack(side="right", padx=12, pady=10)

        tk.Frame(topbar, bg=BORDER, width=1).pack(side="right", fill="y", pady=8)

        # ── main area ────────────────────────────────────────────────
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)

        # Left panel — profile list
        left = tk.Frame(main, bg=BG2, width=200)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="PROFILES", bg=BG2, fg=FG2, font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=14, pady=(14, 6))

        list_frame = tk.Frame(left, bg=BG2)
        list_frame.pack(fill="both", expand=True, padx=6)

        self.profile_list = tk.Listbox(
            list_frame, bg=BG2, fg=FG, selectbackground=ACCENT2,
            selectforeground="#fff", relief="flat", bd=0,
            font=FONT, activestyle="none", highlightthickness=0,
            cursor="hand2")
        self.profile_list.pack(fill="both", expand=True)
        self.profile_list.bind("<<ListboxSelect>>", self._on_profile_select)

        # List action buttons
        list_btns = tk.Frame(left, bg=BG2)
        list_btns.pack(fill="x", padx=6, pady=8)
        icon_btn(list_btns, "+ Add",    self._add_profile,    width=7).pack(side="left", padx=(0, 4))
        icon_btn(list_btns, "⧉ Dupe",  self._dupe_profile,   width=7).pack(side="left", padx=(0, 4))
        icon_btn(list_btns, "✕ Del",   self._delete_profile,
                 style="Danger.TButton", width=6).pack(side="left")

        # Divider
        tk.Frame(main, bg=BORDER, width=1).pack(side="left", fill="y")

        # Right panel — profile detail
        self.right = tk.Frame(main, bg=BG)
        self.right.pack(side="left", fill="both", expand=True)

        self._build_detail_panel(self.right)

    def _build_detail_panel(self, parent):
        scroll_canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        self.detail = tk.Frame(scroll_canvas, bg=BG)
        self.detail_window = scroll_canvas.create_window((0, 0), window=self.detail, anchor="nw")

        def _on_resize(e):
            scroll_canvas.itemconfig(self.detail_window, width=e.width)
        scroll_canvas.bind("<Configure>", _on_resize)
        self.detail.bind("<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind("<MouseWheel>",
            lambda e: scroll_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        pad = dict(padx=28, pady=0)

        # Profile name
        name_row = tk.Frame(self.detail, bg=BG)
        name_row.pack(fill="x", padx=28, pady=(22, 0))
        tk.Label(name_row, text="Profile name", bg=BG, fg=FG2, font=FONT_SM).pack(anchor="w")
        self.v_profile_name = tk.StringVar()
        self.v_profile_name.trace_add("write", self._mark_dirty)
        ttk.Entry(name_row, textvariable=self.v_profile_name, font=FONT_H, width=30).pack(
            anchor="w", pady=(4, 0))

        # Row: hotkey + message
        mid_row = tk.Frame(self.detail, bg=BG)
        mid_row.pack(fill="x", padx=28, pady=(16, 0))
        mid_row.columnconfigure(1, weight=1)
        mid_row.columnconfigure(3, weight=2)

        tk.Label(mid_row, text="Hotkey", bg=BG, fg=FG2, font=FONT_SM).grid(
            row=0, column=0, sticky="w", padx=(0, 8))
        self.v_hotkey = tk.StringVar()
        self.v_hotkey.trace_add("write", self._mark_dirty)
        ttk.Entry(mid_row, textvariable=self.v_hotkey, width=16).grid(
            row=0, column=1, sticky="w")
        tk.Label(mid_row, text="  e.g. ctrl+alt+w", bg=BG, fg=FG2, font=FONT_SM).grid(
            row=0, column=2, sticky="w")

        tk.Label(mid_row, text="Startup message", bg=BG, fg=FG2, font=FONT_SM).grid(
            row=0, column=3, sticky="w", padx=(24, 8))
        self.v_message = tk.StringVar()
        self.v_message.trace_add("write", self._mark_dirty)
        ttk.Entry(mid_row, textvariable=self.v_message, width=36).grid(
            row=0, column=4, sticky="ew")

        # Keywords
        kw_frame = tk.Frame(self.detail, bg=BG)
        kw_frame.pack(fill="x", padx=28, pady=(16, 0))
        tk.Label(kw_frame, text="Voice / keyword triggers  (one per line)",
                 bg=BG, fg=FG2, font=FONT_SM).pack(anchor="w")
        self.kw_text = dark_text(kw_frame, height=4)
        self.kw_text.pack(fill="x", pady=(4, 0))
        self.kw_text.bind("<<Modified>>", self._mark_dirty)

        # Apps section
        apps_header = tk.Frame(self.detail, bg=BG)
        apps_header.pack(fill="x", padx=28, pady=(22, 0))
        tk.Label(apps_header, text="Apps", bg=BG, fg=FG, font=FONT_B).pack(side="left")

        app_btns = tk.Frame(apps_header, bg=BG)
        app_btns.pack(side="right")
        icon_btn(app_btns, "↑ Up",      self._app_move_up,   width=6).pack(side="left", padx=2)
        icon_btn(app_btns, "↓ Down",    self._app_move_down, width=6).pack(side="left", padx=2)
        icon_btn(app_btns, "+ Add",     self._app_add,       width=6).pack(side="left", padx=2)
        icon_btn(app_btns, "✎ Edit",    self._app_edit,      width=6).pack(side="left", padx=2)
        icon_btn(app_btns, "✕ Remove",  self._app_delete,
                 style="Danger.TButton", width=8).pack(side="left", padx=2)

        # Apps treeview
        tree_frame = tk.Frame(self.detail, bg=BG)
        tree_frame.pack(fill="x", padx=28, pady=(6, 24))

        cols = ("name", "path", "delay", "monitor", "preset")
        self.apps_tree = ttk.Treeview(tree_frame, columns=cols,
                                       show="headings", height=8,
                                       selectmode="browse")
        self.apps_tree.heading("name",    text="Name")
        self.apps_tree.heading("path",    text="Path")
        self.apps_tree.heading("delay",   text="Delay")
        self.apps_tree.heading("monitor", text="Monitor")
        self.apps_tree.heading("preset",  text="Preset")
        self.apps_tree.column("name",    width=130, minwidth=80)
        self.apps_tree.column("path",    width=280, minwidth=120)
        self.apps_tree.column("delay",   width=55,  minwidth=45, anchor="center")
        self.apps_tree.column("monitor", width=65,  minwidth=50, anchor="center")
        self.apps_tree.column("preset",  width=140, minwidth=80)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.apps_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.apps_tree.xview)
        self.apps_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.apps_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.apps_tree.bind("<Double-1>", lambda e: self._app_edit())

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
        if self.profiles:
            self.profile_list.select_set(0)
            self.profile_list.event_generate("<<ListboxSelect>>")
        self._dirty = False
        self._update_title()

    def _save(self):
        self._flush_current_profile()
        self.config_data["profiles"] = self.profiles
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        self._dirty = False
        self._update_title()
        self.save_btn.configure(text="💾  Save")

    def _flush_current_profile(self):
        """Write form values back into self.profiles for the current profile."""
        if self._current_profile is None:
            return
        old_name = self._current_profile
        new_name = self.v_profile_name.get().strip()
        if not new_name:
            return

        profile = self.profiles.get(old_name, {})
        profile["hotkey"]           = self.v_hotkey.get().strip()
        profile["message"]          = self.v_message.get().strip()
        raw_kw = self.kw_text.get("1.0", "end").strip()
        profile["trigger_keywords"] = [k.strip() for k in raw_kw.splitlines() if k.strip()]
        profile["apps"]             = self._tree_to_apps()

        if new_name != old_name:
            ordered = {}
            for k, v in self.profiles.items():
                ordered[new_name if k == old_name else k] = v
            self.profiles = ordered
            self._current_profile = new_name
        else:
            self.profiles[old_name] = profile

        self._refresh_profile_list(select=new_name)

    def _tree_to_apps(self) -> list:
        apps = []
        for iid in self.apps_tree.get_children():
            data = self.apps_tree.item(iid, "values")
            app_obj = json.loads(self.apps_tree.item(iid, "tags")[0])
            apps.append(app_obj)
        return apps

    # ---------------------------------------------------------------- #
    #  Profile list actions                                              #
    # ---------------------------------------------------------------- #

    def _refresh_profile_list(self, select: str | None = None):
        self.profile_list.delete(0, "end")
        for name in self.profiles:
            self.profile_list.insert("end", f"  {name}")
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
        if self._current_profile:
            self._flush_current_profile()

        name = list(self.profiles.keys())[sel[0]]
        self._current_profile = name
        profile = self.profiles[name]

        self.v_profile_name.set(name)
        self.v_hotkey.set(profile.get("hotkey", ""))
        self.v_message.set(profile.get("message", ""))

        self.kw_text.delete("1.0", "end")
        self.kw_text.insert("1.0", "\n".join(profile.get("trigger_keywords", [])))
        self.kw_text.edit_modified(False)

        self._refresh_apps_tree(profile.get("apps", []))

    def _add_profile(self):
        self._flush_current_profile()
        name = self._unique_name("new-profile")
        self.profiles[name] = {
            "trigger_keywords": [], "hotkey": "", "message": "", "apps": []
        }
        self._refresh_profile_list(select=name)
        self._current_profile = None
        self.profile_list.select_set(list(self.profiles.keys()).index(name))
        self.profile_list.event_generate("<<ListboxSelect>>")
        self._mark_dirty()

    def _dupe_profile(self):
        if not self._current_profile:
            return
        self._flush_current_profile()
        src = self._current_profile
        name = self._unique_name(src + "-copy")
        self.profiles[name] = deepcopy(self.profiles[src])
        self._refresh_profile_list(select=name)
        self._current_profile = None
        self.profile_list.select_set(list(self.profiles.keys()).index(name))
        self.profile_list.event_generate("<<ListboxSelect>>")
        self._mark_dirty()

    def _delete_profile(self):
        if not self._current_profile:
            return
        if not messagebox.askyesno("Delete profile",
                f"Delete profile '{self._current_profile}'?", parent=self):
            return
        del self.profiles[self._current_profile]
        self._current_profile = None
        self._refresh_profile_list()
        if self.profiles:
            self.profile_list.select_set(0)
            self.profile_list.event_generate("<<ListboxSelect>>")
        self._mark_dirty()

    def _unique_name(self, base: str) -> str:
        if base not in self.profiles:
            return base
        i = 2
        while f"{base}-{i}" in self.profiles:
            i += 1
        return f"{base}-{i}"

    # ---------------------------------------------------------------- #
    #  Apps treeview                                                     #
    # ---------------------------------------------------------------- #

    def _refresh_apps_tree(self, apps: list):
        self.apps_tree.delete(*self.apps_tree.get_children())
        for app in apps:
            w = app.get("window", {})
            self.apps_tree.insert("", "end",
                values=(
                    app.get("name", ""),
                    app.get("path", ""),
                    app.get("delay", 0),
                    w.get("monitor", 0),
                    w.get("preset", "full"),
                ),
                tags=(json.dumps(app),)
            )

    def _selected_app_idx(self) -> int | None:
        sel = self.apps_tree.selection()
        if not sel:
            return None
        children = self.apps_tree.get_children()
        return list(children).index(sel[0])

    def _app_add(self):
        dlg = AppDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.apps_tree.insert("", "end",
                values=(
                    dlg.result["name"], dlg.result["path"],
                    dlg.result["delay"],
                    dlg.result["window"]["monitor"],
                    dlg.result["window"]["preset"],
                ),
                tags=(json.dumps(dlg.result),)
            )
            self._mark_dirty()

    def _app_edit(self):
        sel = self.apps_tree.selection()
        if not sel:
            return
        iid = sel[0]
        app_data = json.loads(self.apps_tree.item(iid, "tags")[0])
        dlg = AppDialog(self, app_data)
        self.wait_window(dlg)
        if dlg.result:
            self.apps_tree.item(iid,
                values=(
                    dlg.result["name"], dlg.result["path"],
                    dlg.result["delay"],
                    dlg.result["window"]["monitor"],
                    dlg.result["window"]["preset"],
                ),
                tags=(json.dumps(dlg.result),)
            )
            self._mark_dirty()

    def _app_delete(self):
        sel = self.apps_tree.selection()
        if sel:
            self.apps_tree.delete(sel[0])
            self._mark_dirty()

    def _app_move_up(self):
        sel = self.apps_tree.selection()
        if not sel:
            return
        iid = sel[0]
        idx = self.apps_tree.index(iid)
        if idx > 0:
            self.apps_tree.move(iid, "", idx - 1)
            self._mark_dirty()

    def _app_move_down(self):
        sel = self.apps_tree.selection()
        if not sel:
            return
        iid = sel[0]
        idx = self.apps_tree.index(iid)
        self.apps_tree.move(iid, "", idx + 1)
        self._mark_dirty()

    # ---------------------------------------------------------------- #
    #  Dirty state                                                       #
    # ---------------------------------------------------------------- #

    def _mark_dirty(self, *_):
        if not self._dirty:
            self._dirty = True
            self._update_title()
            self.save_btn.configure(text="💾  Save  ●")

    def _update_title(self):
        dot = " ●" if self._dirty else ""
        self.title(f"WakeUp — Config Editor{dot}")

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
