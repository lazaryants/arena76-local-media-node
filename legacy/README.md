# Legacy launchers

The two launchers and matching systemd units document the disabled historical
`cam116 → place7` and `cam117 → place8` configuration. They embedded complete
camera and destination URLs in command arguments and are therefore unsuitable
for reactivation.

The current `arena-curling@.service` workers replace this design: URLs are read
from protected files and assigned through GStreamer properties. Legacy files
remain examples only and are never installed by project tooling.
