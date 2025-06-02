#!/usr/bin/env sh
set -eux

# 1) Pull the Scala CLI image so it's cached on the node

if ! docker pull virtuslab/scala-cli:latest; then
  echo "Failed to pull Scala CLI image. Exiting."
  exit 1
fi

# 2) Exec into uvicorn (replaces this shell, preserves signals)
exec uvicorn main:app --host 0.0.0.0 --port 80