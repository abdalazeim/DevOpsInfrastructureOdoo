# Security and data protection

Updated: 2026-11-07 | Status: locally reviewed, runtime security NOT VERIFIED

- No installation, container removal, database replacement, volume pruning or production-domain modification was executed during this audit.
- Existing Odoo containers are checked before managed deployment. Partial stacks or image mismatches fail instead of being silently adopted.
- Managed secrets/Compose use mode 0600 under mode 0700. These POSIX permissions have not been tested on Ubuntu in this audit. Docker administrators can read environment credentials; archives containing inspect/config data must remain private.
- Local Odoo/Traefik/Jenkins endpoints bind loopback. PostgreSQL is not published. Domain TLS, firewall exposure and authentication require independent live checks. Socket access grants broad Docker control even with a read-only mount.
- No chmod 777 guidance remains in the current operating guides. Historical originals are archived and must not be used as current instructions.
- Cleanup protects parents containing backup descendants and rejects unreadable trees. Ownership of shared Docker resources still needs careful review before any uninstall.
- New restore manifests require checksums and safe file names. Archives are inspected before database replacement. SHA-256 detects damage, not authenticity; trust the backup source.
- Legacy backup pruning is disabled unless `CONFIRM_BACKUP_PRUNE=yes` is explicitly set with a positive retention count.

Remaining review: restore semantics, legacy execution paths, current image/package vulnerabilities, actual host permissions, secret exposure in logs, and live Portainer HTTPS readiness. No vulnerability-database scan or penetration test was executed. [Readiness report](FINAL_PRODUCTION_READINESS_REPORT.md).
