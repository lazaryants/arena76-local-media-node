# Operations

## Expected services

The normal production state is:

- `mediamtx.service` active and enabled;
- `arena-mediamtx-direct-route.service` active and enabled;
- `arena-volleyball@1..6.service` active and enabled;
- `arena-curling@1..2.service` active and enabled;
- SRT template instances disabled unless a controlled test is running.

## Read-only checks

```bash
systemctl --failed
systemctl is-active mediamtx arena-mediamtx-direct-route
systemctl is-active arena-volleyball@{1,2,3,4,5,6}
systemctl is-active arena-curling@{1,2}
curl --silent http://127.0.0.1:9997/v3/paths/list
nvidia-smi
```

Do not print complete process arguments, environment files or MediaMTX source
URLs during diagnostics. GStreamer error output must be passed through the
workers' sanitizers before it reaches the journal.

## Recovery

A single worker may be restarted independently after its source and destination
are verified. Avoid restarting MediaMTX while the eight workers are healthy,
because all local RTSP sessions depend on it.

The route service changes only one destination-specific policy rule. Validate
its candidate unit and helper script before replacing the historical unit.
