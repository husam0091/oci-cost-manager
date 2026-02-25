-- Phase 1 production core fixes.
-- Run on PostgreSQL after backup.

BEGIN;

-- 1) Disable demo mode and enable safe production features.
UPDATE settings
SET
  enable_demo_mode = FALSE,
  enable_oci_executors = TRUE,
  enable_budget_auto_eval = TRUE,
  enable_destructive_actions = FALSE,
  updated_at = NOW()
WHERE id = 1;

-- 2) Remove root-bound OCI file paths so runtime uses OCI_CONFIG_FILE secret mount.
UPDATE settings
SET
  oci_config_file = NULL,
  oci_key_file = NULL,
  updated_at = NOW()
WHERE id = 1
  AND (
    COALESCE(oci_config_file, '') LIKE '/root/.oci/%'
    OR COALESCE(oci_key_file, '') LIKE '/root/.oci/%'
  );

COMMIT;
