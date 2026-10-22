#!/usr/bin/env python3
"""PTY test: the installer runs interactively in a real terminal (dry-run,
so nothing is touched), prints the full plan, and the status action works."""
import os
import pty
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FAIL = []


def run_pty(argv, feed=b"", env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    out = []

    def read(fd):
        try:
            data = os.read(fd, 1024)
        except OSError:
            return b""
        out.append(data)
        return data

    pty.spawn(argv, read)
    return b"".join(out).decode("utf-8", "replace")


def check(name, cond):
    print(("ok  " if cond else "FAIL") + " " + name)
    if not cond:
        FAIL.append(name)


# install --dry-run: full plan, no changes, no reboot prompt answered
txt = run_pty(["sh", os.path.join(ROOT, "homeos-plus.sh"), "--dry-run", "install"])
check("plan shows package step", "rpd-wayland-core" in txt and "rpd-theme" in txt)
check("plan shows autologin user", "autologin-user=" in txt)
check("plan shows desktop entries", "desktop entries" in txt)
check("plan shows state file", "/var/lib/homeos-plus/state" in txt)
check("dry run says nothing changed", "nothing was changed" in txt)
check("no real state written", not os.path.exists("/var/lib/homeos-plus/state"))

# uninstall --dry-run
txt = run_pty(["sh", os.path.join(ROOT, "homeos-plus.sh"), "--dry-run", "uninstall"])
check("uninstall restores console boot", "console boot" in txt)
check("uninstall mentions package removal hint", "apt-get remove" in txt)

# status
txt = run_pty(["sh", os.path.join(ROOT, "homeos-plus.sh"), "status"])
check("status runs and reports", "HomeOS Plus" in txt and "installed:" in txt)

# bad action
pid = run_pty(["sh", os.path.join(ROOT, "homeos-plus.sh"), "bogus"])
check("bad action prints usage", "install|uninstall|status" in pid)

print()
if FAIL:
    print("%d FAILURES" % len(FAIL))
    sys.exit(1)
print("all PTY tests passed")
