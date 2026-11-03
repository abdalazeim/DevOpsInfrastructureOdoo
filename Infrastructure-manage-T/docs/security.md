# Security & Hardening Architecture

## Security Principles

1. **Least Privilege (Principle of Least Privilege)**:
   - Traefik containers run with `security_opt: no-new-privileges:true`.
   - Host volumes are mounted read-only (`:ro`) wherever write access is not required.
   
2. **PostgreSQL Network Isolation**:
   - PostgreSQL instances (`odoo17-db` and `odoo19-db`) do **NOT** publish ports to the host interface (`0.0.0.0:5432` is not bound).
   - Only Odoo containers located on the internal bridge network (`odoo17_internal` / `odoo19_internal`) can reach PostgreSQL.
   - External internet and Traefik cannot access database ports directly.

3. **Secrets Management**:
   - No passwords or tokens are stored in YAML profiles or committed to Git.
   - All database credentials, master passwords, and ACME tokens are referenced via environment variables (`.env`).
   - `.env` must be assigned restrictive Unix permissions:
     ```bash
     chmod 600 .env
     ```
   - Traefik `acme.json` certificate store is strictly managed with `chmod 600`.

4. **Firewall & Kernel Hardening**:
   - UFW default rules: allow SSH (port 22), HTTP (port 80), and HTTPS (port 443).
   - Sysctl tunings for high-concurrency connection queues (`somaxconn`), memory map limits (`max_map_count`), and file handles.

5. **Safe Subprocess Execution**:
   - All shell scripts enforce `set -Eeuo pipefail`.
   - Python execution service uses parameter lists (`List[str]`), avoiding string interpolation vulnerabilities.
   - Destructive operations (`down -v`, database drop) require mandatory typed safety tokens and explicit flags (`--force`).
