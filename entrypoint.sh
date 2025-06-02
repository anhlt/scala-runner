#!/usr/bin/env sh
set -eux

# 1) Pull the Scala CLI image so it's cached on the node


# 2) Exec into uvicorn (replaces this shell, preserves signals)
exec uvicorn main:app --host 0.0.0.0 --port 80