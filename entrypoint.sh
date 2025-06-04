#!/usr/bin/env sh
set -eux

# 1) Pull the Scala CLI image so it's cached on the node

until docker info; do
  echo "waiting for dockerd…"
  sleep 1
done


if ! docker pull virtuslab/scala-cli:latest; then
  echo "Failed to pull Scala CLI image. Exiting."
  exit 1
fi

# 2) Run Scala CLI to compile the Scala app
echo 'println("hello")' > /tmp/hello.sc

if ! docker run --rm -v /tmp/:/tmp/   virtuslab/scala-cli:latest run /tmp/hello.sc --scala 2.13 --verbose --progress --platform=jvm; then
  echo "Failed to compile Scala app. Exiting."
  exit 1
fi

if ! docker run --rm -v /tmp/:/tmp/   virtuslab/scala-cli:latest run /tmp/hello.sc --scala 3.6.4 --verbose --progress --platform=jvm; then
  echo "Failed to compile Scala app. Exiting."
  exit 1
fi


# 2) Exec into uvicorn (replaces this shell, preserves signals)
exec uvicorn scala_runner.main:app --host 0.0.0.0 --port 80