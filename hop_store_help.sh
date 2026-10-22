#!/bin/sh
# Shown in a terminal when the Pi App Store is not installed yet.
cat <<'MSG'

  HomeOS Plus - App Store

  The Pi App Store is not installed yet. To add it, review
  the install script (it's source you run as you), then run:

      git clone https://github.com/Greenisus1/pi-app-store
      cd pi-app-store
      bash install.sh --local

  It asks before installing anything. When it finishes,
  press the App Store button again.

  Close this window when you're done.

MSG
exec sh -i
