#!/usr/bin/env python3

import os
import sys
import signal
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import re
import gi

gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gst, GLib

Gst.init(None)

if len(sys.argv) != 3:
    print(
        "Usage: srt-worker.py <source-path> <remote-path>",
        file=sys.stderr,
    )
    sys.exit(2)

source_path = sys.argv[1]
remote_path = sys.argv[2]


def wait_for_local_source(path, timeout=120):
    url = f"http://127.0.0.1:9997/v3/paths/get/{path}"
    deadline = time.monotonic() + timeout
    announced = False

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.load(response)

            if data.get("ready") is True and data.get("online") is True:
                print(f"Local source {path} is ready", flush=True)
                return

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ConnectionError,
            json.JSONDecodeError,
        ):
            pass

        if not announced:
            print(f"Waiting for local source {path}...", flush=True)
            announced = True

        time.sleep(2)

    raise RuntimeError(
        f"Local source {path} was not ready within {timeout} seconds"
    )


wait_for_local_source(source_path)

credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
if not credential_dir:
    raise RuntimeError("CREDENTIALS_DIRECTORY is not set")

credential_file = os.path.join(
    credential_dir,
    "publisher.env",
)

values = {}

with open(
    credential_file,
    "r",
    encoding="utf-8",
) as fh:
    for raw_line in fh:
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        values[key.strip()] = value

srt_user = values.get("SRT_USER")
srt_password = values.get("SRT_PASSWORD")
srt_endpoint = values.get("SRT_ENDPOINT")

if not srt_user or not srt_password or not srt_endpoint:
    raise RuntimeError(
        "SRT_USER, SRT_PASSWORD or SRT_ENDPOINT is missing"
    )

parsed_endpoint = urllib.parse.urlsplit(
    srt_endpoint
)
if (
    parsed_endpoint.scheme != "srt"
    or not parsed_endpoint.hostname
    or parsed_endpoint.port is None
    or parsed_endpoint.username is not None
    or parsed_endpoint.password is not None
    or parsed_endpoint.query
    or parsed_endpoint.fragment
):
    raise RuntimeError(
        "SRT_ENDPOINT must contain only srt://host:port"
    )

pipeline_description = f"""
rtspsrc
    location=rtsp://127.0.0.1:8554/{source_path}
    protocols=tcp
    latency=500
    name=src

mpegtsmux
    name=mux
    alignment=7

src.
    ! application/x-rtp,media=video,encoding-name=H265
    ! queue
    ! rtph265depay
    ! h265parse
    ! nvh265dec
    ! nvh264enc
        preset=p4
        rc-mode=cbr
        bitrate=6000
        gop-size=60
        bframes=0
        repeat-sequence-header=true
        zerolatency=true
    ! video/x-h264,profile=high
    ! h264parse
        config-interval=-1
    ! video/x-h264,stream-format=byte-stream,alignment=au
    ! queue
    ! mux.

src.
    ! application/x-rtp,media=audio,encoding-name=MPEG4-GENERIC
    ! queue
    ! rtpmp4gdepay
    ! aacparse
    ! queue
    ! mux.

mux.
    ! srtsink
        name=srtout
        mode=caller
        latency=500
        auto-reconnect=true
"""

pipeline = Gst.parse_launch(
    pipeline_description
)

srtout = pipeline.get_by_name("srtout")

if srtout is None:
    raise RuntimeError(
        "Unable to find srtsink element"
    )

srtout.set_property(
    "uri",
    srt_endpoint,
)

streamid = (
    f"publish:{remote_path}:"
    f"{srt_user}:{srt_password}"
)

secrets = (
    srt_user,
    srt_password,
    srt_endpoint,
    streamid,
)

srtout.set_property(
    "streamid",
    streamid,
)

# Remove copies from Python variables after property assignment.
srt_password = None
streamid = None
values.clear()


def sanitize(message):
    result = str(message)
    for secret in secrets:
        if secret:
            result = result.replace(
                secret,
                "[MEDIA CREDENTIAL HIDDEN]",
            )
    return re.sub(
        r"(?:rtsp|srt)://[^\s]+",
        "MEDIA_URL://HIDDEN",
        result,
    )

loop = GLib.MainLoop()

bus = pipeline.get_bus()
bus.add_signal_watch()


def on_message(bus, message):
    msg_type = message.type

    if msg_type == Gst.MessageType.ERROR:
        err, debug = message.parse_error()

        print(
            f"GStreamer ERROR: {sanitize(err)}",
            file=sys.stderr,
            flush=True,
        )

        if debug:
            print(
                f"Debug: {sanitize(debug)}",
                file=sys.stderr,
                flush=True,
            )

        loop.quit()

    elif msg_type == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()

        print(
            f"GStreamer WARNING: {sanitize(err)}",
            file=sys.stderr,
            flush=True,
        )

        if debug:
            print(
                f"Debug: {sanitize(debug)}",
                file=sys.stderr,
                flush=True,
            )

    elif msg_type == Gst.MessageType.EOS:
        print(
            "GStreamer EOS",
            flush=True,
        )
        loop.quit()


bus.connect(
    "message",
    on_message,
)


def stop_handler(signum, frame):
    print(
        f"Signal {signum} received, stopping",
        flush=True,
    )
    loop.quit()


signal.signal(
    signal.SIGTERM,
    stop_handler,
)

signal.signal(
    signal.SIGINT,
    stop_handler,
)

print(
    f"Starting SRT worker: "
    f"{source_path} -> {remote_path}",
    flush=True,
)

result = pipeline.set_state(
    Gst.State.PLAYING
)

if result == Gst.StateChangeReturn.FAILURE:
    pipeline.set_state(
        Gst.State.NULL
    )
    raise RuntimeError(
        "Unable to set pipeline to PLAYING"
    )

try:
    loop.run()
finally:
    print(
        "Stopping pipeline",
        flush=True,
    )

    pipeline.send_event(
        Gst.Event.new_eos()
    )

    pipeline.set_state(
        Gst.State.NULL
    )

print(
    "SRT worker stopped",
    flush=True,
)
