#!/usr/bin/env python3
"""
OCI Cyber Compartment Report

Features:
- Enumerate instances under prod-tamam-cyber child compartments
- Export:
    - Instance details (shape, AD, FD, tags)
    - VCN, Subnet, Security Lists, Private IPs
    - Boot volume + attached data volumes (with totals)
    - Cost: last 30 days, last 365 days, since creation
    - Storage cost (boot + data volumes) with same windows
    - Avg CPU & Memory Utilization (last 7 days)
    - Storage growth forecast for boot volume (GB/30 days)
    - OS and license model (e.g., Windows license included/BYOL)
- Outputs: CSV, XLSX, JSON
- Optional: Email attachments
- Includes OCI Functions handler() for scheduled execution
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import oci
from oci.monitoring.models import SummarizeMetricsDataDetails
import xlsxwriter

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

# Parent compartment defaults
PARENT_COMPARTMENT_OCID = (
    "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq"
)

# Alternative parent choices for interactive selection (prod + staging)
PARENT_COMPARTMENT_CHOICES: Tuple[Tuple[str, str], ...] = (
    ("Production (prod root)", "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq"),
    ("Staging (staging root)", "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa"),
)

# Fallback child compartments for prompts when Identity API listing is unavailable
STAGING_CHILDREN_FALLBACK: Tuple[Tuple[str, str], ...] = (
    ("stagging-testing", "ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova"),
    ("staging-ad1", "ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q"),
    ("staging-benchmatrix", "ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq"),
    ("staging-cyber", "ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa"),
    ("staging-dmz", "ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka"),
    ("staging-erp", "ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua"),
    ("staging-foo", "ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq"),
    ("staging-hub", "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq"),
    ("staging-intellect", "ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q"),
    ("staging-interactive", "ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq"),
    ("staging-kepler", "ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq"),
    ("staging-monitor", "ocid1.compartment.oc1..aaaaaaaabb2yiiri5axph44kee26svtjwmng6kz5f2duokqxobxkg46scfwa"),
    ("staging-optasia", "ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq"),
    ("staging-tamam", "ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq"),
)

PRODUCTION_CHILDREN_FALLBACK: Tuple[Tuple[str, str], ...] = (
    ("prd-erp", "ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a"),
    ("prod-ad1", "ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja"),
    ("prod-audit", "ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa"),
    ("prod-benchmatrix", "ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq"),
    ("prod-born-interactive", "ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda"),
    ("prod-dmz", "ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q"),
    ("prod-foo", "ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq"),
    ("prod-hub", "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka"),
    ("prod-intellect", "ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq"),
    ("prod-kepler", "ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq"),
    ("prod-optasia", "ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq"),
    ("prod-tamam", "ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza"),
    ("prod-tamam-cyber", "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq"),
)

# Child compartments to scan (used when no interactive selection is performed)
TARGET_CHILD_COMPARTMENTS = [
    "ocid1.compartment.oc1..aaaaaaaaugwikr4obsajq2afls57ilbdja7k54h2353id7ens5acodftntha",  # prod-cyber-networking
    "ocid1.compartment.oc1..aaaaaaaaingfoprklhejxgmi4iioqnon2k5zq32theto545zmfoujzrcodoa",  # prod-cyber-compute
]

# Output directory (override with OCI_REPORT_DIR). Default:
# - /tmp when running as an OCI Function (needs writable /tmp)
# - ~/oci_cyber_reports for local/VM runs to avoid /tmp permission clashes
DEFAULT_REPORT_DIR = (
    Path(os.getenv("OCI_REPORT_DIR"))
    if os.getenv("OCI_REPORT_DIR")
    else (Path("/tmp") if os.getenv("OCI_RESOURCE_PRINCIPAL_VERSION") else Path.home() / "oci_cyber_reports")
)

REPORT_DIR = DEFAULT_REPORT_DIR
REPORT_CSV = str(REPORT_DIR / "oci_cyber_instances.csv")
REPORT_XLSX = str(REPORT_DIR / "oci_cyber_instances.xlsx")
REPORT_JSON = str(REPORT_DIR / "oci_cyber_instances.json")

# Email/SMS settings (toggle with env flags)
ENABLE_EMAIL = os.getenv("ENABLE_EMAIL", "true").lower() == "true"
ENABLE_SMS = os.getenv("ENABLE_SMS", "true").lower() == "true"

# External mailer and SMS scripts
MAIL_SCRIPT_PATH = Path(
    os.getenv("MAIL_SCRIPT_PATH", "/mnt/app-data/scripts/services/mail/mail.py")
)
SMS_SCRIPT_PATH = Path(
    os.getenv("SMS_SCRIPT_PATH", "/mnt/app-data/scripts/services/sms/sms.sh")
)

# Notification defaults
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "hosamaldin.awd@tamam.life")
EMAIL_CATEGORY = os.getenv("EMAIL_CATEGORY", "OCI Cyber Report")
EMAIL_MONITOR = os.getenv("EMAIL_MONITOR", "oci-cyber-report")
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "Daily OCI Cyber Compartment Report")
SMS_DESTINATION = os.getenv("SMS_DESTINATION", "0540372159")

# Proxy handling: set to True (or env BYPASS_OCI_PROXY=true) to strip proxy vars and
# append common OCI hosts to NO_PROXY/no_proxy before making SDK calls. This
# addresses MaxRetryError/ProxyError cases when the proxy blocks OCI endpoints.
# Default is True to avoid proxy MITM/SSL issues unless explicitly disabled.
BYPASS_OCI_PROXY = os.getenv("BYPASS_OCI_PROXY", "true").lower() == "true"
NO_PROXY_SUFFIXES = os.getenv(
    "OCI_NO_PROXY_SUFFIXES", "oraclecloud.com,.oraclecloud.com"
).split(",")

# Prompt behaviour
ENABLE_INTERACTIVE_PROMPTS = (
    os.getenv("ENABLE_INTERACTIVE_PROMPTS", "true").lower() == "true"
)
FORCE_INTERACTIVE_PROMPTS = os.getenv("FORCE_INTERACTIVE", "false").lower() == "true"

# Currency and licensing
USD_TO_SAR_RATE = float(os.getenv("USD_TO_SAR_RATE", "3.75"))
WINDOWS_LICENSE_PER_OCPU_HOUR = float(os.getenv("WINDOWS_LICENSE_PER_OCPU_HOUR", "0.092"))

# XLSX sheet names
SHEET_INVENTORY = "OCI_Instance_Inventory"
SHEET_WINDOWS_LICENSE = "Windows_License_Calculation"
SHEET_COST_SUMMARY = "Cost_Summary_(USD_SAR)"
SHEET_FULL_YEAR = "Full-Year Estimated Costs (USD)"


# -------------------------------------------------------------------
# OCI CLIENTS
# -------------------------------------------------------------------

def get_oci_clients() -> tuple[
    Dict[str, Any],
    oci.core.ComputeClient,
    oci.core.BlockstorageClient,
    oci.core.VirtualNetworkClient,
    oci.usage_api.UsageapiClient,
    oci.monitoring.MonitoringClient,
    oci.identity.IdentityClient,
]:
    """
    Supports:
    - Local/VM/CloudShell via ~/.oci/config
    - OCI Functions via Resource Principal
    """
    if os.getenv("OCI_RESOURCE_PRINCIPAL_VERSION"):
        signer = oci.auth.signers.get_resource_principals_signer()
        config = {"region": os.getenv("OCI_REGION")}
        client_kwargs = {"config": config, "signer": signer}
    else:
        config = oci.config.from_file()
        client_kwargs = {"config": config}

    _bypass_proxy_for_oci(config.get("region"))

    compute = oci.core.ComputeClient(**client_kwargs)
    blockstorage = oci.core.BlockstorageClient(**client_kwargs)
    vcn_client = oci.core.VirtualNetworkClient(**client_kwargs)
    usage_client = oci.usage_api.UsageapiClient(**client_kwargs)
    monitoring_client = oci.monitoring.MonitoringClient(**client_kwargs)
    identity_client = oci.identity.IdentityClient(**client_kwargs)

    return (
        config,
        compute,
        blockstorage,
        vcn_client,
        usage_client,
        monitoring_client,
        identity_client,
    )


def get_identity_client_for_prompt() -> Optional[oci.identity.IdentityClient]:
    """Lightweight identity client for interactive compartment selection."""

    try:
        if os.getenv("OCI_RESOURCE_PRINCIPAL_VERSION"):
            signer = oci.auth.signers.get_resource_principals_signer()
            config = {"region": os.getenv("OCI_REGION")}
            client_kwargs = {"config": config, "signer": signer}
        else:
            config = oci.config.from_file()
            client_kwargs = {"config": config}

        _bypass_proxy_for_oci(config.get("region"))
        return oci.identity.IdentityClient(**client_kwargs)
    except Exception as exc:  # noqa: BLE001 - prompt helper only
        print(f"[WARN] Unable to initialize identity client for prompts: {exc}")
        return None


def _bypass_proxy_for_oci(region: Optional[str]) -> None:
    """Optionally remove proxy env vars and extend NO_PROXY for OCI endpoints."""

    if not BYPASS_OCI_PROXY:
        return

    for var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        if var in os.environ:
            os.environ.pop(var, None)

    suffixes = set(NO_PROXY_SUFFIXES)
    if region:
        suffixes.update(
            {
                f"usageapi.{region}.oci.oraclecloud.com",
                f"telemetry.{region}.oraclecloud.com",
                f"iaas.{region}.oraclecloud.com",
                f"identity.{region}.oraclecloud.com",
            }
        )

    current = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    entries = {entry.strip() for entry in current.split(",") if entry.strip()}
    entries.update(suffixes)
    merged = ",".join(sorted(entries)) if entries else ""
    os.environ["NO_PROXY"] = merged
    os.environ["no_proxy"] = merged
    print(
        "[INFO] Proxy variables cleared for OCI calls; NO_PROXY set to:",  # noqa: T201
        merged,
    )


IMAGE_CACHE: Dict[str, tuple[str, Optional[str]]] = {}


def get_image_details(
    compute: oci.core.ComputeClient, image_id: Optional[str]
) -> tuple[str, Optional[str]]:
    """Return (operating_system, license_model) for an image, cached by image_id."""

    if not image_id:
        return "", None

    if image_id in IMAGE_CACHE:
        return IMAGE_CACHE[image_id]

    try:
        image = compute.get_image(image_id).data
        IMAGE_CACHE[image_id] = (
            getattr(image, "operating_system", "") or "",
            getattr(image, "license_model", None),
        )
    except Exception as exc:  # noqa: BLE001 - logging only
        print(f"[WARN] Unable to fetch image details for {image_id}: {exc}")
        IMAGE_CACHE[image_id] = ("", None)

    return IMAGE_CACHE[image_id]


def list_child_compartments(
    identity_client: oci.identity.IdentityClient, parent_compartment_ocid: str
) -> List[Dict[str, str]]:
    """Return active immediate child compartments for a parent compartment."""

    response = identity_client.list_compartments(
        compartment_id=parent_compartment_ocid,
        compartment_id_in_subtree=False,
        lifecycle_state="ACTIVE",
        access_level="ANY",
        sort_by="NAME",
    )

    children: List[Dict[str, str]] = []
    for comp in response.data:
        children.append({"name": comp.name, "ocid": comp.id})

    return children


def _prompt_choice(prompt: str, options: Sequence[str], default_index: int = 0) -> int:
    """Prompt the user to select an index from a list of options."""

    for idx, label in enumerate(options):
        print(f"[{idx}] {label}")

    raw = input(f"{prompt} [{default_index}]: ").strip()
    if raw == "":
        return default_index

    try:
        val = int(raw)
    except ValueError:
        print("[WARN] Invalid entry; using default.")
        return default_index

    if 0 <= val < len(options):
        return val

    print("[WARN] Out of range; using default.")
    return default_index


def _fallback_children_for_parent(parent_ocid: str) -> List[Dict[str, str]]:
    if parent_ocid == PARENT_COMPARTMENT_CHOICES[1][1]:
        return [
            {"name": name, "ocid": ocid} for name, ocid in STAGING_CHILDREN_FALLBACK
        ]
    if parent_ocid == PARENT_COMPARTMENT_CHOICES[0][1]:
        return [
            {"name": name, "ocid": ocid} for name, ocid in PRODUCTION_CHILDREN_FALLBACK
        ]
    return []


def _child_compartments_with_compute(
    identity_client: Optional[oci.identity.IdentityClient],
    children: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Expand to compute subcompartments when available; fallback to provided children."""

    if identity_client is None:
        return children

    expanded: List[Dict[str, str]] = []
    for comp in children:
        try:
            grandkids = list_child_compartments(identity_client, comp["ocid"])
        except Exception as exc:  # noqa: BLE001 - prompts should not fail generation
            print(f"[WARN] Unable to list subcompartments for {comp['name']}: {exc}")
            expanded.append(comp)
            continue

        compute_only = [
            c
            for c in grandkids
            if "compute" in c.get("name", "").lower()
            or c.get("name", "").lower().endswith("-cmp")
        ]

        if compute_only:
            expanded.extend(compute_only)
        else:
            expanded.append(comp)

    return expanded


def resolve_runtime_inputs(
    identity_client: Optional[oci.identity.IdentityClient],
    interactive: bool,
) -> tuple[str, List[str], Dict[str, str], str, str]:
    """Resolve parent/child compartments and notification targets.

    Returns (parent_label, child_ocids, child_parent_map, email_recipients, sms_destination).
    """

    parent_label = "Default"
    parent_ocid = PARENT_COMPARTMENT_OCID
    child_ocids = list(TARGET_CHILD_COMPARTMENTS)
    child_parent_map: Dict[str, str] = {cid: parent_ocid for cid in child_ocids}
    email_recipients = EMAIL_RECIPIENTS
    sms_destination = SMS_DESTINATION

    if not interactive:
        return parent_label, child_ocids, child_parent_map, email_recipients, sms_destination

    env_options = ["Production", "Staging", "All"]
    print("[PROMPT] Select environment to scan:")
    env_choice = _prompt_choice("Enter option", env_options, default_index=0)

    parent_targets: List[Tuple[str, str]] = []
    if env_choice == 2:  # All
        parent_targets = list(PARENT_COMPARTMENT_CHOICES)
        parent_label = "All"
    else:
        parent_targets = [PARENT_COMPARTMENT_CHOICES[env_choice]]
        parent_label = env_options[env_choice]
        parent_ocid = parent_targets[0][1]

    child_ocids = []
    child_parent_map = {}

    for label, parent in parent_targets:
        children: List[Dict[str, str]] = []
        if identity_client is not None:
            try:
                children = list_child_compartments(identity_client, parent)
            except Exception as exc:  # noqa: BLE001 - prompts should not fail generation
                print(f"[WARN] Unable to list child compartments for {label}: {exc}")

        if not children:
            children = _fallback_children_for_parent(parent)

        children = _child_compartments_with_compute(identity_client, children)

        if env_choice != 2:
            print(
                "[PROMPT] Select child compartments (comma-separated indexes, blank=all):"
            )
            for idx, comp in enumerate(children):
                print(f"[{idx}] {comp['name']} ({comp['ocid']})")

            raw_children = input("Child indexes: ").strip()
            if raw_children:
                selected: List[str] = []
                for token in raw_children.split(","):
                    token = token.strip()
                    if not token:
                        continue
                    try:
                        i = int(token)
                    except ValueError:
                        print(f"[WARN] Skipping invalid index '{token}'.")
                        continue
                    if 0 <= i < len(children):
                        selected.append(children[i]["ocid"])
                    else:
                        print(f"[WARN] Index {i} out of range; skipping.")
                if selected:
                    children = [c for c in children if c["ocid"] in selected]
            # blank input keeps all

        if not children:
            print(
                f"[PROMPT] No children available for {label}. "
                "Press Enter to skip or paste comma-separated child OCIDs:"
            )
            manual_children = input("Child OCIDs: ").strip()
            if manual_children:
                manual_list = [
                    token.strip() for token in manual_children.split(",") if token.strip()
                ]
                children = [
                    {"name": f"manual-{idx}", "ocid": ocid}
                    for idx, ocid in enumerate(manual_list)
                ]

        for comp in children:
            child_ocids.append(comp["ocid"])
            child_parent_map[comp["ocid"]] = parent

    new_email = input(f"Email recipients [{email_recipients}]: ").strip()
    if new_email:
        email_recipients = new_email

    new_sms = input(f"SMS destination [{sms_destination}]: ").strip()
    if new_sms:
        sms_destination = new_sms

    if not child_ocids:
        child_ocids = list(TARGET_CHILD_COMPARTMENTS)
        child_parent_map = {cid: parent_ocid for cid in child_ocids}

    return parent_label, child_ocids, child_parent_map, email_recipients, sms_destination


def usd_to_sar(amount: Optional[float]) -> Optional[float]:
    """Convert USD to SAR using the configured rate."""

    if amount is None:
        return None

    return round(amount * USD_TO_SAR_RATE, 4)


def compute_windows_license_cost(
    operating_system: str, ocpus: Optional[float], created_at: datetime, now: datetime
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Return (hourly_cost_usd, monthly_cost_usd, since_creation_cost_usd) for Windows OS.

    If the OS is not Windows or OCPUs are missing, returns (None, None, None).
    """

    if not operating_system or "windows" not in operating_system.lower():
        return None, None, None

    if ocpus is None:
        return None, None, None

    hourly_cost = round(ocpus * WINDOWS_LICENSE_PER_OCPU_HOUR, 3)
    monthly_cost = round(hourly_cost * 24 * 30, 2)
    hours_since_creation = max((now - created_at).total_seconds() / 3600, 0)
    since_creation_cost = round(hourly_cost * hours_since_creation, 2)

    return hourly_cost, monthly_cost, since_creation_cost


# -------------------------------------------------------------------
# NETWORKING HELPERS
# -------------------------------------------------------------------

def get_instance_networking(
    compute: oci.core.ComputeClient,
    vcn_client: oci.core.VirtualNetworkClient,
    inst: oci.core.models.Instance,
    compartment_id: str,
) -> tuple[str, str, str, str, str, str, str]:
    """
    Returns:
      private_ips (comma string),
      vcn_name, vcn_ocid,
      subnet_name, subnet_ocid,
      sec_list_names (comma),
      sec_list_ocids (comma)
    """
    private_ips: List[str] = []
    vcn_name = vcn_ocid = ""
    subnet_name = subnet_ocid = ""
    sec_list_names: List[str] = []
    sec_list_ocids: List[str] = []

    vnic_attachments = oci.pagination.list_call_get_all_results(
        compute.list_vnic_attachments,
        compartment_id=compartment_id,
        instance_id=inst.id,
    ).data

    if not vnic_attachments:
        return "", "", "", "", "", "", ""

    for va in vnic_attachments:
        vnic = vcn_client.get_vnic(va.vnic_id).data
        if vnic.private_ip:
            private_ips.append(vnic.private_ip)

        subnet = vcn_client.get_subnet(vnic.subnet_id).data
        vcn = vcn_client.get_vcn(subnet.vcn_id).data

        vcn_name = vcn.display_name
        vcn_ocid = vcn.id
        subnet_name = subnet.display_name
        subnet_ocid = subnet.id

        for sl_id in subnet.security_list_ids:
            sl = vcn_client.get_security_list(sl_id).data
            sec_list_names.append(sl.display_name)
            sec_list_ocids.append(sl.id)

    return (
        ", ".join(private_ips),
        vcn_name,
        vcn_ocid,
        subnet_name,
        subnet_ocid,
        ", ".join(sec_list_names),
        ", ".join(sec_list_ocids),
    )


# -------------------------------------------------------------------
# VOLUME HELPERS
# -------------------------------------------------------------------

def get_boot_volume(
    compute: oci.core.ComputeClient,
    blockstorage: oci.core.BlockstorageClient,
    inst: oci.core.models.Instance,
    compartment_id: str,
) -> tuple[Optional[int], str, Optional[datetime]]:
    """
    Returns boot volume size (GB) and OCID for the instance.
    Uses list_boot_volume_attachments which REQUIRES availability_domain.
    """
    ad = inst.availability_domain
    attachments = oci.pagination.list_call_get_all_results(
        compute.list_boot_volume_attachments,
        availability_domain=ad,
        compartment_id=compartment_id,
        instance_id=inst.id,
    ).data

    if not attachments:
        return None, "", None

    bva = attachments[0]
    bv = blockstorage.get_boot_volume(bva.boot_volume_id).data

    return bv.size_in_gbs, bv.id, bv.time_created


@dataclass
class VolumeSummary:
    volume_id: str
    size_gb: int
    created: Optional[datetime]
    label: str


def get_data_volumes(
    compute: oci.core.ComputeClient,
    blockstorage: oci.core.BlockstorageClient,
    inst: oci.core.models.Instance,
    compartment_id: str,
) -> tuple[str, int, List[VolumeSummary]]:
    """
    Returns attached block volumes as a display string, total size, and structured list.

    Display format: 'Name(SizeGB):OCID; Name(SizeGB):OCID; ...'
    """
    volumes_info: List[str] = []
    total_size_gb = 0
    volume_summaries: List[VolumeSummary] = []

    v_atts = oci.pagination.list_call_get_all_results(
        compute.list_volume_attachments,
        compartment_id=compartment_id,
        instance_id=inst.id,
    ).data

    for va in v_atts:
        vol = blockstorage.get_volume(va.volume_id).data
        info = f"{vol.display_name}({vol.size_in_gbs}GB):{vol.id}"
        volumes_info.append(info)
        total_size_gb += vol.size_in_gbs
        volume_summaries.append(
            VolumeSummary(
                volume_id=vol.id,
                size_gb=vol.size_in_gbs,
                created=vol.time_created,
                label=vol.display_name,
            )
        )

    return "; ".join(volumes_info), total_size_gb, volume_summaries


# -------------------------------------------------------------------
# COST HELPERS
# -------------------------------------------------------------------

def _truncate_to_midnight(dt_value: datetime) -> datetime:
    """Return a copy of ``dt_value`` truncated to 00:00:00 UTC."""

    return dt_value.replace(hour=0, minute=0, second=0, microsecond=0)


def _cap_usage_window(start_time: datetime, end_time: datetime, max_days: int = 366) -> tuple[datetime, datetime]:
    """Ensure the Usage API window does not exceed ``max_days``.

    The Usage API rejects monthly granularity queries longer than 366 days with
    an ``InvalidParameter`` error. When the requested window exceeds this
    threshold (for example, ``since_creation`` on very old instances), we clamp
    the start date to ``max_days`` before the end date.
    """

    truncated_start = _truncate_to_midnight(start_time)
    truncated_end = _truncate_to_midnight(end_time)

    max_range_start = truncated_end - timedelta(days=max_days)
    if truncated_start < max_range_start:
        print(
            "[WARN] Cost window exceeds Usage API limit; clamping to",  # noqa: T201 - intentional logging
            max_range_start.isoformat(),
        )
        truncated_start = max_range_start

    return truncated_start, truncated_end


def get_resource_cost(
    usage_client: oci.usage_api.UsageapiClient,
    config: Dict[str, Any],
    resource_ocid: str,
    start_time: datetime,
    end_time: datetime,
    max_attempts: int = 3,
    backoff_seconds: int = 2,
) -> Optional[float]:
    """
    Uses Usage API to sum COST-like fields for this resource between ``start_time`` and ``end_time``.

    The Usage API requires timestamps truncated to midnight UTC; requests with non-zero minute/second
    precision return ``InvalidParameter`` errors, so we coerce the window accordingly. We also retry on
    throttling to cope with occasional ``TooManyRequests`` responses.
    """

    truncated_start, truncated_end = _cap_usage_window(start_time, end_time)

    details = oci.usage_api.models.RequestSummarizedUsagesDetails(
        tenant_id=config["tenancy"],
        time_usage_started=truncated_start,
        time_usage_ended=truncated_end,
        granularity=oci.usage_api.models.RequestSummarizedUsagesDetails.GRANULARITY_MONTHLY,
        query_type=oci.usage_api.models.RequestSummarizedUsagesDetails.QUERY_TYPE_COST,
        group_by=["resourceId"],
    )

    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            resp = usage_client.request_summarized_usages(details)
            total = 0.0
            for item in resp.data.items:
                if item.resource_id != resource_ocid:
                    continue

                val: Optional[float] = None
                for attr in (
                    "computed_amount",
                    "computed_amount_in_billing_currency",
                    "cost",
                    "sum",
                ):
                    if hasattr(item, attr) and getattr(item, attr) is not None:
                        val = float(getattr(item, attr))
                        break

                if val is not None:
                    total += val

            return round(total, 2)
        except oci.exceptions.ServiceError as exc:
            if exc.status == 429 and attempt < max_attempts:
                wait_seconds = backoff_seconds * attempt
                print(
                    f"[WARN] Cost lookup throttled for {resource_ocid} (attempt {attempt}/{max_attempts}); "
                    f"sleeping {wait_seconds}s."
                )
                time.sleep(wait_seconds)
                continue
            print(f"[WARN] Cost lookup failed for {resource_ocid}: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001 - intentional broad catch for API robustness
            if attempt < max_attempts:
                wait_seconds = backoff_seconds * attempt
                print(
                    f"[WARN] Cost lookup error for {resource_ocid} (attempt {attempt}/{max_attempts}); "
                    f"sleeping {wait_seconds}s. Error: {exc}"
                )
                time.sleep(wait_seconds)
                continue

            print(f"[WARN] Cost lookup failed for {resource_ocid}: {exc}")
            return None

    return None


# -------------------------------------------------------------------
# METRICS HELPERS (CPU / MEM / STORAGE)
# -------------------------------------------------------------------

def get_avg_metric(
    monitoring_client: oci.monitoring.MonitoringClient,
    metric_name: str,
    resource_id: str,
    compartment_id: str,
    days: int = 7,
) -> Optional[float]:
    """
    Returns average metric value over last `days`.
    namespace: oci_computeagent
    query example:
      CpuUtilization[1h]{resourceId = "<ocid>"}.mean()
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    query = f'{metric_name}[1h]{{resourceId = "{resource_id}"}}.mean()'

    details = SummarizeMetricsDataDetails(
        namespace="oci_computeagent",
        query=query,
        start_time=start_time,
        end_time=end_time,
        resolution="1h",
    )

    try:
        resp = monitoring_client.summarize_metrics_data(
            compartment_id=compartment_id,
            summarize_metrics_data_details=details,
        )
    except Exception as exc:  # noqa: BLE001 - intentional broad catch for API robustness
        print(f"[WARN] Metric {metric_name} failed for {resource_id}: {exc}")
        return None

    values: List[float] = []
    for series in resp.data:
        for dp in series.aggregated_datapoints:
            if dp.value is not None:
                values.append(dp.value)

    if not values:
        return None

    return round(sum(values) / len(values), 2)


def aggregate_costs_for_resources(
    usage_client: oci.usage_api.UsageapiClient,
    config: Dict[str, Any],
    resources: List[VolumeSummary],
    now: datetime,
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Sum cost across a list of resources (volumes) for common time windows.

    Returns: (monthly_cost, yearly_cost, since_creation_cost)
    """

    monthly_total = 0.0
    yearly_total = 0.0
    since_total = 0.0
    any_monthly = False
    any_yearly = False
    any_since = False

    for resource in resources:
        created_dt = (resource.created or now).replace(tzinfo=None)

        monthly_cost = get_resource_cost(
            usage_client, config, resource.volume_id, now - timedelta(days=30), now
        )
        yearly_cost = get_resource_cost(
            usage_client, config, resource.volume_id, now - timedelta(days=365), now
        )
        since_creation_cost = get_resource_cost(
            usage_client, config, resource.volume_id, created_dt, now
        )

        if monthly_cost is not None:
            monthly_total += monthly_cost
            any_monthly = True
        if yearly_cost is not None:
            yearly_total += yearly_cost
            any_yearly = True
        if since_creation_cost is not None:
            since_total += since_creation_cost
            any_since = True

    return (
        round(monthly_total, 2) if any_monthly else None,
        round(yearly_total, 2) if any_yearly else None,
        round(since_total, 2) if any_since else None,
    )


def get_storage_forecast(
    monitoring_client: oci.monitoring.MonitoringClient,
    volume_id: str,
    compartment_id: str,
) -> Optional[float]:
    """
    Simple forecast using VolumeUsedBytes over the last 14 days.
    Returns predicted growth (GB) over next 30 days (linear).
    namespace: oci_blockstore
    metric: VolumeUsedBytes
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=14)

    query = f'VolumeUsedBytes[1h]{{resourceId = "{volume_id}"}}.mean()'

    details = SummarizeMetricsDataDetails(
        namespace="oci_blockstore",
        query=query,
        start_time=start_time,
        end_time=end_time,
        resolution="1h",
    )

    try:
        resp = monitoring_client.summarize_metrics_data(
            compartment_id=compartment_id,
            summarize_metrics_data_details=details,
        )
    except Exception as exc:  # noqa: BLE001 - intentional broad catch for API robustness
        print(f"[WARN] Storage forecast metric failed for {volume_id}: {exc}")
        return None

    values: List[float] = []
    for series in resp.data:
        for dp in series.aggregated_datapoints:
            if dp.value is not None:
                values.append(dp.value)

    if len(values) < 2:
        return None

    daily_growth_bytes = (values[-1] - values[0]) / 14.0
    monthly_growth_gb = (daily_growth_bytes * 30.0) / (1024**3)
    return round(monthly_growth_gb, 2)


# -------------------------------------------------------------------
# EXPORT HELPERS (CSV / XLSX / EMAIL)
# -------------------------------------------------------------------

INVENTORY_HEADERS = [
    "Region",
    "Instance Name",
    "State",
    "OCPUs",
    "Memory (GB)",
    "Created UTC",
    "Private IPs",
    "Subnet Name",
    "Boot Volume Size (GB)",
    "Data Volumes",
    "Total Storage (GB)",
    "Storage Monthly Cost (USD)",
    "Storage Yearly Cost (USD)",
    "Storage Cost Since Creation (USD)",
    "Monthly Cost (USD)",
    "Yearly Cost (USD)",
    "Cost Since Creation (USD)",
    "Cost Since Creation (SAR)",
    "Operating System",
    "License Model",
    "Avg CPU Utilization % (7d)",
    "Avg Memory Utilization % (7d)",
    "Forecast Storage Growth (GB/30d)",
    "Defined Tags",
]

WINDOWS_LICENSE_HEADERS = [
    "Instance",
    "OS",
    "OCPUs",
    "License cost per hour (USD)",
    "Approx per 30-day month (USD)",
    "Since creation (USD)",
    "Since creation (SAR)",
]

COST_SUMMARY_HEADERS = [
    "Instance Name",
    "Cost Since Creation resources (USD)",
    "Cost Since Creation resources (SAR)",
    "Since creation Windows OS (USD)",
    "Since creation Windows OS (SAR)",
    "Final COST USD",
    "Final COST SAR",
]

FULL_YEAR_HEADERS = [
    "Instance Name",
    "Cost Since Creation (USD)",
    "Full Year (USD)",
    "Cost Since Creation (SAR)",
    "Full Year (SAR)",
]

def write_csv(rows: List[Dict[str, Any]], filename: str) -> None:
    if not rows:
        print("[INFO] No rows to write CSV.")
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", newline="", encoding="utf-8") as csv_file:
        headers = list(rows[0].keys())
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[INFO] CSV written to {filename}")


def _write_sheet(
    workbook: xlsxwriter.Workbook,
    sheet_name: str,
    headers: List[str],
    rows: List[Dict[str, Any]],
) -> None:
    worksheet = workbook.add_worksheet(sheet_name)
    header_format = workbook.add_format({"bold": True})

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)

    for row_idx, row in enumerate(rows, start=1):
        for col_idx, header in enumerate(headers):
            worksheet.write(row_idx, col_idx, row.get(header, ""))

    worksheet.autofilter(0, 0, len(rows), len(headers) - 1)
    worksheet.freeze_panes(1, 0)


def write_xlsx_workbook(
    inventory_rows: List[Dict[str, Any]],
    windows_license_rows: List[Dict[str, Any]],
    cost_summary_rows: List[Dict[str, Any]],
    full_year_rows: List[Dict[str, Any]],
    filename: str,
) -> None:
    if not inventory_rows:
        print("[INFO] No rows to write XLSX.")
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    workbook = xlsxwriter.Workbook(filename)

    _write_sheet(workbook, SHEET_INVENTORY, INVENTORY_HEADERS, inventory_rows)

    if windows_license_rows:
        _write_sheet(
            workbook, SHEET_WINDOWS_LICENSE, WINDOWS_LICENSE_HEADERS, windows_license_rows
        )

    if cost_summary_rows:
        _write_sheet(workbook, SHEET_COST_SUMMARY, COST_SUMMARY_HEADERS, cost_summary_rows)

    if full_year_rows:
        _write_sheet(workbook, SHEET_FULL_YEAR, FULL_YEAR_HEADERS, full_year_rows)

    workbook.close()
    print(f"[INFO] XLSX written to {filename}")


def send_report_email(
    csv_path: str,
    xlsx_path: str,
    json_path: str,
    body: str,
    recipients: Optional[str] = None,
) -> None:
    if not ENABLE_EMAIL:
        print("[INFO] Email sending disabled (ENABLE_EMAIL=false).")
        return

    if not MAIL_SCRIPT_PATH.exists():
        print(f"[WARN] Mail script not found at {MAIL_SCRIPT_PATH}; skipping email.")
        return

    attachments = [path for path in [csv_path, xlsx_path, json_path] if os.path.exists(path)]
    if not attachments:
        print("[WARN] No report files available to attach; skipping email.")
        return

    cmd = [
        sys.executable,
        str(MAIL_SCRIPT_PATH),
        "-s",
        EMAIL_SUBJECT,
        "-r",
        recipients or EMAIL_RECIPIENTS,
        "-g",
        EMAIL_CATEGORY,
        "-n",
        EMAIL_MONITOR,
        "-m",
        body,
        "-a",
        ",".join(attachments),
    ]

    try:
        subprocess.run(cmd, check=True)
        print("[INFO] Email sent successfully via external mail script.")
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] Email send failed: {exc}")


def send_report_sms(message: str, destination: Optional[str] = None) -> None:
    if not ENABLE_SMS:
        print("[INFO] SMS sending disabled (ENABLE_SMS=false).")
        return

    if not SMS_SCRIPT_PATH.exists():
        print(f"[WARN] SMS script not found at {SMS_SCRIPT_PATH}; skipping SMS.")
        return

    dest = destination or SMS_DESTINATION

    if not dest:
        print("[WARN] No SMS destination configured; skipping SMS.")
        return

    cmd = [str(SMS_SCRIPT_PATH), "-m", message, "-d", dest]

    try:
        subprocess.run(cmd, check=True)
        print(f"[INFO] SMS sent to {dest} via external script.")
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] SMS send failed: {exc}")


# -------------------------------------------------------------------
# MAIN REPORT LOGIC
# -------------------------------------------------------------------

def generate_report(
    parent_compartment_ocid: Optional[str] = None,
    target_child_compartments: Optional[Sequence[str]] = None,
    email_recipients: Optional[str] = None,
    sms_destination: Optional[str] = None,
    child_parent_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    (
        config,
        compute,
        blockstorage,
        vcn_client,
        usage_client,
        monitoring_client,
        _identity_client,
    ) = get_oci_clients()
    region = config.get("region", "unknown")

    parent_compartment_ocid = parent_compartment_ocid or PARENT_COMPARTMENT_OCID
    selected_children = (
        list(target_child_compartments)
        if target_child_compartments is not None
        else list(TARGET_CHILD_COMPARTMENTS)
    )
    child_parent_map = child_parent_map or {
        cid: parent_compartment_ocid for cid in selected_children
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Saving reports to {REPORT_DIR}")

    rows: List[Dict[str, Any]] = []
    inventory_rows: List[Dict[str, Any]] = []
    windows_license_rows: List[Dict[str, Any]] = []
    cost_summary_rows: List[Dict[str, Any]] = []
    full_year_rows: List[Dict[str, Any]] = []

    for compartment_ocid in selected_children:
        print(f"[INFO] Listing instances in compartment: {compartment_ocid}")
        instances = oci.pagination.list_call_get_all_results(
            compute.list_instances, compartment_id=compartment_ocid
        ).data

        for inst in instances:
            if inst.lifecycle_state != "RUNNING":
                continue

            print(f"[INFO] Processing instance: {inst.display_name} ({inst.id})")

            ocpus = getattr(getattr(inst, "shape_config", None), "ocpus", None)
            mem_gb = getattr(getattr(inst, "shape_config", None), "memory_in_gbs", None)

            (
                private_ips,
                vcn_name,
                vcn_ocid,
                subnet_name,
                subnet_ocid,
                sec_list_names,
                sec_list_ocids,
            ) = get_instance_networking(compute, vcn_client, inst, compartment_ocid)

            boot_size_gb, boot_ocid, boot_created = get_boot_volume(
                compute, blockstorage, inst, compartment_ocid
            )
            (
                data_volumes_str,
                data_volumes_size_gb,
                data_volume_summaries,
            ) = get_data_volumes(compute, blockstorage, inst, compartment_ocid)

            total_storage_gb = (boot_size_gb or 0) + data_volumes_size_gb

            now = datetime.utcnow()
            created = inst.time_created.replace(tzinfo=None)

            monthly_cost = get_resource_cost(
                usage_client, config, inst.id, now - timedelta(days=30), now
            )
            yearly_cost = get_resource_cost(
                usage_client, config, inst.id, now - timedelta(days=365), now
            )
            since_creation_cost = get_resource_cost(
                usage_client, config, inst.id, created, now
            )

            volume_entries: List[VolumeSummary] = []
            if boot_ocid:
                volume_entries.append(
                    VolumeSummary(
                        volume_id=boot_ocid,
                        size_gb=boot_size_gb or 0,
                        created=boot_created,
                        label="boot-volume",
                    )
                )
            volume_entries.extend(data_volume_summaries)
            (
                storage_monthly_cost,
                storage_yearly_cost,
                storage_since_creation_cost,
            ) = aggregate_costs_for_resources(usage_client, config, volume_entries, now)

            avg_cpu = get_avg_metric(
                monitoring_client, "CpuUtilization", inst.id, compartment_ocid, days=7
            )
            avg_mem = get_avg_metric(
                monitoring_client, "MemoryUtilization", inst.id, compartment_ocid, days=7
            )

            storage_growth_gb: Optional[float] = None
            if boot_ocid:
                storage_growth_gb = get_storage_forecast(
                    monitoring_client, boot_ocid, compartment_ocid
                )

            image_os, license_model = get_image_details(
                compute, getattr(getattr(inst, "source_details", None), "image_id", None)
            )

            (
                windows_hourly_cost,
                windows_monthly_cost,
                windows_since_creation_cost,
            ) = compute_windows_license_cost(image_os, ocpus, created, now)

            cost_since_creation_sar = usd_to_sar(since_creation_cost)
            windows_since_creation_sar = usd_to_sar(windows_since_creation_cost)
            final_cost_since_creation_usd = None
            final_cost_since_creation_sar = None

            if since_creation_cost is not None or windows_since_creation_cost is not None:
                final_cost_since_creation_usd = round(
                    (since_creation_cost or 0) + (windows_since_creation_cost or 0), 2
                )
                final_cost_since_creation_sar = usd_to_sar(final_cost_since_creation_usd)

            monthly_components = [
                monthly_cost or 0,
                storage_monthly_cost or 0,
                windows_monthly_cost or 0,
            ]
            full_year_usd = round(sum(monthly_components) * 12, 2)
            full_year_sar = usd_to_sar(full_year_usd)

            freeform_tags = json.dumps(inst.freeform_tags or {}, ensure_ascii=False)
            defined_tags = json.dumps(inst.defined_tags or {}, ensure_ascii=False)

            row_parent = child_parent_map.get(compartment_ocid, parent_compartment_ocid)

            row = {
                "Region": region,
                "Parent Compartment OCID": row_parent,
                "Compartment OCID": compartment_ocid,
                "Instance Name": inst.display_name,
                "Instance OCID": inst.id,
                "State": inst.lifecycle_state,
                "Availability Domain": inst.availability_domain,
                "Fault Domain": inst.fault_domain,
                "Shape": inst.shape,
                "OCPUs": ocpus,
                "Memory (GB)": mem_gb,
                "Created UTC": inst.time_created.strftime("%Y-%m-%d %H:%M:%S"),
                "Private IPs": private_ips,
                "VCN Name": vcn_name,
                "VCN OCID": vcn_ocid,
                "Subnet Name": subnet_name,
                "Subnet OCID": subnet_ocid,
                "Security Lists": sec_list_names,
                "Security Lists OCIDs": sec_list_ocids,
                "Boot Volume Size (GB)": boot_size_gb,
                "Boot Volume OCID": boot_ocid,
                "Data Volumes": data_volumes_str,
                "Total Storage (GB)": total_storage_gb,
                "Storage Monthly Cost (USD)":
                    storage_monthly_cost if storage_monthly_cost is not None else "",
                "Storage Yearly Cost (USD)":
                    storage_yearly_cost if storage_yearly_cost is not None else "",
                "Storage Cost Since Creation (USD)":
                    storage_since_creation_cost
                    if storage_since_creation_cost is not None
                    else "",
                "Monthly Cost (USD)": monthly_cost if monthly_cost is not None else "",
                "Yearly Cost (USD)": yearly_cost if yearly_cost is not None else "",
                "Cost Since Creation (USD)":
                    since_creation_cost if since_creation_cost is not None else "",
                "Cost Since Creation (SAR)":
                    cost_since_creation_sar if cost_since_creation_sar is not None else "",
                "Operating System": image_os,
                "License Model": license_model or "",
                "Avg CPU Utilization % (7d)": avg_cpu if avg_cpu is not None else "",
                "Avg Memory Utilization % (7d)": avg_mem if avg_mem is not None else "",
                "Forecast Storage Growth (GB/30d)":
                    storage_growth_gb if storage_growth_gb is not None else "",
                "Freeform Tags": freeform_tags,
                "Defined Tags": defined_tags,
                "_windows_hourly_cost": windows_hourly_cost,
                "_windows_monthly_cost": windows_monthly_cost,
                "_windows_since_creation_cost": windows_since_creation_cost,
                "_final_cost_since_creation_usd": final_cost_since_creation_usd,
                "_final_cost_since_creation_sar": final_cost_since_creation_sar,
                "_full_year_usd": full_year_usd,
                "_full_year_sar": full_year_sar,
            }

            rows.append(row)

            inventory_rows.append(
                {
                    "Region": region,
                    "Instance Name": inst.display_name,
                    "State": inst.lifecycle_state,
                    "OCPUs": ocpus,
                    "Memory (GB)": mem_gb,
                    "Created UTC": inst.time_created.strftime("%Y-%m-%d %H:%M:%S"),
                    "Private IPs": private_ips,
                    "Subnet Name": subnet_name,
                    "Boot Volume Size (GB)": boot_size_gb,
                    "Data Volumes": data_volumes_str,
                    "Total Storage (GB)": total_storage_gb,
                    "Storage Monthly Cost (USD)": storage_monthly_cost,
                    "Storage Yearly Cost (USD)": storage_yearly_cost,
                    "Storage Cost Since Creation (USD)": storage_since_creation_cost,
                    "Monthly Cost (USD)": monthly_cost,
                    "Yearly Cost (USD)": yearly_cost,
                    "Cost Since Creation (USD)": since_creation_cost,
                    "Cost Since Creation (SAR)": cost_since_creation_sar,
                    "Operating System": image_os,
                    "License Model": license_model or "",
                    "Avg CPU Utilization % (7d)": avg_cpu,
                    "Avg Memory Utilization % (7d)": avg_mem,
                    "Forecast Storage Growth (GB/30d)": storage_growth_gb,
                    "Defined Tags": defined_tags,
                }
            )

            if windows_hourly_cost is not None:
                windows_license_rows.append(
                    {
                        "Instance": inst.display_name,
                        "OS": image_os,
                        "OCPUs": ocpus,
                        "License cost per hour (USD)": windows_hourly_cost,
                        "Approx per 30-day month (USD)": windows_monthly_cost,
                        "Since creation (USD)": windows_since_creation_cost,
                        "Since creation (SAR)": windows_since_creation_sar,
                    }
                )

            cost_summary_rows.append(
                {
                    "Instance Name": inst.display_name,
                    "Cost Since Creation resources (USD)": since_creation_cost,
                    "Cost Since Creation resources (SAR)": cost_since_creation_sar,
                    "Since creation Windows OS (USD)": windows_since_creation_cost,
                    "Since creation Windows OS (SAR)": windows_since_creation_sar,
                    "Final COST USD": final_cost_since_creation_usd,
                    "Final COST SAR": final_cost_since_creation_sar,
                }
            )

            full_year_rows.append(
                {
                    "Instance Name": inst.display_name,
                    "Cost Since Creation (USD)": since_creation_cost,
                    "Full Year (USD)": full_year_usd,
                    "Cost Since Creation (SAR)": cost_since_creation_sar,
                    "Full Year (SAR)": full_year_sar,
                }
            )

    write_csv(rows, REPORT_CSV)

    # Append totals to cost summary and full-year tabs
    if cost_summary_rows:
        total_resource = round(
            sum(r["Cost Since Creation resources (USD)"] or 0 for r in cost_summary_rows), 2
        )
        total_resource_sar = usd_to_sar(total_resource)
        total_windows = round(
            sum(r["Since creation Windows OS (USD)"] or 0 for r in cost_summary_rows), 2
        )
        total_windows_sar = usd_to_sar(total_windows)
        final_usd_total = round(total_resource + total_windows, 2)
        final_sar_total = usd_to_sar(final_usd_total)
        cost_summary_rows.append(
            {
                "Instance Name": "TOTAL",
                "Cost Since Creation resources (USD)": total_resource,
                "Cost Since Creation resources (SAR)": total_resource_sar,
                "Since creation Windows OS (USD)": total_windows,
                "Since creation Windows OS (SAR)": total_windows_sar,
                "Final COST USD": final_usd_total,
                "Final COST SAR": final_sar_total,
            }
        )

    if full_year_rows:
        total_since_creation = round(
            sum(r["Cost Since Creation (USD)"] or 0 for r in full_year_rows if r), 2
        )
        total_full_year = round(sum(r["Full Year (USD)"] or 0 for r in full_year_rows), 2)
        total_since_creation_sar = usd_to_sar(total_since_creation)
        total_full_year_sar = usd_to_sar(total_full_year)
        full_year_rows.append(
            {
                "Instance Name": "TOTAL",
                "Cost Since Creation (USD)": total_since_creation,
                "Full Year (USD)": total_full_year,
                "Cost Since Creation (SAR)": total_since_creation_sar,
                "Full Year (SAR)": total_full_year_sar,
            }
        )

    write_xlsx_workbook(
        inventory_rows, windows_license_rows, cost_summary_rows, full_year_rows, REPORT_XLSX
    )
    with open(REPORT_JSON, "w", encoding="utf-8") as json_file:
        json.dump(rows, json_file, indent=2, default=str)
    print(f"[INFO] JSON written to {REPORT_JSON}")

    summary_body = (
        f"Region: {region}\n"
        f"Instances processed: {len(rows)}\n"
        f"CSV: {REPORT_CSV}\n"
        f"XLSX: {REPORT_XLSX}\n"
        f"JSON: {REPORT_JSON}\n"
        f"Generated at: {datetime.utcnow().isoformat()}Z"
    )

    send_report_email(
        REPORT_CSV, REPORT_XLSX, REPORT_JSON, summary_body, recipients=email_recipients
    )
    send_report_sms(
        f"OCI cyber report ready ({len(rows)} instances). Files at {REPORT_DIR}. Email sent to {email_recipients or EMAIL_RECIPIENTS}.",
        destination=sms_destination,
    )

    return {
        "rows_count": len(rows),
        "csv": REPORT_CSV,
        "xlsx": REPORT_XLSX,
        "json": REPORT_JSON,
    }


# -------------------------------------------------------------------
# LOCAL ENTRYPOINT
# -------------------------------------------------------------------

def run_cli() -> dict:
    """CLI entrypoint used by both filenames, preserving interactive prompts."""

    interactive_run = False
    if ENABLE_INTERACTIVE_PROMPTS and (sys.stdin.isatty() or FORCE_INTERACTIVE_PROMPTS):
        interactive_run = True
    else:
        if not ENABLE_INTERACTIVE_PROMPTS:
            print("[INFO] Interactive prompts disabled via ENABLE_INTERACTIVE_PROMPTS=false.")
        elif not sys.stdin.isatty() and not FORCE_INTERACTIVE_PROMPTS:
            print(
                "[INFO] No TTY detected; skipping prompts (set FORCE_INTERACTIVE=true to override)."
            )

    identity_for_prompt = get_identity_client_for_prompt() if interactive_run else None
    (
        runtime_parent_label,
        runtime_children,
        runtime_child_parent_map,
        runtime_email,
        runtime_sms,
    ) = resolve_runtime_inputs(identity_for_prompt, interactive=interactive_run)

    report_result = generate_report(
        parent_compartment_ocid=runtime_child_parent_map.get(
            runtime_children[0], PARENT_COMPARTMENT_OCID
        )
        if runtime_children
        else None,
        target_child_compartments=runtime_children,
        email_recipients=runtime_email,
        sms_destination=runtime_sms,
        child_parent_map=runtime_child_parent_map,
    )
    print("[INFO] Report generation finished.")
    print(json.dumps(report_result, indent=2))
    return report_result


if __name__ == "__main__":
    REPORT_RESULT = run_cli()


# -------------------------------------------------------------------
# OCI FUNCTION HANDLER
# -------------------------------------------------------------------

def handler(ctx: Any, data: Optional[bytes] = None) -> str:
    """
    OCI Functions entrypoint.
    - Deploy this file as a Python function.
    - Configure a Schedule/Event rule to trigger it daily.
    """
    result = generate_report()
    return json.dumps(result)