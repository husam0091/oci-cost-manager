"""Action executor registry."""

from __future__ import annotations

from . import cleanup_unattached_volume, notify_only, stop_idle_instance, tag_fix

EXECUTOR_BY_TYPE = {
    "notify_only": notify_only,
    "cleanup_unattached_volume": cleanup_unattached_volume,
    "stop_idle_instance": stop_idle_instance,
    "tag_fix": tag_fix,
}
