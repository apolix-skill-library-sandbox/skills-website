#!/bin/sh
# Build the catalog and serve it on http://localhost:8765
#   ./serve.sh          latest skills from GitHub (uses your `gh` login)
#   ./serve.sh --local  skills from the local clones in ../skills
set -e
cd "$(dirname "$0")"
if [ "$1" = "--local" ]; then
  python3 build.py --local ../skills
else
  GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)" python3 build.py
fi
echo "Serving on http://localhost:8765 (Ctrl+C to stop)"
exec python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
