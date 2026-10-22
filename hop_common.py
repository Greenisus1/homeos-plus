"""Shared helpers for HomeOS Plus (dock + settings).

All state lives in ~/.config/homeos-plus/. Everything here is pure-logic and
unit-testable: no GUI, no privileged calls. System effects are confined to
writing the user's own config files (GTK theme, pcmanfm wallpaper, dock
config) - the shell installer owns privileged work.
"""
import json
import os
import re
import shutil
import subprocess

APP_ID = "homeos-plus"
CONFIG_DIR = os.path.join(os.path.expanduser(os.environ.get("HOP_HOME", "~")),
                          ".config", APP_ID)
DOCK_CONFIG = os.path.join(CONFIG_DIR, "dock.json")

DEFAULT_DOCK = {
    "position": "top",      # top | bottom | left | right
    "size": 56,             # button strip thickness in px
    "autohide": False,
    "apps": [],             # desktop-file ids chosen in Settings
}

# The two required first apps, always pinned ahead of any custom pick.
TERMINAL_ID = "homeos-plus-terminal"
EXIT_ID = "homeos-plus-exit"


def load_dock_config(path=DOCK_CONFIG):
    cfg = dict(DEFAULT_DOCK)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULT_DOCK})
    except (OSError, ValueError):
        pass
    if cfg["position"] not in ("top", "bottom", "left", "right"):
        cfg["position"] = "top"
    try:
        cfg["size"] = min(128, max(32, int(cfg["size"])))
    except (TypeError, ValueError):
        cfg["size"] = DEFAULT_DOCK["size"]
    cfg["autohide"] = bool(cfg["autohide"])
    if not isinstance(cfg["apps"], list):
        cfg["apps"] = []
    return cfg


def save_dock_config(cfg, path=DOCK_CONFIG):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    merged = dict(DEFAULT_DOCK)
    merged.update({k: v for k, v in cfg.items() if k in DEFAULT_DOCK})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2)
    return merged


def iter_desktop_dirs(home=None):
    home = home or os.path.expanduser(os.environ.get("HOP_HOME", "~"))
    dirs = [os.path.join(home, ".local", "share", "applications"),
            "/usr/local/share/applications", "/usr/share/applications"]
    extra = os.environ.get("HOP_DESKTOP_DIRS")
    if extra:
        dirs = extra.split(os.pathsep)
    return dirs


def list_apps(home=None):
    """Return [{id, name, icon, exec}] for every launchable app, sorted."""
    apps, seen = {}, set()
    for d in iter_desktop_dirs(home):
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".desktop"):
                continue
            full = os.path.join(d, fn)
            app_id = fn[:-len(".desktop")]
            if app_id in seen:
                continue
            seen.add(app_id)
            info = parse_desktop_file(full)
            if info and not info.get("nodisplay") and not info.get("hidden"):
                apps[app_id] = {"id": app_id, "name": info.get("name", app_id),
                                "icon": info.get("icon", ""), "exec": info.get("exec", "")}
    return [apps[k] for k in sorted(apps, key=lambda k: apps[k]["name"].lower())]


def parse_desktop_file(path):
    info, in_entry = {}, False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line == "[Desktop Entry]":
                    in_entry = True
                    continue
                if line.startswith("["):
                    in_entry = False
                if not in_entry or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key == "Name":
                    info["name"] = val
                elif key == "Exec":
                    info["exec"] = val
                elif key == "Icon":
                    info["icon"] = val
                elif key == "NoDisplay":
                    info["nodisplay"] = val.lower() == "true"
                elif key == "Hidden":
                    info["hidden"] = val.lower() == "true"
                elif key == "Terminal":
                    info["terminal"] = val.lower() == "true"
    except OSError:
        return None
    return info if info.get("exec") or info.get("name") else None


_FIELD_CODE = re.compile(r"%[fFuUdDnNickvm]")


def clean_exec(exec_line):
    """Strip desktop field codes (%U etc.) for direct subprocess use."""
    return re.sub(r"\s+", " ", _FIELD_CODE.sub("", exec_line or "")).strip()


def list_themes(theme_dirs=None):
    """Installed GTK themes: names of dirs containing gtk-3.0 or gtk-2.0."""
    home = os.path.expanduser(os.environ.get("HOP_HOME", "~"))
    dirs = theme_dirs or [os.path.join(home, ".themes"), "/usr/share/themes"]
    names = set()
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if (os.path.isdir(os.path.join(d, name, "gtk-3.0"))
                    or os.path.isdir(os.path.join(d, name, "gtk-2.0"))):
                names.add(name)
    return sorted(names)


def current_theme(home=None):
    home = home or os.path.expanduser(os.environ.get("HOP_HOME", "~"))
    settings = os.path.join(home, ".config", "gtk-3.0", "settings.ini")
    try:
        with open(settings, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.strip().startswith("gtk-theme-name"):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def apply_theme(theme_name, home=None):
    """Write GTK2 + GTK3 theme config for the user. Returns written paths."""
    home = home or os.path.expanduser(os.environ.get("HOP_HOME", "~"))
    written = []
    cfg3 = os.path.join(home, ".config", "gtk-3.0")
    os.makedirs(cfg3, exist_ok=True)
    settings = os.path.join(cfg3, "settings.ini")
    lines, found = [], False
    try:
        with open(settings, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = ["[Settings]"]
    if not any(l.strip() == "[Settings]" for l in lines):
        lines.insert(0, "[Settings]")
    for i, line in enumerate(lines):
        if line.strip().startswith("gtk-theme-name"):
            lines[i] = "gtk-theme-name=%s" % theme_name
            found = True
    if not found:
        idx = next(i for i, l in enumerate(lines) if l.strip() == "[Settings]")
        lines.insert(idx + 1, "gtk-theme-name=%s" % theme_name)
    with open(settings, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    written.append(settings)
    gtkrc = os.path.join(home, ".gtkrc-2.0")
    with open(gtkrc, "w", encoding="utf-8") as fh:
        fh.write('gtk-theme-name="%s"\n' % theme_name)
    written.append(gtkrc)
    return written


def wallpaper_backends():
    """Detected wallpaper mechanisms, best first."""
    fake = os.environ.get("HOP_FAKE_BACKENDS")
    if fake is not None:
        return [b for b in fake.split(",") if b]
    found = []
    if shutil.which("pcmanfm"):
        found.append("pcmanfm")
    if shutil.which("swaybg"):
        found.append("swaybg")
    return found


def apply_wallpaper(path_or_color, home=None):
    """Apply wallpaper via the best available mechanism.

    path_or_color: absolute image path, or '#rrggbb' for a solid colour.
    Returns (backend, detail). Raises RuntimeError when nothing works.
    """
    home = home or os.path.expanduser(os.environ.get("HOP_HOME", "~"))
    backends = wallpaper_backends()
    if "pcmanfm" in backends:
        if path_or_color.startswith("#"):
            subprocess.run(["pcmanfm", "--wallpaper-mode=color"],
                           check=False, timeout=15)
            return ("pcmanfm", "solid %s" % path_or_color)
        subprocess.run(["pcmanfm", "--set-wallpaper", path_or_color,
                        "--wallpaper-mode=fit"], check=False, timeout=15)
        return ("pcmanfm", path_or_color)
    # Config-file fallback: write the PIXEL desktop config directly.
    pdir = os.path.join(home, ".config", "pcmanfm", "LXDE-pi")
    os.makedirs(pdir, exist_ok=True)
    conf = os.path.join(pdir, "desktop-items-0.conf")
    lines = []
    try:
        with open(conf, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = ["[*]"]
    if not any(l.strip() == "[*]" for l in lines):
        lines.insert(0, "[*]")
    key = "wallpaper"
    val = path_or_color
    wrote = False
    for i, line in enumerate(lines):
        if line.strip().startswith("wallpaper="):
            lines[i] = "wallpaper=%s" % val
            wrote = True
    if not wrote:
        idx = next(i for i, l in enumerate(lines) if l.strip() == "[*]")
        lines.insert(idx + 1, "wallpaper=%s" % val)
    with open(conf, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return ("config-file", conf)


def list_wallpapers(extra_dirs=None):
    """Image files from the system wallpaper dirs, sorted."""
    home = os.path.expanduser(os.environ.get("HOP_HOME", "~"))
    dirs = extra_dirs or [os.path.join(home, "Pictures"),
                          "/usr/share/rpd-wallpaper",
                          "/usr/share/raspberrypi-artwork",
                          "/usr/share/pixmaps"]
    exts = (".png", ".jpg", ".jpeg")
    out = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith(exts):
                out.append(os.path.join(d, fn))
    return out
