#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec /usr/bin/python3 -m app.gui "$@"
