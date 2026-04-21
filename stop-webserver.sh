#!/usr/bin/env bash
set -euo pipefail

echo "Stopping tiny web page server ..."

pkill -f "python3 -m http.server 8080" || true

echo "Web server stopped."