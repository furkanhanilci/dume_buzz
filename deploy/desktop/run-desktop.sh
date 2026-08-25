#!/usr/bin/env bash
# Official Buzz Desktop v0.5.18 on an Ubuntu 22.04 host.
#
# The app is NOT rebuilt or patched. The official AppImage payload is run
# against ubuntu:24.04 — the same base image the upstream release job pins
# (release.yml: container: ubuntu:24.04@sha256:4fbb8e6a...) — because the
# bundled binaries need GLIBC_2.38/2.39 and this host provides 2.35.
#
# WebKitGTK: the app asks for WEBKIT_DMABUF_RENDERER_FORCE_SHM=1
# rather than DISABLE_DMABUF_RENDERER, which it warns SIGSEGVs upstream (#3654).
set -euo pipefail
cd "$(dirname "$0")"

NAME=buzz-desktop
IMAGE=buzz-desktop:0.5.18
APP="$PWD/squashfs-root"
DATA="$PWD/appdata"

[ -d "$APP" ] || { echo "missing $APP — run: ./Buzz_0.5.18_amd64.AppImage --appimage-extract"; exit 1; }
mkdir -p "$DATA/.buzz" "$DATA/.local" "$DATA/.config" "$DATA/.cache"

ACTION="${1:-start}"
shift || true
DEEPLINK="${1:-}"   # buzz://join?... when invoked as the scheme handler

case "$ACTION" in
  stop)    docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "stopped"; exit 0 ;;
  logs)    exec docker logs -f "$NAME" ;;
  status)  docker ps -a --filter "name=$NAME" --format '{{.Names}}\t{{.Status}}'; exit 0 ;;
esac

xhost +SI:localuser:"$(id -un)" >/dev/null 2>&1 || true
docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d --name "$NAME" \
  --network host \
  -e DISPLAY="${DISPLAY:-:0}" \
  -e XDG_RUNTIME_DIR=/tmp/runtime \
  -e WEBKIT_DMABUF_RENDERER_FORCE_SHM=1 \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -e GDK_BACKEND=x11 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
  -v "$HOME/.Xauthority:/home/ubuntu/.Xauthority:ro" \
  -v "$APP:/opt/buzz:ro" \
  -v "$DATA/.buzz:/home/ubuntu/.buzz" \
  -v "$DATA/.local:/home/ubuntu/.local" \
  -v "$DATA/.config:/home/ubuntu/.config" \
  -v "$DATA/.cache:/home/ubuntu/.cache" \
  --entrypoint /bin/bash \
  "$IMAGE" -c "mkdir -p /tmp/runtime && chmod 700 /tmp/runtime && exec /opt/buzz/AppRun $(printf '%q' "${DEEPLINK:-}")" >/dev/null

echo "Buzz Desktop starting — relay: http://127.0.0.1:3100"
echo "  logs:   ./run-desktop.sh logs"
echo "  stop:   ./run-desktop.sh stop"
