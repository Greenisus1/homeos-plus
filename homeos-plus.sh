#!/bin/sh
# HomeOS Plus installer: console Home Pi / Pi OS Lite -> autologin PIXEL desktop
# with the HomeOS Plus dock (Terminal + Exit first), Settings, and App Store entry.
# Idempotent. --dry-run prints the plan without changing anything.
set -eu

VERSION="1.0.0"
STATE_DIR=/var/lib/homeos-plus
STATE_FILE=$STATE_DIR/state
LIGHTDM_DROPIN=/etc/lightdm/lightdm.conf.d/60-homeos-plus.conf
DRY=0
[ "${1:-}" = "--dry-run" ] && { DRY=1; shift; }
[ "${HOP_DRY_RUN:-0}" = "1" ] && DRY=1

say() { printf '%s\n' "$*"; }
run() { if [ "$DRY" = 1 ]; then say "  plan: $*"; else "$@"; fi; }

as_root() {
    if [ "$(id -u)" -eq 0 ]; then run "$@";
    elif [ "$DRY" = 1 ]; then say "  plan: sudo $*";
    else sudo "$@"; fi
}

target_user() {
    if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
        printf '%s' "$SUDO_USER"
    else
        printf '%s' "$(id -un)"
    fi
}

os_ok() {
    [ -r /etc/os-release ] || return 1
    grep -qiE '^ID=(raspbian|debian)' /etc/os-release
}

cmd_install() {
    say "HomeOS Plus $VERSION - install"
    USER_NAME=$(target_user)
    USER_HOME=$(getent passwd "$USER_NAME" | cut -d: -f6)
    [ -n "$USER_HOME" ] || { say "Could not find your user account." >&2; exit 1; }
    os_ok || say "Note: this is meant for Raspberry Pi OS (or Debian) - continuing anyway."
    HERE=$(cd -- "$(dirname -- "$0")" && pwd)

    say "1/5 Installing the desktop packages (this is the big step, a few minutes)..."
    if [ "$DRY" = 1 ]; then
        say "  plan: sudo apt-get update"
        say "  plan: sudo apt-get install -y --no-install-recommends rpd-wayland-core"
        say "  plan: sudo apt-get install -y rpd-theme rpd-preferences rpd-utilities lxterminal python3-tk alsa-utils"
    else
        as_root env DEBIAN_FRONTEND=noninteractive apt-get update
        as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends rpd-wayland-core
        as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y rpd-theme rpd-preferences rpd-utilities lxterminal python3-tk alsa-utils
        command -v lightdm >/dev/null 2>&1 || [ -e /etc/init.d/lightdm ] || {
            say "The desktop packages installed but lightdm is missing - cannot enable the desktop." >&2
            exit 1
        }
    fi

    say "2/5 Setting boot to the desktop with autologin as $USER_NAME..."
    as_root systemctl set-default graphical.target
    if [ "$DRY" = 1 ]; then
        say "  plan: write $LIGHTDM_DROPIN (autologin-user=$USER_NAME)"
    else
        as_root mkdir -p /etc/lightdm/lightdm.conf.d
        printf '[Seat:*]\nautologin-user=%s\n' "$USER_NAME" | as_root tee "$LIGHTDM_DROPIN" >/dev/null
        as_root systemctl enable lightdm >/dev/null 2>&1 || true
    fi

    say "3/5 Adding the HomeOS Plus apps (Terminal, Exit, App Store, Settings)..."
    APPS_DIR=$USER_HOME/.local/share/applications
    AUTOSTART_DIR=$USER_HOME/.config/autostart
    if [ "$DRY" = 1 ]; then
        say "  plan: write desktop entries into $APPS_DIR and autostart into $AUTOSTART_DIR"
    else
        mkdir -p "$APPS_DIR" "$AUTOSTART_DIR"
        cat > "$APPS_DIR/homeos-plus-terminal.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Terminal
Comment=Open a terminal
Exec=x-terminal-emulator
Icon=utilities-terminal
Categories=System;TerminalEmulator;
DESK
        cat > "$APPS_DIR/homeos-plus-exit.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Exit to Console
Comment=Quit the desktop back to the console
Exec=sh -c "sudo -n systemctl isolate multi-user.target || x-terminal-emulator -e 'echo sudo needs a password: run sudo systemctl isolate multi-user.target; exec sh'"
Icon=system-log-out
Categories=System;
DESK
        cat > "$APPS_DIR/homeos-plus-settings.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=HomeOS Plus Settings
Comment=Wallpaper, theme, dock layout and dock apps
Exec=python3 $HERE/hop_settings.py
Icon=preferences-system
Categories=Settings;
DESK
        cat > "$APPS_DIR/homeos-plus-music.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Music
Comment=Play .hs HomeOS songs (letters are notes, number = chord kind)
Exec=x-terminal-emulator -e "python3 $HERE/hop_music.py; exec sh"
Icon=audio-x-generic
Categories=AudioVideo;
DESK
        cat > "$AUTOSTART_DIR/homeos-plus-dock.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=HomeOS Plus Dock
Exec=python3 $HERE/hop_dock.py
X-GNOME-Autostart-enabled=true
DESK
        chown -R "$USER_NAME:$USER_NAME" "$USER_HOME/.local/share/applications" "$USER_HOME/.config/autostart" 2>/dev/null || true
    fi

    say "4/5 Saving install state..."
    if [ "$DRY" = 1 ]; then
        say "  plan: write $STATE_FILE"
    else
        as_root mkdir -p "$STATE_DIR"
        printf 'version=%s\nuser=%s\n' "$VERSION" "$USER_NAME" | as_root tee "$STATE_FILE" >/dev/null
    fi

    say "5/5 Done."
    say ""
    say "HomeOS Plus is installed. Your console is always one keypress away:"
    say "Ctrl+Alt+F1 (back to the desktop with Ctrl+Alt+F7), login homepi if asked."
    if [ "$DRY" = 1 ]; then
        say "(dry run - nothing was changed)"
    else
        printf 'Reboot now to enter your desktop? [Y/n] '
        read -r ans || ans=n
        case "$ans" in
            n|N|no|NO) say "Reboot whenever you're ready: sudo reboot" ;;
            *) as_root systemctl reboot ;;
        esac
    fi
}

cmd_uninstall() {
    say "HomeOS Plus - uninstall"
    USER_NAME=$(target_user)
    USER_HOME=$(getent passwd "$USER_NAME" | cut -d: -f6)
    say "Restoring console boot (desktop packages stay installed; nothing else is removed)."
    as_root systemctl set-default multi-user.target
    if [ "$DRY" = 1 ]; then
        say "  plan: remove $LIGHTDM_DROPIN, desktop entries, autostart, $STATE_FILE"
    else
        as_root rm -f "$LIGHTDM_DROPIN"
        rm -f "$USER_HOME/.local/share/applications/homeos-plus-terminal.desktop" \
              "$USER_HOME/.local/share/applications/homeos-plus-exit.desktop" \
              "$USER_HOME/.local/share/applications/homeos-plus-settings.desktop" \
              "$USER_HOME/.local/share/applications/homeos-plus-music.desktop" \
              "$USER_HOME/.config/autostart/homeos-plus-dock.desktop" 2>/dev/null || true
        as_root rm -f "$STATE_FILE"
    fi
    say "Done. Next boot goes to the console. Remove the desktop packages too with:"
    say "  sudo apt-get remove --purge rpd-wayland-core rpd-theme rpd-preferences rpd-utilities"
}

cmd_status() {
    say "HomeOS Plus $VERSION"
    if [ -r "$STATE_FILE" ]; then
        say "installed: yes ($(cat $STATE_FILE | tr '\n' ' '))"
    else
        say "installed: no"
    fi
    cur=$(readlink -f /etc/systemd/system/default.target 2>/dev/null || echo unknown)
    case "$cur" in
        *graphical.target) say "boot: desktop" ;;
        *multi-user.target) say "boot: console" ;;
        *) say "boot: $cur" ;;
    esac
    if [ -r "$LIGHTDM_DROPIN" ]; then
        say "autologin: $(grep autologin-user $LIGHTDM_DROPIN | cut -d= -f2)"
    fi
    say "Run from the Pi App Store to manage. Settings and the dock live in the desktop."
}

case "${1:-status}" in
    install) cmd_install ;;
    uninstall) cmd_uninstall ;;
    status) cmd_status ;;
    *) say "Use: sh homeos-plus.sh [--dry-run] install|uninstall|status"; exit 1 ;;
esac
