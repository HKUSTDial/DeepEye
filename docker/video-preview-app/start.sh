#!/bin/sh
# Wait for scene files to be uploaded, then start Vite dev server.
# VideoDeployService uploads config.json + TSX files + scene_registry.ts to /app/src/,
# then signals readiness by creating /app/src/.ready.

echo "[video-preview] Waiting for scene files..."
while [ ! -f /app/src/.ready ]; do
  sleep 0.3
done
echo "[video-preview] Scene files ready. Starting Vite dev server..."
cd /app
exec npm run dev
