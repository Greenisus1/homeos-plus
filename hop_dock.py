#!/usr/bin/env python3
"""HomeOS Plus dock: a small always-on-top launcher bar.

First buttons are always Terminal and Exit, then the
App Store and Settings, then any apps picked in Settings. The dock reloads
itself when its config file changes, so Settings never has to manage it.
"""
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hop_common as hop  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STORE_HELP = os.path.join(HERE, "hop_store_help.sh")

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:  # pragma: no cover - exercised on device only
    print("HomeOS Plus dock needs python3-tk (sudo apt install python3-tk).")
    raise SystemExit(1)


def run_detached(argv):
    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def open_terminal(command=None):
    term = shutil.which("x-terminal-emulator") or shutil.which("lxterminal")
    if not term:
        return False
    argv = [term] if not command else [term, "-e", command]
    run_detached(argv)
    return True


def open_app_store():
    if shutil.which("appstore"):
        open_terminal("appstore")
    else:
        open_terminal("sh %s" % STORE_HELP)


def open_music():
    run_detached([shutil.which("x-terminal-emulator") or "lxterminal", "-e",
                  "python3 %s; exec sh" % os.path.join(HERE, "hop_music.py")])


def open_settings():
    run_detached([sys.executable, os.path.join(HERE, "hop_settings.py")])


def launch_desktop_app(exec_line):
    cmd = hop.clean_exec(exec_line)
    if cmd:
        run_detached(["sh", "-c", cmd])


class Dock:
    def __init__(self):
        self.cfg = hop.load_dock_config()
        self.cfg_mtime = self._mtime()
        self.root = tk.Tk()
        self.root.title("HomeOS Plus")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1c2b39")
        self.expanded = True
        self.frame = None
        self._build()
        self._place()
        self.root.after(1500, self._watch_config)

    def _mtime(self):
        try:
            return os.path.getmtime(hop.DOCK_CONFIG)
        except OSError:
            return 0.0

    def _watch_config(self):
        m = self._mtime()
        if m != self.cfg_mtime:
            self.cfg_mtime = m
            self.cfg = hop.load_dock_config()
            self._build()
            self._place()
        self.root.after(1500, self._watch_config)

    def _place(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        pos = self.cfg["position"]
        if pos == "top":
            geo = "%dx%d+%d+0" % (w, h, (sw - w) // 2)
        elif pos == "bottom":
            geo = "%dx%d+%d+%d" % (w, h, (sw - w) // 2, sh - h)
        elif pos == "left":
            geo = "%dx%d+0+%d" % (w, h, (sh - h) // 2)
        else:
            geo = "%dx%d+%d+%d" % (w, h, sw - w, (sh - h) // 2)
        self.root.geometry(geo)

    def _button(self, parent, text, cmd, bg="#2e4457"):
        side = "left" if self.cfg["position"] in ("top", "bottom") else "top"
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white",
                      activebackground="#3d5a73", activeforeground="white",
                      relief="flat", bd=0, padx=14,
                      font=("DejaVu Sans", max(9, self.cfg["size"] // 5)))
        b.pack(side=side, padx=3, pady=3)
        return b

    def _build(self):
        if self.frame is not None:
            self.frame.destroy()
        self.frame = tk.Frame(self.root, bg="#1c2b39")
        self.frame.pack()
        vertical = self.cfg["position"] in ("left", "right")
        if self.cfg["autohide"] and not self.expanded:
            strip = tk.Frame(self.frame, bg="#1c2b39",
                             width=self.cfg["size"] if vertical else 40,
                             height=40 if vertical else self.cfg["size"])
            strip.pack()
            strip.bind("<Enter>", self._expand)
            return
        # Required first two apps:
        self._button(self.frame, "Terminal", lambda: open_terminal(), "#2456a6")
        self._button(self.frame, "Exit", self._exit_desktop, "#a03b3b")
        self._button(self.frame, "App Store", open_app_store)
        self._button(self.frame, "Music", open_music)
        self._button(self.frame, "Settings", open_settings)
        by_id = {a["id"]: a for a in hop.list_apps()}
        for app_id in self.cfg["apps"]:
            app = by_id.get(app_id)
            if app:
                self._button(self.frame, app["name"],
                             lambda e=app["exec"]: launch_desktop_app(e))
        if self.cfg["autohide"]:
            for w in self.frame.winfo_children():
                w.bind("<Leave>", self._maybe_collapse)

    def _expand(self, _event=None):
        self.expanded = True
        self._build()
        self._place()

    def _maybe_collapse(self, event=None):
        x, y = self.root.winfo_pointerxy()
        wx, wy = self.root.winfo_rootx(), self.root.winfo_rooty()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        if not (wx <= x <= wx + w and wy <= y <= wy + h):
            self.expanded = False
            self._build()
            self._place()

    def _exit_desktop(self):
        if not messagebox.askyesno(
                "Exit HomeOS Plus",
                "Quit the desktop and go back to the console?\n"
                "Unsaved work in open windows will be lost."):
            return
        rc = subprocess.run(
            ["sudo", "-n", "systemctl", "isolate", "multi-user.target"],
            check=False).returncode
        if rc != 0:
            messagebox.showerror(
                "Exit HomeOS Plus",
                "Could not leave the desktop (sudo said no).\n"
                "From a terminal run: sudo systemctl isolate multi-user.target")

    def run(self):
        self.root.mainloop()


def main():
    Dock().run()


if __name__ == "__main__":
    main()
