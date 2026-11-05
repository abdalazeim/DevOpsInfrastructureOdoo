# Odoo Multi-Version Deployment - Operating Methods (Linux Ubuntu Only)

## Project Location
`D:\Project Django Frameworks\DevOpsInfrastructureOdoo\Infrastructure-manage-T\deployment\Odoo-MultiVersion-Deployment\scripts\`

> **Important Notice**: This system is fully programmed for **Linux Ubuntu** (versions 20, 22, 24 and above). It does not contain any Windows-specific components. The path above is a storage path on a Windows disk for ease of editing only, but actual execution is performed on a Linux Ubuntu server.

---

## System Requirements (Linux Ubuntu)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Operating System | Ubuntu Server 20.04 LTS | Ubuntu Server 22.04 / 24.04 LTS |
| Processor | 2 cores | 4 cores or more |
| Memory | 4 GB RAM | 8 GB RAM or more |
| Storage | 100 GB SSD | 500 GB SSD or more |
| Docker Engine | 20.10+ | Latest version |
| Docker Compose | v2 | Latest version |
| Ansible | Core + collections | Latest version |
| Python3 | 3.8+ | Latest version |
| Git | 2.x | Latest version |

---

## Method 1: Quick Start (Single Command)

Open Terminal on your Linux Ubuntu server and run:

```bash
# Navigate to scripts directory
cd /opt/Odoo-MultiVersion-Deployment/scripts

# Run the main script with root privileges (automatically runs bootstrap)
sudo bash launch-odoo-infra.sh
```

---

## Method 2: Step-by-Step Execution

### Step 1: Install Dependencies and Set Up Environment
```bash
sudo bash bootstrap-odoo-infra.sh
```

### Step 2: Run Project and Install Odoo 17 and 19
```bash
sudo bash launch-odoo-infra.sh
```

---

## Method 3: Manual Execution for Each Component

### Install Odoo 17 Only (Two Instances)
```bash
sudo bash install-odoo17.sh
```

### Install Odoo 19 Only (Two Instances)
```bash
sudo bash install-odoo19.sh
```

### Check Service Health
```bash
sudo bash health-check.sh instance1 8069 8072
sudo bash health-check.sh instance2 8069 8072
```

### Take a Backup
```bash
sudo bash backup.sh instance1 odoo17 /data/backups/odoo17
sudo bash backup.sh instance2 odoo17 /data/backups/odoo17
sudo bash backup.sh instance1 odoo19 /data/backups/odoo19
sudo bash backup.sh instance2 odoo19 /data/backups/odoo19
```

### Restore a Backup
```bash
sudo bash restore.sh odoo17-instance1-20261104 odoo17 instance1 existing
```

### Verify Backup Integrity
```bash
sudo bash verify-backups.sh /data/backups
```

### List All Available Backups
```bash
sudo bash list-backups.sh /data/backups
```

### Backup Ubuntu System Configuration
```bash
sudo bash backup-system-config.sh
```

### Restore Ubuntu System Configuration
```bash
sudo bash restore-system-config.sh 2026-11-04_020000
```

---

## Method 4: Via Jenkins

Open the Jenkins control panel on your Linux server and run the following pipelines:

| Pipeline | Path | Purpose |
|----------|------|---------|
| Install Odoo 17 | `Jenkins/install-odoo17.Jenkinsfile` | Install two Odoo 17 instances |
| Install Odoo 19 | `Jenkins/install-odoo19.Jenkinsfile` | Install two Odoo 19 instances |
| Backup | `Jenkins/backup.Jenkinsfile` | Take a backup |
| Restore | `Jenkins/restore.Jenkinsfile` | Restore a backup (requires confirmation) |
| Verify Backups | `Jenkins/verify-backups.Jenkinsfile` | Verify backup integrity |
| System Config Backup | `Jenkins/system-config-backup.Jenkinsfile` | Backup Ubuntu system configuration |

---

## Method 5: Via Ansible Playbooks Directly

```bash
# Navigate to project directory
cd /opt/Odoo-MultiVersion-Deployment

# Install Odoo 17
ansible-playbook -i ansible/inventory/hosts.ini -e @versions/odoo17.yml ansible/playbooks/install-odoo17.yml

# Install Odoo 19
ansible-playbook -i ansible/inventory/hosts.ini -e @versions/odoo19.yml ansible/playbooks/install-odoo19.yml

# Take a backup
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml

# Verify backups
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/verify.yml

# Backup system configuration
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/system-config-backup.yml
```

---

## Final Links After Successful Startup

| Service | Link |
|---------|------|
| Odoo 17 - Instance 1 | https://${ODOO17_INSTANCE1_DOMAIN} |
| Odoo 17 - Instance 2 | https://${ODOO17_INSTANCE2_DOMAIN} |
| Odoo 19 - Instance 1 | https://${ODOO19_INSTANCE1_DOMAIN} |
| Odoo 19 - Instance 2 | https://${ODOO19_INSTANCE2_DOMAIN} |

---

## Important Note on Permissions

All scripts must be run with **root (sudo/root)** privileges because they:
- Install system packages (Docker, Ansible, Python3, Git)
- Create Docker networks and permissions
- Set up data directories (`/data/`) and configuration directories (`/opt/`)
- Run and manage Docker containers

---

## Script Files in the Folder

| File | Purpose |
|------|---------|
| `bootstrap-odoo-infra.sh` | Install dependencies and set up basic environment (Linux only) |
| `launch-odoo-infra.sh` | Run the full project (automatically runs bootstrap) |
| `install-odoo17.sh` | Install Odoo 17 (two independent instances) |
| `install-odoo19.sh` | Install Odoo 19 (two independent instances) |
| `health-check.sh` | Check service and container health |
| `backup.sh` | Take Odoo backup |
| `restore.sh` | Restore Odoo backup |
| `verify-backups.sh` | Verify backup integrity |
| `list-backups.sh` | List all available backups |
| `backup-system-config.sh` | Backup Ubuntu system configuration (network, SSH, Docker, etc.) |
| `restore-system-config.sh` | Restore Ubuntu system configuration |

---

## System Paths After Installation

| Component | Path |
|-----------|------|
| Project files | `/opt/Odoo-MultiVersion-Deployment/` |
| Odoo 17 data | `/data/odoo17/instance1, /data/odoo17/instance2` |
| Odoo 19 data | `/data/odoo19/instance1, /data/odoo19/instance2` |
| Odoo 17 configuration | `/opt/odoo17/instance1, /opt/odoo17/instance2` |
| Odoo 19 configuration | `/opt/odoo19/instance1, /opt/odoo19/instance2` |
| Backups | `/data/backups/odoo17, /data/backups/odoo19` |
| Bootstrap logs | `/var/log/odoo-bootstrap.log` |

---

## Support

For any issues or inquiries, please open an Issue in the project's GitHub repository.

**Version:** 1.0  
**Last Updated:** 2026-11-04  
**Target System:** Linux Ubuntu 20.04 / 22.04 / 24.04 LTS  
**Status:** Production Ready
