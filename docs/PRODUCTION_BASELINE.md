# Production baseline

This document records the read-only comparison performed on `arena76-local`
on 2026-08-27. It contains no camera addresses, destination URLs or
credentials. The repository candidate was not deployed during the audit.

## Live state

| Component | Observed state |
|---|---|
| MediaMTX | active and enabled |
| `arena-volleyball@1..6` | active and enabled |
| `arena-curling@1..2` | active and enabled |
| `arena-srt@7`, `arena-srt@9` | inactive and disabled |
| direct-route service | active and enabled |
| canonical camera paths | 8/8 ready |
| required GStreamer elements | 14/14 present |

Both active camera workers use the protected RTMP target file, NVDEC/NVENC,
JPEG preview handling and the decoded-frame `media_progress_watchdog`.

## Repository and deployed differences

The repository is a migration candidate, not a byte-for-byte archive of the
deployed filesystem.

| Area | Deployed host | Repository candidate |
|---|---|---|
| Preview endpoint | existing worker implementation | loaded from protected preview configuration |
| SRT endpoint | older worker implementation | delivered with the systemd credential file |
| SRT log handling | older implementation | credential-aware sanitization |
| Camera unit hardening | 0/10 audited baseline directives | 10/10 |
| SRT unit hardening | 4/10 | 10/10 |
| MediaMTX unit hardening | 3/10 | 10/10 |
| Direct route | historical inline unit logic | validated helper plus external address file |
| MediaMTX config path | `/usr/local/etc/mediamtx/mediamtx-test.yml` | `/etc/mediamtx/mediamtx.yml` |

These differences must be introduced through a separate deployment change
with backups, validation and rollback. Replacing all files at once is not an
approved migration method.

## Private-file permissions

The RTMP target and preview configuration files are mode `0640` and restricted
to the service group. The SRT publisher credential is mode `0600`. Per-stream
SRT files contain path names only and are mode `0644`.

The live MediaMTX configuration is currently mode `0644`. Since a MediaMTX
source configuration can contain private RTSP URLs and camera credentials,
this is tracked as security debt. The intended mode is `0640 root:mediamtx`
or a stricter service-readable equivalent. Permission and path migration must
be tested before restarting MediaMTX.

## Deployment priority

1. Keep observing the healthy 8/8 RTMP baseline.
2. Prepare a staged permission/path migration for MediaMTX.
3. Deploy the external direct-route configuration and helper with rollback.
4. Migrate camera workers and hardened units one instance at a time.
5. Evaluate the optional SRT workers only after the RTMP baseline remains
   stable.
