#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v git >/dev/null; then
  echo "Please install Git before starting."
  exit 1
fi
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  echo "Please install ffmpeg (including ffprobe) before continuing."
  exit 1
fi
if [[ ! -d .venv ]]; then
  if command -v python3.11 >/dev/null; then
    python3.11 -m venv .venv
  else
    echo "Python 3.11 is required. Install it from python.org first."
    exit 1
  fi
fi
source .venv/bin/activate
python -m pip install -r requirements.txt
python studio.py --ui