# Security

## Secrets excluded from Git

- private RTSP camera URLs and credentials;
- remote RTMP destinations and publish keys;
- SRT username, password and endpoint credentials;
- preview bearer token;
- live MediaMTX configuration;
- the real destination used by the VPN-bypass policy rule.

Only variable names and explicit `CHANGE_ME` examples are tracked.

## Runtime handling

RTMP workers read destination URLs from `/etc/arena76/rtmp-targets.env` and
assign URLs through GStreamer properties instead of command-line arguments.
Preview tokens are used only in an HTTPS Authorization header. SRT credentials
are delivered with systemd `LoadCredential` and are scrubbed from normal log
messages.

## Service isolation

Packaged units use dedicated non-login users, `NoNewPrivileges`, read-only
system paths, kernel/control-group protection, restricted address families and
empty capability sets. Camera workers retain access to the host NVIDIA device
namespace because NVDEC/NVENC requires it; GPU device restrictions must be
introduced only after testing all required device nodes on the actual host.

The route service is the only packaged unit retaining `CAP_NET_ADMIN`.
