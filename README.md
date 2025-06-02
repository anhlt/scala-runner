# Scala-Runner API

A small FastAPI service that wraps a `scala-cli` Docker invocation.  
It allows you to POST Scala code (or a local `.sc` file path) and returns the output.

---

## Prerequisites

- Python 3.9+  
- Docker installed and running  
- (Optional) `git` if you clone the repo

---

## Setup & Run

1. Clone or copy this repo:

   ```bash
   git clone https://your.repo.url/scala_runner_fastapi.git
   cd scala_runner_fastapi