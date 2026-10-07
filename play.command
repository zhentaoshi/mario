#!/bin/zsh
# Double-click this file on macOS, or run ./play.command in Terminal.
cd -- "${0:A:h}" || exit 1
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv || exit 1
fi
if ! .venv/bin/python -c 'import pygame' >/dev/null 2>&1; then
    .venv/bin/python -m pip install -r requirements.txt || exit 1
fi
exec .venv/bin/python game.py "$@"
