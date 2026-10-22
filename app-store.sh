#!/bin/sh
# pi-app-store: 1
# pi-app-store-category: desktop-apps
set -eu
cd -- "$(dirname -- "$0")"
case "${1:-run}" in
    install) sh homeos-plus.sh install ;;
    uninstall) sh homeos-plus.sh uninstall ;;
    run) sh homeos-plus.sh status ;;
    *) echo 'Use: bash app-store.sh install | uninstall | run'; exit 1 ;;
esac
