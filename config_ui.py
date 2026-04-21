"""
WakeUp Config UI — Visual editor for profiles.json
Run with: python config_ui.py
"""

import json
import shlex
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


# ------------------------------------------------------------------ #
#  Launch behavior mapping (Contract C6)                              #
# ------------------------------------------------------------------ #

_CHROMIUM_BEHAVIORS = ["chrome_urls", "chrome_new_window"]

_BEHAVIOR_OPTIONS = {
    "vscode":   ["vscode_folder", "vscode_session", "plain"],
    "chromium": _CHROMIUM_BEHAVIORS,
    "browser":  _CHROMIUM_BEHAVIORS,
    "generic":  ["plain"],
}

_BEHAVIOR_LABELS = {
    "vscode_folder":     "Open folder/workspace",
    "vscode_session":    "Reopen last session",
    "plain":             "Launch plain",
    "chrome_urls":       "Open these URLs",
    "chrome_new_window": "Open new window",
}

_EMPTY_DRAFT: dict = {
    "name": "",
    "path": "",
    "window_title": "",
    "window": {"monitor": 0, "preset": "full", "x": 0, "y": 0, "w": 1280, "h": 720},
    "app_type": "generic",
    "launch_behavior": "plain",
    "launch_details": {},
    "confidence": "low",
}


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
                wrap="word", highlightthickness=1,
                highlightbackground=BORDER, highlightcolor=ACCENT)
    return t


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
        # Preserve browser block if the source app had one — the advanced
        # dialog doesn't edit it, but must not silently drop it.
        if "browser" in self.data:
            self.result["browser"] = deepcopy(self.data["browser"])
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

    # ---------------------------------------------------------------- #
    #  S3: Capture flow                                                  #
    # ---------------------------------------------------------------- #

    def _build_capture(self):
        container = tk.Frame(self._view_frame, bg=BG)
        container.pack(fill="both", expand=True, padx=32, pady=24)

        section_heading(container, "Capture your current setup")

        tk.Label(
            container,
            text=(
                "Open the apps you want in this mode and arrange them on your monitors.\n"
                "When ready, click Capture."
            ),
            bg=BG, fg=FG2, font=FONT, justify="left",
        ).pack(anchor="w", pady=(0, 24))

        # Status label — updated inline during capture
        status_var = tk.StringVar()
        status_lbl = tk.Label(container, textvariable=status_var,
                              bg=BG, fg=FG2, font=FONT_SM)
        status_lbl.pack(anchor="w", pady=(0, 12))

        def _do_capture():
            status_var.set("Capturing…")
            container.update_idletasks()
            try:
                from capture_service import capture_current_desktop
                drafts = capture_current_desktop()
            except Exception as exc:
                status_var.set(f"Error: {exc}")
                return

            if not drafts:
                status_var.set(
                    "No windows detected. Make sure your apps are open and visible."
                )
                return

            monitor_count = len({d["window"]["monitor"] for d in drafts})
            status_var.set(
                f"Found {len(drafts)} app{'s' if len(drafts) != 1 else ''} "
                f"on {monitor_count} monitor{'s' if monitor_count != 1 else ''}."
            )
            self._draft_apps = drafts
            self.after(400, lambda: self._show_view(VIEW_REVIEW))

        icon_btn(container, "  Capture now  ", _do_capture,
                 style="Accent.TButton").pack(anchor="w")

        # Secondary actions
        sec = tk.Frame(container, bg=BG)
        sec.pack(anchor="w", pady=(20, 0))

        back_lbl = tk.Label(sec, text="← Back", bg=BG, fg=ACCENT,
                            font=FONT, cursor="hand2")
        back_lbl.pack(side="left")
        back_lbl.bind("<Button-1>",
                      lambda _e: self._show_view(VIEW_NEW_MODE_CHOICE))

        tk.Label(sec, text="  or  ", bg=BG, fg=FG2, font=FONT).pack(side="left")

        manual_lbl = tk.Label(sec, text="Build manually instead", bg=BG,
                              fg=ACCENT, font=FONT, cursor="hand2")
        manual_lbl.pack(side="left")

        def _go_manual(_e=None):
            name = self._unique_name("new-mode")
            self.profiles[name] = {
                "trigger_keywords": [], "hotkey": "", "message": "", "apps": []
            }
            self._current_profile = name
            self._draft_apps = None
            self._refresh_profile_list(select=name)
            self._mark_dirty()
            self._show_view(VIEW_MODE_DETAIL)

        manual_lbl.bind("<Button-1>", _go_manual)

    def _make_scroll_canvas(self, parent: tk.Frame) -> tk.Frame:
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        scroll_frame = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        return scroll_frame

    def _build_review(self):
        scroll_frame = self._make_scroll_canvas(self._view_frame)

        # ── header ───────────────────────────────────────────────────
        header = tk.Frame(scroll_frame, bg=BG)
        header.pack(fill="x", padx=32, pady=(24, 8))

        section_heading(header, "Review captured apps")

        drafts = self._draft_apps or []
        tk.Label(
            header,
            text=f"{len(drafts)} app{'s' if len(drafts) != 1 else ''} captured. "
                 "Review and configure each one before saving.",
            bg=BG, fg=FG2, font=FONT,
        ).pack(anchor="w")

        # ── app cards ────────────────────────────────────────────────
        cards_frame = tk.Frame(scroll_frame, bg=BG)
        cards_frame.pack(fill="x", padx=32, pady=(12, 0))

        def _rebuild():
            self._show_view(VIEW_REVIEW)

        for i, draft in enumerate(drafts):
            self._build_app_card(cards_frame, draft, i, on_remove=_rebuild)

        # ── bottom actions ───────────────────────────────────────────
        actions = tk.Frame(scroll_frame, bg=BG)
        actions.pack(fill="x", padx=32, pady=(16, 32))

        icon_btn(actions, "Continue →", lambda: self._show_view(VIEW_MODE_DETAIL),
                 style="Accent.TButton").pack(side="left")

        def _add_manual():
            self._draft_apps = self._draft_apps or []
            self._draft_apps.append(deepcopy(_EMPTY_DRAFT))
            _rebuild()

        icon_btn(actions, "+ Add app manually", _add_manual).pack(
            side="left", padx=(10, 0))

        back_lbl = tk.Label(actions, text="← Back to capture", bg=BG,
                            fg=ACCENT, font=FONT, cursor="hand2")
        back_lbl.pack(side="left", padx=(16, 0))
        back_lbl.bind("<Button-1>", lambda _e: self._show_view(VIEW_CAPTURE))

    def _build_app_card(
        self,
        parent: tk.Frame,
        draft: dict,
        index: int,
        on_remove=None,
    ) -> tk.Frame:
        """Render one DraftApp as an editable card inside `parent`."""

        card = card_frame(parent, fill="x", pady=(0, 10))
        card.columnconfigure(0, weight=1)

        # ── header row: index + confidence badge + remove ─────────
        top = tk.Frame(card, bg=BG2)
        top.pack(fill="x", pady=(0, 8))

        confidence = draft.get("confidence", "low")
        badge_colors = {"high": GREEN, "medium": "#e8a838", "low": RED}
        badge_fg = badge_colors.get(confidence, FG2)

        tk.Label(top, text=f"App {index + 1}", bg=BG2, fg=FG,
                 font=FONT_B).pack(side="left")
        tk.Label(top, text=f"  {confidence} confidence",
                 bg=BG2, fg=badge_fg, font=FONT_SM).pack(side="left")

        if on_remove:
            def _remove():
                if self._draft_apps is not None and index < len(self._draft_apps):
                    self._draft_apps.pop(index)
                on_remove()

            icon_btn(top, "Remove", _remove, style="Danger.TButton").pack(
                side="right")

        # ── form grid ─────────────────────────────────────────────
        form = tk.Frame(card, bg=BG2)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        row = 0

        # Name
        tk.Label(form, text="Name", bg=BG2, fg=FG2, font=FONT_SM).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        v_name = tk.StringVar(value=draft.get("name", ""))

        def _sync_name(*_):
            draft["name"] = v_name.get()

        v_name.trace_add("write", _sync_name)
        ttk.Entry(form, textvariable=v_name).grid(
            row=row, column=1, sticky="ew", pady=3)
        row += 1

        # Path
        tk.Label(form, text="Executable", bg=BG2, fg=FG2, font=FONT_SM).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        path_row = tk.Frame(form, bg=BG2)
        path_row.grid(row=row, column=1, sticky="ew", pady=3)
        path_row.columnconfigure(0, weight=1)

        v_path = tk.StringVar(value=draft.get("path", ""))

        def _sync_path(*_):
            draft["path"] = v_path.get()

        v_path.trace_add("write", _sync_path)
        ttk.Entry(path_row, textvariable=v_path).grid(
            row=0, column=0, sticky="ew")

        def _browse_path():
            p = filedialog.askopenfilename(
                title="Select executable",
                filetypes=[("Executables", "*.exe"), ("All files", "*.*")],
            )
            if p:
                v_path.set(p)

        ttk.Button(path_row, text="Browse…", command=_browse_path, width=9).grid(
            row=0, column=1, padx=(6, 0))
        row += 1

        # Monitor + preset on the same row
        tk.Label(form, text="Monitor", bg=BG2, fg=FG2, font=FONT_SM).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        win_row = tk.Frame(form, bg=BG2)
        win_row.grid(row=row, column=1, sticky="w", pady=3)

        v_monitor = tk.StringVar(
            value=str(draft.get("window", {}).get("monitor", 0)))

        def _sync_monitor(*_):
            try:
                draft.setdefault("window", {})["monitor"] = int(v_monitor.get())
            except ValueError:
                pass

        v_monitor.trace_add("write", _sync_monitor)
        ttk.Spinbox(win_row, textvariable=v_monitor, from_=0, to=5, width=4,
                    background=BG3, foreground=FG).pack(side="left")

        tk.Label(win_row, text="  Preset", bg=BG2, fg=FG2,
                 font=FONT_SM).pack(side="left", padx=(12, 6))

        current_preset = draft.get("window", {}).get("preset") or "full"
        v_preset = tk.StringVar(value=current_preset)

        def _sync_preset(*_):
            draft.setdefault("window", {})["preset"] = v_preset.get()

        v_preset.trace_add("write", _sync_preset)
        ttk.Combobox(win_row, textvariable=v_preset, values=PRESETS,
                     state="readonly", width=18).pack(side="left")
        row += 1

        # Launch behavior
        tk.Label(form, text="Launch as", bg=BG2, fg=FG2, font=FONT_SM).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=3)

        app_type = draft.get("app_type", "generic")
        behavior_keys = _BEHAVIOR_OPTIONS.get(app_type, ["plain"])
        behavior_labels = [_BEHAVIOR_LABELS.get(k, k) for k in behavior_keys]

        current_behavior = draft.get("launch_behavior", behavior_keys[0])
        current_label = _BEHAVIOR_LABELS.get(current_behavior, current_behavior)
        if current_label not in behavior_labels:
            current_label = behavior_labels[0]

        v_behavior_label = tk.StringVar(value=current_label)
        behavior_cb = ttk.Combobox(
            form, textvariable=v_behavior_label,
            values=behavior_labels, state="readonly", width=28)
        behavior_cb.grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        # Detail widget area (swapped by behavior selection)
        detail_frame = tk.Frame(form, bg=BG2)
        detail_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        row += 1

        def _build_detail_widget(behavior_key: str):
            for w in detail_frame.winfo_children():
                w.destroy()

            if behavior_key == "vscode_folder":
                tk.Label(detail_frame, text="Folder/workspace", bg=BG2,
                         fg=FG2, font=FONT_SM).grid(
                    row=0, column=0, sticky="w", padx=(0, 12), pady=3)
                f_row = tk.Frame(detail_frame, bg=BG2)
                f_row.grid(row=0, column=1, sticky="ew", pady=3)
                f_row.columnconfigure(0, weight=1)
                detail_frame.columnconfigure(1, weight=1)

                v_folder = tk.StringVar(
                    value=draft.get("launch_details", {}).get("folder", ""))

                def _sync_folder(*_):
                    draft.setdefault("launch_details", {})["folder"] = v_folder.get()

                v_folder.trace_add("write", _sync_folder)
                ttk.Entry(f_row, textvariable=v_folder).grid(
                    row=0, column=0, sticky="ew")

                def _browse_folder():
                    p = filedialog.askdirectory(title="Select folder")
                    if p:
                        v_folder.set(p)

                ttk.Button(f_row, text="Browse…", command=_browse_folder,
                           width=9).grid(row=0, column=1, padx=(6, 0))

            elif behavior_key == "chrome_urls":
                # Restore-session toggle row
                tk.Label(detail_frame, text="Restore session",
                         bg=BG2, fg=FG2, font=FONT_SM).grid(
                    row=0, column=0, sticky="w", padx=(0, 12), pady=3)

                current_restore = draft.get("launch_details", {}).get(
                    "restore_session", True)
                v_restore = tk.BooleanVar(value=bool(current_restore))

                def _sync_restore(*_):
                    draft.setdefault("launch_details", {})["restore_session"] = (
                        v_restore.get()
                    )

                v_restore.trace_add("write", _sync_restore)
                tk.Checkbutton(detail_frame, variable=v_restore,
                               bg=BG2, fg=FG, selectcolor=BG3,
                               activebackground=BG2, activeforeground=FG,
                               text=" Reopen last-session tabs",
                               font=FONT_SM).grid(
                    row=0, column=1, sticky="w", pady=3)

                # URLs text area
                tk.Label(detail_frame, text="Extra URLs (one per line)",
                         bg=BG2, fg=FG2, font=FONT_SM).grid(
                    row=1, column=0, sticky="nw", padx=(0, 12), pady=3)
                detail_frame.columnconfigure(1, weight=1)

                existing_urls = draft.get("launch_details", {}).get("urls", [])
                txt = dark_text(detail_frame, height=3, width=36)
                txt.insert("1.0", "\n".join(existing_urls))
                txt.grid(row=1, column=1, sticky="ew", pady=3)

                def _sync_urls(_event=None):
                    raw = txt.get("1.0", "end").strip()
                    draft.setdefault("launch_details", {})["urls"] = (
                        [u.strip() for u in raw.splitlines() if u.strip()]
                    )

                txt.bind("<FocusOut>", _sync_urls)
                txt.bind("<KeyRelease>", _sync_urls)

                # Ensure initial default is stored even if user never touches the box
                _sync_restore()

        def _on_behavior_change(_event=None):
            selected_label = v_behavior_label.get()
            key = behavior_keys[0]
            for k, lbl in _BEHAVIOR_LABELS.items():
                if lbl == selected_label:
                    key = k
                    break
            draft["launch_behavior"] = key
            draft["launch_details"] = {}
            _build_detail_widget(key)

        behavior_cb.bind("<<ComboboxSelected>>", _on_behavior_change)

        # Render initial detail widget
        _build_detail_widget(current_behavior)

    def _build_mode_detail(self):
        # Allow entry with no profile when arriving from capture flow
        if self._draft_apps is None and (
            not self._current_profile or self._current_profile not in self.profiles
        ):
            tk.Label(self._view_frame, text="No mode selected.",
                     bg=BG, fg=FG2, font=FONT).pack(pady=60)
            return

        profile = self.profiles.get(self._current_profile, {}) if self._current_profile else {}

        scroll_frame = self._make_scroll_canvas(self._view_frame)

        container = tk.Frame(scroll_frame, bg=BG)
        container.pack(fill="both", expand=True, padx=32, pady=24)
        container.columnconfigure(1, weight=1)

        # ── header ───────────────────────────────────────────────────
        header = tk.Frame(container, bg=BG)
        header.pack(fill="x", pady=(0, 16))

        section_heading(header, "Mode settings")

        # ── form fields ──────────────────────────────────────────────
        form = tk.Frame(container, bg=BG)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        # Inline warning label (shared, hidden by default)
        self._warn_label = tk.Label(form, text="", bg=BG, fg=RED, font=FONT_SM)

        # Mode name — empty for new modes from capture flow
        initial_name = self._current_profile if (self._current_profile and self._draft_apps is None) else ""
        self._v_mode_name = labeled_entry(form, "Mode name", 0, initial_name)
        self._v_mode_name.trace_add("write", self._mark_dirty)

        # Hotkey
        self._v_hotkey = labeled_entry(form, "Hotkey", 1,
                                       profile.get("hotkey", ""))
        tk.Label(form, text="e.g. ctrl+alt+w", bg=BG, fg=FG2,
                 font=FONT_SM).grid(row=1, column=2, sticky="w", padx=(6, 0))
        self._v_hotkey.trace_add("write", self._mark_dirty)

        # Trigger keywords
        tk.Label(form, text="Trigger keywords", bg=BG, fg=FG2,
                 font=FONT_SM).grid(row=2, column=0, sticky="nw",
                                    padx=(0, 12), pady=4)
        self._txt_keywords = dark_text(form, height=2, width=40)
        self._txt_keywords.insert("1.0", ", ".join(profile.get("trigger_keywords", [])))
        self._txt_keywords.grid(row=2, column=1, sticky="ew", pady=4)
        tk.Label(form, text="comma-separated", bg=BG, fg=FG2,
                 font=FONT_SM).grid(row=2, column=2, sticky="nw", padx=(6, 0), pady=4)
        self._txt_keywords.bind("<KeyRelease>", self._mark_dirty)

        # Launch message
        tk.Label(form, text="Launch message", bg=BG, fg=FG2,
                 font=FONT_SM).grid(row=3, column=0, sticky="nw",
                                    padx=(0, 12), pady=4)
        self._txt_message = dark_text(form, height=2, width=40)
        self._txt_message.insert("1.0", profile.get("message", ""))
        self._txt_message.grid(row=3, column=1, sticky="ew", pady=4)
        self._txt_message.bind("<KeyRelease>", self._mark_dirty)

        # Warning row (hidden until needed)
        self._warn_label.grid(row=4, column=1, sticky="w", pady=(0, 4))
        self._warn_label.grid_remove()

        # ── apps section ─────────────────────────────────────────────
        apps_header = tk.Frame(container, bg=BG)
        apps_header.pack(fill="x", pady=(20, 6))

        if self._draft_apps is not None:
            # Capture flow: show read-only draft summary
            tk.Label(apps_header, text="Apps", bg=BG, fg=FG, font=FONT_H2).pack(side="left")
            apps_info = tk.Frame(container, bg=BG)
            apps_info.pack(fill="x")
            tk.Label(apps_info,
                     text=f"{len(self._draft_apps)} app(s) will be saved with this mode.",
                     bg=BG, fg=FG2, font=FONT_SM).pack(anchor="w")
            for d in self._draft_apps:
                tk.Label(apps_info, text=f"  • {d.get('name') or d.get('path', '?')}",
                         bg=BG, fg=FG2, font=FONT_SM).pack(anchor="w")
        else:
            tk.Label(apps_header, text="Apps", bg=BG, fg=FG, font=FONT_H2).pack(side="left")
            icon_btn(apps_header, "+ Add app",
                     lambda: self._add_app_to_profile(), style="Accent.TButton").pack(side="right")
            self._apps_frame = tk.Frame(container, bg=BG)
            self._apps_frame.pack(fill="x")
            self._render_profile_apps()

        # ── bottom actions ───────────────────────────────────────────
        actions = tk.Frame(container, bg=BG)
        actions.pack(fill="x", pady=(20, 0))

        icon_btn(actions, "Save mode", self._save_mode,
                 style="Accent.TButton").pack(side="left")
        icon_btn(actions, "Test this mode", self._test_current_mode).pack(
            side="left", padx=(10, 0))
        if self._draft_apps is not None:
            icon_btn(actions, "← Back to review",
                     lambda: self._show_view(VIEW_REVIEW)).pack(side="left", padx=(10, 0))
        else:
            icon_btn(actions, "Advanced JSON…",
                     lambda: self._show_view(VIEW_ADVANCED)).pack(side="left", padx=(10, 0))
            icon_btn(actions, "Delete mode",
                     self._delete_profile, style="Danger.TButton").pack(side="right")

    def _render_profile_apps(self):
        """Re-render the app list rows inside self._apps_frame."""
        for w in self._apps_frame.winfo_children():
            w.destroy()

        if not self._current_profile:
            return

        apps = self.profiles[self._current_profile].get("apps", [])
        if not apps:
            tk.Label(self._apps_frame, text="No apps yet. Click '+ Add app' to start.",
                     bg=BG, fg=FG2, font=FONT_SM).pack(anchor="w", pady=8)
            return

        for i, app in enumerate(apps):
            row_frame = card_frame(self._apps_frame, fill="x", pady=(0, 6))

            tk.Label(row_frame, text=app.get("name", "Unnamed"),
                     bg=BG2, fg=FG, font=FONT_B).pack(side="left")
            tk.Label(row_frame,
                     text=f"  {app.get('window', {}).get('preset', '')}  "
                          f"·  monitor {app.get('window', {}).get('monitor', 0)}",
                     bg=BG2, fg=FG2, font=FONT_SM).pack(side="left")

            def _edit(idx=i):
                self._edit_app_in_profile(idx)

            def _remove(idx=i):
                self.profiles[self._current_profile]["apps"].pop(idx)
                self._mark_dirty()
                self._render_profile_apps()

            icon_btn(row_frame, "Remove", _remove, style="Danger.TButton").pack(
                side="right")
            icon_btn(row_frame, "Edit", _edit).pack(side="right", padx=(0, 6))

    def _add_app_to_profile(self):
        dlg = AppDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.profiles[self._current_profile].setdefault("apps", []).append(
                dlg.result)
            self._mark_dirty()
            self._render_profile_apps()

    def _edit_app_in_profile(self, index: int):
        apps = self.profiles[self._current_profile].get("apps", [])
        dlg = AppDialog(self, apps[index])
        self.wait_window(dlg)
        if dlg.result:
            apps[index] = dlg.result
            self._mark_dirty()
            self._render_profile_apps()

    def _build_advanced(self):
        if not self._current_profile or self._current_profile not in self.profiles:
            tk.Label(self._view_frame, text="No mode selected.",
                     bg=BG, fg=FG2, font=FONT).pack(pady=60)
            return

        container = tk.Frame(self._view_frame, bg=BG)
        container.pack(fill="both", expand=True, padx=32, pady=24)

        section_heading(container, f"Advanced — {self._current_profile}")
        tk.Label(container,
                 text="Edit the raw JSON for this mode. Invalid JSON cannot be saved.",
                 bg=BG, fg=FG2, font=FONT_SM).pack(anchor="w", pady=(0, 12))

        # JSON text area
        txt_frame = tk.Frame(container, bg=BG)
        txt_frame.pack(fill="both", expand=True)
        txt_frame.columnconfigure(0, weight=1)
        txt_frame.rowconfigure(0, weight=1)

        txt = tk.Text(
            txt_frame,
            bg=BG3, fg=FG, insertbackground=FG,
            font=("Consolas", 10), relief="flat", padx=10, pady=10,
            wrap="none", bd=1, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT,
        )
        vscroll = ttk.Scrollbar(txt_frame, orient="vertical", command=txt.yview)
        hscroll = ttk.Scrollbar(txt_frame, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")
        txt.grid(row=0, column=0, sticky="nsew")

        current_json = json.dumps(
            self.profiles[self._current_profile], indent=2, ensure_ascii=False)
        txt.insert("1.0", current_json)

        # Status / error label
        err_var = tk.StringVar()
        err_lbl = tk.Label(container, textvariable=err_var,
                           bg=BG, fg=RED, font=FONT_SM)
        err_lbl.pack(anchor="w", pady=(6, 0))

        # Actions
        actions = tk.Frame(container, bg=BG)
        actions.pack(fill="x", pady=(10, 0))

        def _apply():
            raw = txt.get("1.0", "end").strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                err_var.set(f"JSON error: {exc}")
                return
            if not isinstance(parsed, dict):
                err_var.set("Must be a JSON object.")
                return
            self.profiles[self._current_profile] = parsed
            self._mark_dirty()
            err_var.set("")
            self._show_view(VIEW_MODE_DETAIL)

        icon_btn(actions, "Apply & back", _apply,
                 style="Accent.TButton").pack(side="left")
        icon_btn(actions, "Test this mode", self._test_current_mode).pack(
            side="left", padx=(10, 0))
        icon_btn(actions, "← Back",
                 lambda: self._show_view(VIEW_MODE_DETAIL)).pack(
            side="left", padx=(10, 0))

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
        """Flush mode-detail form values into self.profiles. No-op outside mode_detail."""
        if self._current_view == VIEW_MODE_DETAIL:
            self._save_mode(quiet=True)

    def _save_mode(self, quiet: bool = False):
        """Read form vars and persist them into profiles, then write to disk."""
        # -- mode name --
        new_name = self._v_mode_name.get().strip()
        if not new_name:
            if not quiet:
                self._show_field_warning("Mode name cannot be empty.")
            return

        old_name = self._current_profile  # may be None for new capture-flow mode
        if old_name and new_name != old_name and new_name in self.profiles:
            if not quiet:
                self._show_field_warning(f"A mode named '{new_name}' already exists.")
            return

        profile = self.profiles.get(old_name, {}) if old_name else {}

        # -- rename or create --
        if old_name and new_name != old_name and old_name in self.profiles:
            del self.profiles[old_name]

        # -- scalar fields --
        profile["hotkey"] = self._v_hotkey.get().strip()
        profile["message"] = self._txt_message.get("1.0", "end").strip()
        raw_kw = self._txt_keywords.get("1.0", "end").strip()
        profile["trigger_keywords"] = (
            [k.strip() for k in raw_kw.split(",") if k.strip()] if raw_kw else []
        )

        # -- apps: convert drafts if coming from capture flow --
        if self._draft_apps is not None:
            from capture_service import draft_to_profile_app
            profile["apps"] = [draft_to_profile_app(d) for d in self._draft_apps]
        elif "apps" not in profile:
            profile["apps"] = []

        self.profiles[new_name] = profile
        self._current_profile = new_name
        self._draft_apps = None
        self.config_data["profiles"] = self.profiles

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)

        self._dirty = False
        self._update_title()
        self._refresh_profile_list(select=new_name)
        if not quiet:
            self._show_view(VIEW_HOME)

    def _test_current_mode(self):
        """Launch the current mode's apps in a daemon thread without requiring a save."""
        from launcher import execute_profile

        if self._draft_apps is not None:
            from capture_service import draft_to_profile_app
            apps = [draft_to_profile_app(d) for d in self._draft_apps]
        elif self._current_profile and self._current_profile in self.profiles:
            apps = self.profiles[self._current_profile].get("apps", [])
        else:
            apps = []

        if not apps:
            self._show_field_warning("No apps configured — nothing to launch.")
            return

        import threading
        threading.Thread(
            target=execute_profile,
            args=({"apps": apps},),
            daemon=True,
            name="test-mode",
        ).start()

        self._show_field_warning(
            f"Launching {len(apps)} app(s)…", duration_ms=3000)

    def _show_field_warning(self, message: str, duration_ms: int = 4000):
        """Display an inline warning in the mode-detail form for `duration_ms` ms."""
        if not hasattr(self, "_warn_label") or not self._warn_label.winfo_exists():
            messagebox.showwarning("Warning", message, parent=self)
            return
        self._warn_label.configure(text=f"⚠  {message}")
        self._warn_label.grid()
        self.after(duration_ms, self._hide_field_warning)

    def _hide_field_warning(self):
        if hasattr(self, "_warn_label") and self._warn_label.winfo_exists():
            self._warn_label.grid_remove()

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
        self._draft_apps = None
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
