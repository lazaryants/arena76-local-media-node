# Architecture

## Inputs

MediaMTX pulls eight H.265/AAC RTSP camera streams from the private Arena76
LAN. Canonical local paths are `volleyball1` through `volleyball6` and
`curling1` through `curling2`.

MediaMTX listens on RTSP `8554`, RTMP `1935`, HLS `8888` and WebRTC `8889`.
Its API and metrics listeners are loopback-only on `9997` and `9998`.

## Active RTMP workers

Each active systemd template instance starts one Python/GStreamer process.
Camera and destination URLs are loaded from protected configuration and are
assigned through GStreamer properties, so they do not appear in the process
command line.

The worker performs:

1. RTSP/RTP H.265 and AAC reception over TCP;
2. NVIDIA H.265 hardware decode;
3. NVIDIA H.264 encode at 6 Mbit/s, GOP 60, preset `p4`;
4. direct AAC passthrough into FLV/RTMP;
5. a leaky half-frame-per-second JPEG branch for monitoring previews;
6. atomic local preview storage and authenticated HTTPS upload;
7. a decoded-frame watchdog that lets systemd recover a stalled pipeline.

## Optional SRT worker

`arena-srt@.service` waits for a ready local MediaMTX path, transcodes the
video with the same NVENC profile and publishes MPEG-TS over SRT. The endpoint,
username and password are supplied through a systemd credential file. Per-unit
environment files contain only local and remote path names.

## VPN bypass

The desktop has a user VPN interface. A dedicated oneshot service installs one
policy-routing rule for the configured remote media address. The address is
kept in `/etc/arena76/direct-route.env`, outside Git.
