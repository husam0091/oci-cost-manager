# OCI Cyber Compartment Report

This utility enumerates compute instances in the specified prod-tamam-cyber child compartments, collects networking, storage, utilization, and cost information, and exports the results to CSV, XLSX, and JSON. Optional email delivery is also supported for scheduled OCI Functions deployments.

## Prerequisites

- Python 3.9+
- Access to the target OCI tenancy with permissions to read compute, network, block storage, monitoring, and usage data.
- OCI credentials available via `~/.oci/config` (for local runs) or Resource Principal configuration (when deployed as an OCI Function).

Install dependencies locally:

```bash
pip install -r requirements.txt
```

## Running locally

Execute the script directly to generate the report files and print a summary. By default the
outputs are written to `~/oci_cyber_reports`. Override with `OCI_REPORT_DIR=/desired/path` if you
want a different location (for OCI Functions, set `OCI_REPORT_DIR=/tmp`).

```bash
python oci_report_cyber.py
```

If your environment is wired to call `oci-report-cyber.py`, a lightweight wrapper forwards to the
main module so either filename can be used interchangeably.

When run interactively (TTY) the script first prompts for **Production**, **Staging**, or **All**.
Choosing Production or Staging then lists the child compartments under that root so you can pick one
or many; the script automatically drills into any `*-compute` subcompartments it finds so instance
enumeration happens where the VMs live. Selecting **All** skips the child prompts and scans every
listed child (and compute subcompartment) under both roots. If child compartments cannot be listed
(for example, identity client unavailable), the script falls back to the provided production/staging
OCID lists and lets you paste comma-separated OCIDs when needed. You can also override the email
recipients and SMS destination during the prompts. Set `FORCE_INTERACTIVE=true` to show prompts even
without a TTY (for example, when piping output) or set `ENABLE_INTERACTIVE_PROMPTS=false` to skip
prompting entirely. Leave prompts blank to accept the defaults shown in brackets.

If outbound OCI API calls must bypass an HTTP/HTTPS proxy (to avoid MaxRetryError/ProxyError when
the proxy blocks `usageapi.*.oci.oraclecloud.com`, `telemetry.*.oraclecloud.com`, or
`iaas.*.oraclecloud.com`), set `BYPASS_OCI_PROXY=true` (the default) in the environment before
running the script. This strips proxy variables and appends common Oracle Cloud host suffixes to
`NO_PROXY`/`no_proxy`, including Usage API, Monitoring, Compute/VCN (`iaas.*`), and Identity
endpoints for the detected region. You can optionally extend the suffix list via
`OCI_NO_PROXY_SUFFIXES`.

Cost queries to the Usage API require day-aligned UTC timestamps; the script automatically truncates
the time windows to midnight UTC, caps requests to the 366-day Usage API limit, and retries throttled
or transiently failed lookups up to three times with backoff. Storage costs (boot + data volumes) are
summed separately with the same windows (last 30 days, last 365 days, since creation), alongside total
storage GB. The report also surfaces the instance operating system and image license model (for example,
Windows license included vs. BYOL) to make Windows licensing visible to recipients. Windows OS
licensing is estimated per OCPU hour (default `WINDOWS_LICENSE_PER_OCPU_HOUR=0.092`), with per-instance
hourly, 30-day, and since-creation estimates expressed in USD and SAR (rate `USD_TO_SAR_RATE`, default 3.75).

The XLSX now matches the provided OCI_Cyber_Prod_Cost_Analysis.xlsx layout with four tabs:

- **OCI_Instance_Inventory**: instance + storage + usage metrics plus SAR-converted costs.
- **Windows_License_Calculation**: per-instance Windows license hourly/monthly and since-creation costs.
- **Cost_Summary_(USD_SAR)**: resources vs. Windows OS since-creation costs and combined totals.
- **Full-Year Estimated Costs (USD)**: since-creation and annualized estimates (compute + storage + Windows license) in USD/SAR.

If you want to email the CSV/XLSX/JSON files, leave `ENABLE_EMAIL=true` (default) and ensure the external mailer script is accessible
at `/mnt/app-data/scripts/services/mail/mail.py` (override with `MAIL_SCRIPT_PATH`). The report will call that script using the
configured recipients (default: `hosamaldin.awd@tamam.life`) and include all generated report files as attachments. Customize the
category/monitor labels via `EMAIL_CATEGORY` and `EMAIL_MONITOR` if you need different subject prefixes.

SMS notifications are also enabled by default using `/mnt/app-data/scripts/services/sms/sms.sh` (override with `SMS_SCRIPT_PATH`).
Update the destination with `SMS_DESTINATION` (default: `0540372159`) or disable SMS by setting `ENABLE_SMS=false`.

To run the report in the background and capture logs to a file, use `nohup` (helpful for long lists
of instances or constrained shells):

```bash
mkdir -p ~/oci_cyber_reports
nohup env OCI_REPORT_DIR=~/oci_cyber_reports python oci_report_cyber.py \
  > ~/oci_cyber_reports/report.log 2>&1 &
tail -f ~/oci_cyber_reports/report.log
```

## Deploying as an OCI Function

The `handler` function serves as the OCI Functions entrypoint. Package the script with its dependencies, deploy it to your function application, and configure an Event or Schedule rule to trigger it (for example, daily). The function writes report files to `/tmp` and can optionally email them.