# Deployment

This first repository version is a reproducible, secret-free baseline of the
running host. It must not be copied over production as a bulk operation.

## Prerequisites

- Ubuntu 26.04;
- MediaMTX 1.20.1;
- GStreamer 1.28 with the base, good, bad, ugly, extra and tools packages;
- Python 3 with PyGObject;
- NVIDIA driver and working `nvh265dec` / `nvh264enc` elements;
- system users `mediamtx` and `arena-stream`;
- group `arena76-stream` for protected target configuration.

Run the read-only validation first:

```bash
./scripts/validate.sh
```

## Private files

Prepare these outside Git with the schemas from `config/`:

- `/etc/arena76/rtmp-targets.env`;
- `/etc/arena76/preview-upload.env`;
- `/etc/arena76/direct-route.env`;
- `/etc/arena76/srt-streams/N.env`;
- `/etc/arena-srt/publisher.env`;
- `/etc/mediamtx/mediamtx.yml`.

Private files should normally be owned by root and readable only by the exact
service group that requires them. The SRT credential file must remain mode
`0600` because systemd copies it into the service credential directory.

## Migration policy

The current live host uses historical filesystem paths and less-hardened unit
definitions. A later deployment PR must stage files, run worker `--check`
validation, back up every replaced file and provide an automatic rollback.
This baseline intentionally contains no `apply` command and never restarts
live camera services.
