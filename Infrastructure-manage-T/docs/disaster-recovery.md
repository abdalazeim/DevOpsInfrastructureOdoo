# Disaster Recovery & Backup Runbook

## 1. Backup Strategy

The backup subsystem combines:
- **Logical Database Dumps**: `pg_dump -U odoo -d <db> --clean --if-exists | gzip > dump_<db>_<timestamp>.sql.gz`
- **Filestore Snapshots**: Archived via `tar -czf filestore_<db>_<timestamp>.tar.gz`
- **Integrity Checksums**: Automated SHA256 hashing recorded in JSON metadata.
- **Retention Lifecycle**: Automatically purges backups older than the configured threshold (default: 7 revisions).

## 2. Interactive Restore Protocol

1. **Pre-flight Integrity Check**:
   - Validates that the backup archive is non-empty and readable.
2. **Automated Safety Backup**:
   - Before executing a destructive restore on an existing database, the manager creates an immediate snapshot:
     `/opt/odoo-infrastructure/backups/safety_pre_restore/safety_<db>_<timestamp>.sql.gz`
3. **Connection Termination**:
   - Drops active queries/sessions from `pg_stat_activity` to prevent lock contention.
4. **Data Injection**:
   - Database is dropped and recreated with clean UTF-8 encoding.
   - Streamed via `gunzip` into `psql`.
   - Companion filestore is extracted into `/var/lib/odoo/filestore/<db>`.
5. **Post-Restore Verification**:
   - Query count on `information_schema.tables`.

## 3. Disaster Recovery Testing Checklist

- [ ] Execute `backup-db.sh 17 odoo17_prod`
- [ ] Inspect SHA256 checksum in metadata
- [ ] Test restore onto a staging database name: `restore-db.sh 17 <path> odoo17_stage_test --force`
- [ ] Verify HTTP login on staging database
