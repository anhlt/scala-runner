#!/usr/bin/env sh
set -eux

# 1) Pull the Scala CLI image so it's cached on the node

until docker -H tcp://localhost:2375 info; do
  echo "waiting for dockerd…"
  sleep 1
done


if ! docker pull virtuslab/scala-cli:latest; then
  echo "Failed to pull Scala CLI image. Exiting."
  exit 1
fi

# 2) Exec into uvicorn (replaces this shell, preserves signals)
exec uvicorn scala_runner.main:app --host 0.0.0.0 --port 80