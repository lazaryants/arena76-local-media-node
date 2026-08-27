#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    pwd
)"

cd "${PROJECT_ROOT}"

echo "===== PYTHON SYNTAX ====="
python3 -m py_compile \
    workers/arena-curling-worker \
    workers/arena-volleyball-worker \
    workers/srt-worker.py

echo
echo "===== SHELL SYNTAX ====="
bash -n \
    scripts/direct-route.sh \
    scripts/run-curling.sh \
    scripts/run-volleyball.sh \
    scripts/validate.sh \
    legacy/cam116-place7.sh.example \
    legacy/cam117-place8.sh.example

echo
echo "===== GSTREAMER ELEMENTS ====="
if command -v gst-inspect-1.0 >/dev/null; then
    for element in \
        rtspsrc \
        rtph265depay \
        h265parse \
        nvh265dec \
        nvh264enc \
        flvmux \
        rtmpsink \
        videorate \
        videoscale \
        videoconvert \
        jpegenc \
        appsink \
        mpegtsmux \
        srtsink
    do
        gst-inspect-1.0 "${element}" >/dev/null
        printf 'present: %s\n' "${element}"
    done
else
    echo "Skipped: gst-inspect-1.0 is not installed on this validation host"
fi

echo
echo "===== SYSTEMD UNITS ====="
VERIFY_OUTPUT="$(
    systemd-analyze verify \
        systemd/*.service \
        2>&1 \
        || true
)"
printf '%s\n' "${VERIFY_OUTPUT}"

PROJECT_VERIFY_OUTPUT="$(
    printf '%s\n' "${VERIFY_OUTPUT}" \
        | grep -E \
            '(arena-curling@[^ :/]*\.service|arena-mediamtx-direct-route\.service|arena-srt@[^ :/]*\.service|arena-volleyball@[^ :/]*\.service|mediamtx\.service)' \
        || true
)"

UNEXPECTED_VERIFY_OUTPUT="$(
    printf '%s\n' "${PROJECT_VERIFY_OUTPUT}" \
        | grep -vE \
            'Command /usr/local/.+ is not executable: No such file or directory' \
        || true
)"

if test -n "${UNEXPECTED_VERIFY_OUTPUT}"; then
    echo "Unexpected systemd validation output" >&2
    exit 1
fi

echo
echo "===== TESTS ====="
PYTHONPATH="${PROJECT_ROOT}" \
    python3 -m unittest discover \
        -s tests \
        -p 'test_*.py' \
        -v

echo
echo "Validation completed"
echo "No production file or service was changed"
