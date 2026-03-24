"""OCI SDK client service for connecting to Oracle Cloud Infrastructure."""

import oci
from typing import Optional, Any
from pathlib import Path
import configparser
from ntpath import basename as win_basename

from core.config import get_settings, get_oci_config_path
from core.database import SessionLocal
from core.errors import raise_production_block
from core.models import Setting
from core.secrets import resolve_secret
from services.oci_credentials import get_oci_runtime_credentials


class OCIClientService:
    """Service for managing OCI SDK clients."""
    
    def __init__(self, profile_name: Optional[str] = None, runtime_oci: Optional[dict[str, Any]] = None):
        """Initialize OCI client service.
        
        Args:
            profile_name: OCI config profile name. Defaults to settings value.
        """
        settings = get_settings()
        runtime = runtime_oci or _load_runtime_oci_settings()
        self.auth_mode = (runtime.get("auth_mode") or "profile").lower()
        self.profile_name = profile_name or runtime.get("config_profile") or settings.oci_config_profile
        runtime_path = runtime.get("config_file")
        self.config_path = Path(runtime_path).expanduser() if runtime_path else get_oci_config_path()
        self.runtime_oci = runtime
        self._config = None
        self._identity_client = None
        self._database_client = None
        self._mysql_client = None
        self._compute_client = None
        self._usage_client = None
        self._virtual_network_client = None
        self._block_storage_client = None
        self._file_storage_client = None
        self._object_storage_client = None
    
    @property
    def config(self) -> dict:
        """Get OCI configuration."""
        if self._config is None:
            _validate_runtime_path_mode(self.runtime_oci)
            if self.auth_mode == "direct":
                self._config = _build_direct_config(self.runtime_oci)
            else:
                app_cfg = get_settings()
                if app_cfg.app_env.lower() == "production" and not app_cfg.allow_oci_file_path_mode:
                    raise_production_block("oci_config_file", None)
                self._config = _load_config_profile(str(self.config_path), self.profile_name)
            _normalize_key_file_path(self._config)
            oci.config.validate_config(self._config)
        return self._config
    
    @property
    def tenancy_id(self) -> str:
        """Get the tenancy OCID from config."""
        return self.config["tenancy"]
    
    @property
    def region(self) -> str:
        """Get the region from config."""
        return self.config["region"]
    
    @property
    def identity_client(self) -> oci.identity.IdentityClient:
        """Get Identity client for compartments and users."""
        if self._identity_client is None:
            self._identity_client = oci.identity.IdentityClient(self.config)
        return self._identity_client
    
    @property
    def database_client(self) -> oci.database.DatabaseClient:
        """Get Database client for Oracle DB systems."""
        if self._database_client is None:
            self._database_client = oci.database.DatabaseClient(self.config)
        return self._database_client
    
    @property
    def mysql_client(self) -> oci.mysql.DbSystemClient:
        """Get MySQL client for MySQL DB systems."""
        if self._mysql_client is None:
            self._mysql_client = oci.mysql.DbSystemClient(self.config)
        return self._mysql_client
    
    @property
    def compute_client(self) -> oci.core.ComputeClient:
        """Get Compute client for instances (SQL Server VMs)."""
        if self._compute_client is None:
            self._compute_client = oci.core.ComputeClient(self.config)
        return self._compute_client
    
    @property
    def usage_client(self) -> oci.usage_api.UsageapiClient:
        """Get Usage API client for cost data."""
        if self._usage_client is None:
            # Add timeout for usage API calls
            self._usage_client = oci.usage_api.UsageapiClient(
                self.config,
                timeout=(30, 120)  # (connect_timeout, read_timeout)
            )
        return self._usage_client
    
    @property
    def virtual_network_client(self) -> oci.core.VirtualNetworkClient:
        """Get Virtual Network client for VNICs and IPs."""
        if self._virtual_network_client is None:
            self._virtual_network_client = oci.core.VirtualNetworkClient(self.config)
        return self._virtual_network_client
    
    @property
    def file_storage_client(self) -> oci.file_storage.FileStorageClient:
        """Get File Storage client."""
        if self._file_storage_client is None:
            self._file_storage_client = oci.file_storage.FileStorageClient(self.config)
        return self._file_storage_client

    @property
    def block_storage_client(self) -> oci.core.BlockstorageClient:
        """Get Block Storage client for volumes and backups."""
        if self._block_storage_client is None:
            self._block_storage_client = oci.core.BlockstorageClient(self.config)
        return self._block_storage_client
    
    @property
    def object_storage_client(self) -> oci.object_storage.ObjectStorageClient:
        """Get Object Storage client."""
        if self._object_storage_client is None:
            self._object_storage_client = oci.object_storage.ObjectStorageClient(self.config)
        return self._object_storage_client
    
    def get_tenancy(self) -> oci.identity.models.Tenancy:
        """Get tenancy details."""
        return self.identity_client.get_tenancy(self.tenancy_id).data
    
    def list_compartments(self, compartment_id: Optional[str] = None) -> list:
        """List all compartments in the tenancy.
        
        Args:
            compartment_id: Parent compartment OCID. Defaults to tenancy root.
            
        Returns:
            List of compartment objects.
        """
        compartment_id = compartment_id or self.tenancy_id
        
        compartments = []
        response = self.identity_client.list_compartments(
            compartment_id=compartment_id,
            compartment_id_in_subtree=True,
            lifecycle_state="ACTIVE"
        )
        compartments.extend(response.data)
        
        # Handle pagination
        while response.has_next_page:
            response = self.identity_client.list_compartments(
                compartment_id=compartment_id,
                compartment_id_in_subtree=True,
                lifecycle_state="ACTIVE",
                page=response.next_page
            )
            compartments.extend(response.data)
        
        return compartments
    
    def list_db_systems(self, compartment_id: str) -> list:
        """List Oracle DB systems in a compartment.
        
        Args:
            compartment_id: Compartment OCID.
            
        Returns:
            List of DB system objects.
        """
        db_systems = []
        response = self.database_client.list_db_systems(compartment_id=compartment_id)
        db_systems.extend(response.data)
        
        while response.has_next_page:
            response = self.database_client.list_db_systems(
                compartment_id=compartment_id,
                page=response.next_page
            )
            db_systems.extend(response.data)
        
        return db_systems
    
    def list_mysql_db_systems(self, compartment_id: str) -> list:
        """List MySQL DB systems in a compartment.
        
        Args:
            compartment_id: Compartment OCID.
            
        Returns:
            List of MySQL DB system objects.
        """
        mysql_systems = []
        response = self.mysql_client.list_db_systems(compartment_id=compartment_id)
        mysql_systems.extend(response.data)
        
        while response.has_next_page:
            response = self.mysql_client.list_db_systems(
                compartment_id=compartment_id,
                page=response.next_page
            )
            mysql_systems.extend(response.data)
        
        return mysql_systems
    
    def list_instances(self, compartment_id: str) -> list:
        """List compute instances in a compartment.
        
        Args:
            compartment_id: Compartment OCID.
            
        Returns:
            List of instance objects.
        """
        instances = []
        response = self.compute_client.list_instances(compartment_id=compartment_id)
        instances.extend(response.data)
        
        while response.has_next_page:
            response = self.compute_client.list_instances(
                compartment_id=compartment_id,
                page=response.next_page
            )
            instances.extend(response.data)
        
        return instances
    
    def get_instance_image(self, image_id: str) -> Optional[oci.core.models.Image]:
        """Get image details for an instance.
        
        Args:
            image_id: Image OCID.
            
        Returns:
            Image object or None if not found.
        """
        try:
            return self.compute_client.get_image(image_id).data
        except oci.exceptions.ServiceError:
            return None
    
    def get_instance_private_ip(self, instance_id: str, compartment_id: str) -> Optional[str]:
        """Get private IP for an instance via VNIC attachments."""
        try:
            vnic_attachments = self.compute_client.list_vnic_attachments(
                compartment_id=compartment_id,
                instance_id=instance_id
            ).data
            for att in vnic_attachments:
                if att.lifecycle_state == "ATTACHED":
                    vnic = self.virtual_network_client.get_vnic(att.vnic_id).data
                    return vnic.private_ip
        except Exception:
            pass
        return None
    
    def list_file_systems(self, compartment_id: str, availability_domain: str) -> list:
        """List file systems in a compartment/AD."""
        try:
            return self.file_storage_client.list_file_systems(
                compartment_id=compartment_id,
                availability_domain=availability_domain,
                lifecycle_state="ACTIVE"
            ).data
        except Exception:
            return []

    def list_exports(self, compartment_id: str, export_set_id: str) -> list:
        """List file system exports under an export set."""
        try:
            return self.file_storage_client.list_exports(
                compartment_id=compartment_id,
                export_set_id=export_set_id,
            ).data
        except Exception:
            return []
    
    def list_mount_targets(self, compartment_id: str, availability_domain: str) -> list:
        """List mount targets in a compartment/AD."""
        try:
            return self.file_storage_client.list_mount_targets(
                compartment_id=compartment_id,
                availability_domain=availability_domain,
                lifecycle_state="ACTIVE"
            ).data
        except Exception:
            return []
    
    def list_buckets(self, compartment_id: str) -> list:
        """List object storage buckets in a compartment."""
        try:
            namespace = self.object_storage_client.get_namespace().data
            return self.object_storage_client.list_buckets(
                namespace_name=namespace,
                compartment_id=compartment_id
            ).data
        except Exception:
            return []
    
    def get_bucket_details(self, bucket_name: str) -> Optional[dict]:
        """Get bucket details including approximate size."""
        try:
            namespace = self.object_storage_client.get_namespace().data
            bucket = self.object_storage_client.get_bucket(
                namespace_name=namespace,
                bucket_name=bucket_name,
                fields=["approximateCount", "approximateSize"]
            ).data
            return {
                "approximate_count": getattr(bucket, "approximate_count", None),
                "approximate_size": getattr(bucket, "approximate_size", None),
                "storage_tier": getattr(bucket, "storage_tier", None),
            }
        except Exception:
            return None
    
    def list_availability_domains(self, compartment_id: str) -> list:
        """List availability domains for a compartment."""
        try:
            return self.identity_client.list_availability_domains(compartment_id).data
        except Exception:
            return []

    def list_volumes(self, compartment_id: str, availability_domain: Optional[str] = None) -> list:
        """List block volumes in a compartment (optionally by AD)."""
        try:
            return self.block_storage_client.list_volumes(
                compartment_id=compartment_id,
                availability_domain=availability_domain,
            ).data
        except Exception:
            return []

    def list_boot_volumes(self, compartment_id: str, availability_domain: Optional[str] = None) -> list:
        """List boot volumes in a compartment (optionally by AD)."""
        try:
            return self.block_storage_client.list_boot_volumes(
                compartment_id=compartment_id,
                availability_domain=availability_domain,
            ).data
        except Exception:
            return []

    def list_volume_attachments(self, compartment_id: str) -> list:
        """List block volume attachments in a compartment."""
        attachments = []
        try:
            response = self.compute_client.list_volume_attachments(compartment_id=compartment_id)
            attachments.extend(response.data)
            while response.has_next_page:
                response = self.compute_client.list_volume_attachments(
                    compartment_id=compartment_id,
                    page=response.next_page,
                )
                attachments.extend(response.data)
        except Exception:
            return []
        return attachments

    def list_boot_volume_attachments(self, compartment_id: str) -> list:
        """List boot volume attachments in a compartment."""
        attachments = []
        try:
            response = self.compute_client.list_boot_volume_attachments(compartment_id=compartment_id)
            attachments.extend(response.data)
            while response.has_next_page:
                response = self.compute_client.list_boot_volume_attachments(
                    compartment_id=compartment_id,
                    page=response.next_page,
                )
                attachments.extend(response.data)
        except Exception:
            return []
        return attachments

    def list_volume_backups(self, compartment_id: str) -> list:
        """List block volume backups in a compartment."""
        try:
            return self.block_storage_client.list_volume_backups(
                compartment_id=compartment_id,
            ).data
        except Exception:
            return []

    def list_boot_volume_backups(self, compartment_id: str) -> list:
        """List boot volume backups in a compartment."""
        try:
            return self.block_storage_client.list_boot_volume_backups(
                compartment_id=compartment_id,
            ).data
        except Exception:
            return []

    def get_subscriptions(self) -> list:
        """Get Universal Credit subscriptions from OCI onesubscription API.

        Returns list of subscription dicts with committed value and metadata.
        Returns empty list (with graceful fallback) if IAM access is missing.
        """
        try:
            import oci.onesubscription  # noqa: PLC0415
            sub_client = oci.onesubscription.SubscriptionClient(self.config)
            response = sub_client.list_subscriptions(compartment_id=self.tenancy_id)
            result = []
            for s in (response.data or []):
                currency_obj = getattr(s, "currency", None)
                iso_code = (
                    getattr(currency_obj, "iso_code", None)
                    if currency_obj
                    else None
                ) or "USD"
                result.append({
                    "id": str(getattr(s, "id", "") or ""),
                    "status": str(getattr(s, "status", "") or ""),
                    "subscription_type": str(getattr(s, "subscription_type", "") or ""),
                    "time_start": str(getattr(s, "time_start", None)),
                    "time_end": str(getattr(s, "time_end", None)),
                    "total_value": float(getattr(s, "total_value", 0) or 0),
                    "currency": iso_code,
                })
            return result
        except Exception:
            return []


# Singleton instance
_oci_client: Optional[OCIClientService] = None


def get_oci_client(profile_name: Optional[str] = None) -> OCIClientService:
    """Get or create OCI client service instance.
    
    Args:
        profile_name: Optional profile name to use.
        
    Returns:
        OCIClientService instance.
    """
    global _oci_client
    if _oci_client is None or (profile_name and _oci_client.profile_name != profile_name):
        _oci_client = OCIClientService(profile_name)
    return _oci_client


def test_oci_connection(runtime_oci: Optional[dict[str, Any]] = None) -> dict:
    """Test OCI connectivity and return basic tenancy context."""
    client = OCIClientService(runtime_oci=runtime_oci)
    tenancy = client.get_tenancy()
    return {
        "status": "healthy",
        "tenancy_name": getattr(tenancy, "name", None),
        "region": client.region,
        "auth_mode": client.auth_mode,
    }


def reset_oci_client() -> None:
    """Reset cached OCI client so new settings take effect immediately."""
    global _oci_client
    _oci_client = None


def _load_runtime_oci_settings() -> dict[str, Any]:
    """Load OCI settings from persisted settings if available."""
    db = SessionLocal()
    try:
        app_cfg = get_settings()
        if app_cfg.app_env.lower() == "production":
            secure = get_oci_runtime_credentials(db)
            if secure:
                return secure
        setting = db.query(Setting).filter(Setting.id == 1).one_or_none()
        if not setting:
            return {}
        return {
            "auth_mode": getattr(setting, "oci_auth_mode", "profile"),
            "config_profile": getattr(setting, "oci_config_profile", None),
            "config_file": getattr(setting, "oci_config_file", None),
            "user": getattr(setting, "oci_user", None),
            "fingerprint": getattr(setting, "oci_fingerprint", None),
            "tenancy": getattr(setting, "oci_tenancy", None),
            "region": getattr(setting, "oci_region", None),
            "key_file": getattr(setting, "oci_key_file", None),
            "key_content": resolve_secret(getattr(setting, "oci_key_content", None), env_var="OCI_KEY_CONTENT"),
            "pass_phrase": resolve_secret(getattr(setting, "oci_pass_phrase", None), env_var="OCI_PASSPHRASE"),
        }
    except Exception:
        return {}
    finally:
        db.close()


def _load_config_profile(config_file: str, profile_name: str) -> dict:
    """Load OCI profile values without pre-validating key_file paths."""
    parser = configparser.ConfigParser()
    read_ok = parser.read(config_file, encoding="utf-8")
    if not read_ok:
        raise FileNotFoundError(f"OCI config file not found: {config_file}")

    section = profile_name if parser.has_section(profile_name) else "DEFAULT"
    if section != profile_name and not parser.has_section("DEFAULT"):
        raise KeyError(f"OCI profile '{profile_name}' not found in {config_file}")

    values = dict(parser.items(section))
    # Preserve profile for diagnostics in SDK errors.
    values["profile_name"] = section
    return values


def _normalize_key_file_path(config: dict[str, Any]) -> None:
    """Map host key_file paths to mounted container paths when needed."""
    cfg = get_settings()
    if cfg.app_env.lower() == "production" and not cfg.allow_oci_file_path_mode:
        if config.get("key_file"):
            raise_production_block("oci_key_file", None)
        return
    key_file = config.get("key_file")
    if not key_file:
        return
    key_path = Path(key_file).expanduser()
    if key_path.exists():
        return
    mapped_paths = [
        Path("/home/app/.oci") / win_basename(key_file),
        Path("/root/.oci") / win_basename(key_file),
    ]
    for mapped in mapped_paths:
        if mapped.exists():
            config["key_file"] = str(mapped)
            return


def _build_direct_config(runtime_oci: dict[str, Any]) -> dict[str, Any]:
    """Build OCI config from direct credentials saved in app settings."""
    cfg = {
        "user": (runtime_oci.get("user") or "").strip(),
        "fingerprint": (runtime_oci.get("fingerprint") or "").strip(),
        "tenancy": (runtime_oci.get("tenancy") or "").strip(),
        "region": (runtime_oci.get("region") or "").strip(),
    }
    key_file = (runtime_oci.get("key_file") or "").strip()
    key_content = (runtime_oci.get("key_content") or "").strip()
    pass_phrase = runtime_oci.get("pass_phrase")
    if key_content:
        cfg["key_content"] = key_content.replace("\\n", "\n")
    if key_file:
        app_cfg = get_settings()
        if app_cfg.app_env.lower() == "production" and not app_cfg.allow_oci_file_path_mode:
            raise_production_block("oci_key_file", None)
        cfg["key_file"] = key_file
    if pass_phrase:
        cfg["pass_phrase"] = pass_phrase
    return cfg


def _validate_runtime_path_mode(runtime_oci: dict[str, Any]) -> None:
    app_cfg = get_settings()
    if app_cfg.app_env.lower() != "production" or app_cfg.allow_oci_file_path_mode:
        return
    config_file = str((runtime_oci or {}).get("config_file") or "")
    key_file = str((runtime_oci or {}).get("key_file") or "")
    blocked_prefixes = ("/root/.oci", "~/.oci", "/home/app/.oci")
    if config_file and (config_file.startswith("/") or config_file.startswith("~")):
        raise_production_block("oci_config_file", None)
    if key_file and (key_file.startswith("/") or key_file.startswith("~")):
        raise_production_block("oci_key_file", None)
    if any(config_file.startswith(p) for p in blocked_prefixes):
        raise_production_block("oci_config_file", None)
    if any(key_file.startswith(p) for p in blocked_prefixes):
        raise_production_block("oci_key_file", None)
