"""OCI-backed executors (feature-flag gated)."""

from . import delete_unattached_volume_oci, stop_instance_oci, tag_fix_oci

OCI_EXECUTOR_BY_TYPE = {
    "tag_fix_oci": tag_fix_oci,
    "stop_instance_oci": stop_instance_oci,
    "delete_unattached_volume_oci": delete_unattached_volume_oci,
}
