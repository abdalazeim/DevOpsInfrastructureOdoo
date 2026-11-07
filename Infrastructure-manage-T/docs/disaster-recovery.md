# Backup and recovery runbook

Updated: 2026-11-07 | Live restoration drill: **NOT EXECUTED**

## Formats

The new instance helper `app/services/instance_backup.py` records `manifest.json` format 1, `database.sql`, `filestore.tar.gz`, `config.tar.gz` and `containers.json`. It stops a running app for consistency and restarts it in finally; the database stays available for pg_dump. Inspect/config archives can contain secrets. Keep them private and copy off-host using an approved secure channel.

MultiVersion scripts and their backup/restore Ansible roles use this helper. The CLI naming contract uses VERSION-INSTANCE containers, for example `odoo17-instance1` and `odoo17-instance1-db`. Do not pass a canonical `odoo17` stack as if it were `odoo17-instance1`: the helper's Python API accepts explicit app/db names but its backup CLI does not yet expose that mapping.

The legacy `automation/scripts/backup-db.sh` produces timestamped compressed dumps and companion filestore/metadata. It is a different format. Existing archives were not deleted or rewritten. New legacy metadata includes a filestore checksum; older archives without it need manual review before restoration. Never fabricate a checksum to bypass integrity checks on an untrusted archive.

`system_backup.py` produces configuration and SQL exports. Restoring this archive extracts files; it does not restore live databases automatically.

## Safe sequence

1. Identify exact source and target containers, database, filestore, mounts, addons and private configuration. Record image digests and backup format.
2. Capture and independently verify a fresh backup; preserve all existing backups. Check available disk space.
3. Restore to an isolated instance/network with a distinct port and no production routing. Do not perform the first restoration drill against production.
4. Verify database content, representative records/attachments, addon loading, HTTP login and permissions. A table count or HTTP 200 alone is insufficient.
5. Only after a successful drill prepare a reviewed production replacement/rollback plan.

Existing-instance replacement requires `--confirm-replace`; wrappers require their explicit confirmation mechanism. The helper takes a safety backup before replacement, rejects unsafe archives before Docker operations, and rejects read-only Odoo configuration mounts before replacing a database. A rejected operation is not a successful restore.

## Remaining limitations

The current helper keeps Odoo stopped until file copying and ownership restoration finish. A network-isolated maintenance container moves previous filestore/addon contents into uniquely named .restore-safety directories instead of merging or deleting them; it requires writable data and addon mounts. Unsupported mount layouts fail before database replacement. New-instance configuration and image-specific mount reconstruction still require a real drill; the helper is not approved for production recovery. For read-only managed configuration, use a reviewed isolated recovery procedure rather than removing mount protection.

Legacy restoration has separate host-path assumptions. Do not mix its archives with format-1 restoration. Retention is opt-in; automatic backup deletion is not part of the default audit workflow.

[Evidence and blockers](FINAL_PRODUCTION_READINESS_REPORT.md)
