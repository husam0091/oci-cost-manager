#!/usr/bin/env python3
"""Compatibility wrapper for environments that expect `oci-report-cyber.py`.

Delegates to `oci_report_cyber.py` so both filenames can be used interchangeably.
"""

from oci_report_cyber import handler, run_cli  # noqa: F401


if __name__ == "__main__":
    run_cli()