#!/usr/bin/env bash

set -euo pipefail

PATH_NAME="${1:?MediaMTX path required}"
RTMP_URL="${2:?RTMP URL required}"

exec gst-launch-1.0 -e \
  rtspsrc \
    location="rtsp://127.0.0.1:8554/${PATH_NAME}" \
    protocols=tcp \
    latency=500 \
    tcp-timeout=10000000 \
    name=src \
  flvmux name=mux streamable=true \
    ! rtmpsink location="${RTMP_URL}" \
  src. ! "application/x-rtp,media=video,payload=98,encoding-name=H265" \
    ! queue \
    ! rtph265depay \
    ! h265parse \
    ! nvh265dec \
    ! nvh264enc \
        preset=p4 \
        rc-mode=cbr \
        bitrate=6000 \
        gop-size=60 \
        zerolatency=true \
    ! video/x-h264,profile=high \
    ! h264parse config-interval=-1 \
    ! queue \
    ! mux. \
  src. ! "application/x-rtp,media=audio,payload=97,encoding-name=MPEG4-GENERIC" \
    ! queue \
    ! rtpmp4gdepay \
    ! aacparse \
    ! queue \
    ! mux.
