#!/usr/bin/env python3
"""HomeOS Plus Settings: customize the desktop without admin knowledge.

Wallpaper, theme, dock layout, and which apps sit on the dock. Everything
writes user-level config; the dock picks changes up by itself.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hop_common as hop  # noqa: E402

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:  # pragma: no cover
    print("HomeOS Plus Settings needs python3-tk (sudo apt install python3-tk).")
    raise SystemExit(1)

ACCENTS = ["#2b6cb0", "#2f855a", "#b7791f", "#c53030", "#6b46c1",
           "#1c2b39", "#000000", "#4a5568"]


class Settings(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HomeOS Plus Settings")
        self.configure(bg="#f4f4f4")
        self.cfg = hop.load_dock_config()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self._dock_tab(nb)
        self._apps_tab(nb)
        self._look_tab(nb)
        self.minsize(520, 420)

    # --- Dock tab: position, size, autohide -------------------------------
    def _dock_tab(self, nb):
        tab = tk.Frame(nb, bg="#f4f4f4")
        nb.add(tab, text="Dock")
        tk.Label(tab, text="Dock position", bg="#f4f4f4").pack(anchor="w", padx=10, pady=(12, 0))
        self.pos_var = tk.StringVar(value=self.cfg["position"])
        for pos in ("top", "bottom", "left", "right"):
            tk.Radiobutton(tab, text=pos.title(), value=pos,
                           variable=self.pos_var, bg="#f4f4f4",
                           command=self._save_dock).pack(anchor="w", padx=24)
        tk.Label(tab, text="Button size", bg="#f4f4f4").pack(anchor="w", padx=10, pady=(12, 0))
        self.size_var = tk.IntVar(value=self.cfg["size"])
        tk.Scale(tab, from_=32, to=96, orient="horizontal",
                 variable=self.size_var, bg="#f4f4f4",
                 command=lambda _v: self._save_dock()).pack(fill="x", padx=24)
        self.hide_var = tk.BooleanVar(value=self.cfg["autohide"])
        tk.Checkbutton(tab, text="Hide the dock until I touch the screen edge",
                       variable=self.hide_var, bg="#f4f4f4",
                       command=self._save_dock).pack(anchor="w", padx=10, pady=12)

    def _save_dock(self):
        self.cfg["position"] = self.pos_var.get()
        self.cfg["size"] = int(self.size_var.get())
        self.cfg["autohide"] = bool(self.hide_var.get())
        self.cfg = hop.save_dock_config(self.cfg)

    # --- Apps tab: which apps sit on the dock ------------------------------
    def _apps_tab(self, nb):
        tab = tk.Frame(nb, bg="#f4f4f4")
        nb.add(tab, text="Apps")
        tk.Label(tab, text="Apps on your dock (Terminal and Exit are always first)",
                 bg="#f4f4f4").pack(anchor="w", padx=10, pady=(12, 4))
        box = tk.Frame(tab, bg="#f4f4f4")
        box.pack(fill="both", expand=True, padx=10, pady=4)
        canvas = tk.Canvas(box, bg="#f4f4f4", highlightthickness=0)
        scroll = tk.Scrollbar(box, command=canvas.yview)
        inner = tk.Frame(canvas, bg="#f4f4f4")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.app_vars = {}
        skip = {hop.TERMINAL_ID, hop.EXIT_ID, "homeos-plus-settings"}
        for app in hop.list_apps():
            if app["id"] in skip:
                continue
            var = tk.BooleanVar(value=app["id"] in self.cfg["apps"])
            self.app_vars[app["id"]] = var
            tk.Checkbutton(inner, text=app["name"], variable=var,
                           bg="#f4f4f4", anchor="w",
                           command=self._save_apps).pack(anchor="w")
        if not self.app_vars:
            tk.Label(inner, text="No other apps found yet.",
                     bg="#f4f4f4").pack(anchor="w")
        tk.Button(tab, text="Install an Ubuntu app (.deb file)...",
                  command=self._install_deb).pack(anchor="w", padx=10, pady=10)

    def _save_apps(self):
        self.cfg["apps"] = [k for k, v in self.app_vars.items() if v.get()]
        self.cfg = hop.save_dock_config(self.cfg)

    # --- Look tab: wallpaper + theme ---------------------------------------
    def _look_tab(self, nb):
        tab = tk.Frame(nb, bg="#f4f4f4")
        nb.add(tab, text="Look")
        tk.Label(tab, text="Theme", bg="#f4f4f4").pack(anchor="w", padx=10, pady=(12, 0))
        themes = hop.list_themes()
        current = hop.current_theme()
        self.theme_var = tk.StringVar(value=current if current in themes else (themes[0] if themes else ""))
        menu = ttk.Combobox(tab, values=themes, textvariable=self.theme_var, state="readonly")
        menu.pack(fill="x", padx=24, pady=4)
        tk.Button(tab, text="Apply theme", command=self._apply_theme).pack(anchor="w", padx=24)
        tk.Label(tab, text="Wallpaper colour", bg="#f4f4f4").pack(anchor="w", padx=10, pady=(16, 0))
        row = tk.Frame(tab, bg="#f4f4f4")
        row.pack(anchor="w", padx=24, pady=4)
        for color in ACCENTS:
            tk.Button(row, bg=color, width=2, relief="flat",
                      command=lambda c=color: self._apply_wallpaper(c)).pack(side="left", padx=2)
        tk.Label(tab, text="Wallpaper picture", bg="#f4f4f4").pack(anchor="w", padx=10, pady=(12, 0))
        pics = tk.Frame(tab, bg="#f4f4f4")
        pics.pack(fill="both", expand=True, padx=24, pady=4)
        self.pic_list = tk.Listbox(pics, height=6)
        self.pic_list.pack(side="left", fill="both", expand=True)
        for path in hop.list_wallpapers():
            self.pic_list.insert("end", path)
        btnrow = tk.Frame(tab, bg="#f4f4f4")
        btnrow.pack(anchor="w", padx=24, pady=4)
        tk.Button(btnrow, text="Use selected picture",
                  command=self._apply_picked).pack(side="left")
        tk.Button(btnrow, text="Browse...",
                  command=self._browse).pack(side="left", padx=6)

    def _apply_theme(self):
        name = self.theme_var.get()
        if not name:
            return
        hop.apply_theme(name)
        messagebox.showinfo("HomeOS Plus", "Theme set to %s.\nOpen windows pick it up as they reload." % name)

    def _apply_wallpaper(self, value):
        try:
            backend, detail = hop.apply_wallpaper(value)
            messagebox.showinfo("HomeOS Plus", "Wallpaper applied (%s)." % backend)
        except Exception as exc:  # noqa: BLE001 - show plainly to a non-admin
            messagebox.showerror("HomeOS Plus", "Could not set wallpaper: %s" % exc)

    def _apply_picked(self):
        sel = self.pic_list.curselection()
        if sel:
            self._apply_wallpaper(self.pic_list.get(sel[0]))

    def _install_deb(self):
        path = filedialog.askopenfilename(
            filetypes=[("Ubuntu/Debian apps", "*.deb")])
        if not path:
            return
        if not messagebox.askyesno(
                "Install Ubuntu app",
                "Install %s?\n\nPi OS is Debian-based, so most Ubuntu apps "
                "work, but not all.\nA terminal will open and ask for the "
                "install." % os.path.basename(path)):
            return
        import shutil
        import subprocess
        term = shutil.which("x-terminal-emulator") or shutil.which("lxterminal")
        if not term:
            messagebox.showerror("Install Ubuntu app", "No terminal app found.")
            return
        subprocess.Popen([term, "-e",
                          "sudo apt install '%s'; echo; echo Done - close this window; exec sh" % path])

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("Pictures", "*.png *.jpg *.jpeg")])
        if path:
            self._apply_wallpaper(path)


def main():
    Settings().mainloop()


if __name__ == "__main__":
    main()
