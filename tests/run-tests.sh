#!/bin/sh
# HomeOS Plus test suite: shell syntax, python compile, unit tests, PTY tests.
set -eu
cd -- "$(dirname -- "$0")/.."
for f in app-store.sh homeos-plus.sh hop_store_help.sh tests/run-tests.sh; do
    sh -n "$f" && echo "syntax ok: $f"
done
python3 -m py_compile hop_common.py hop_dock.py hop_settings.py hop_music.py
echo "python compile ok"
rm -rf __pycache__
python3 tests/unit_tests.py
python3 tests/pty_test.py
echo "ALL TESTS PASSED"
