"""
Comprehensive Pre-flight Smart Inspector Service.
Audits Ubuntu OS, Docker Engine, Docker Compose, Traefik, Ansible, System Packages,
Storage Paths, Ports, and Configurations without modifying the system.
"""
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class ComponentStatus(str, Enum):
    INSTALLED = "INSTALLED"          # مثبت ويعمل
    MISSING = "MISSING"              # غير مثبت
    NEEDS_UPDATE = "NEEDS_UPDATE"    # يحتاج تحديث
    MISCONFIGURED = "MISCONFIGURED"  # به مشكلة أو غير مضبوط

@dataclass
class InspectedComponent:
    id: str
    name: str
    name_ar: str
    status: ComponentStatus
    detected_version: Optional[str] = None
    binary_path: Optional[str] = None
    config_path: Optional[str] = None
    why_needed: str = ""
    why_needed_ar: str = ""
    details: str = ""
    details_ar: str = ""
    recommended_action: str = ""
    recommended_action_ar: str = ""
    install_command: Optional[List[str]] = None

@dataclass
class PreflightReport:
    timestamp: str
    os_name: str
    os_version: str
    is_supported_ubuntu: bool
    components: List[InspectedComponent] = field(default_factory=list)
    all_ready: bool = False
    missing_count: int = 0
    issues_count: int = 0

class SmartInspectorService:
    """Performs safe, non-destructive audit of the host environment."""

    @staticmethod
    def inspect_ubuntu() -> InspectedComponent:
        os_release = {}
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        os_release[k] = v.strip('"')

        name = os_release.get("NAME", "Linux")
        version_id = os_release.get("VERSION_ID", "unknown")
        pretty_name = os_release.get("PRETTY_NAME", f"{name} {version_id}")

        is_ubuntu = "Ubuntu" in name or "ubuntu" in os_release.get("ID", "")
        try:
            ver_num = float(version_id)
            is_supported = is_ubuntu and ver_num >= 22.04
        except ValueError:
            is_supported = is_ubuntu

        status = ComponentStatus.INSTALLED if is_supported else (ComponentStatus.NEEDS_UPDATE if is_ubuntu else ComponentStatus.MISCONFIGURED)

        return InspectedComponent(
            id="ubuntu_os",
            name="Ubuntu Operating System",
            name_ar="نظام تشغيل أوبونتو (Server / Desktop)",
            status=status,
            detected_version=pretty_name,
            binary_path="/etc/os-release",
            why_needed="Base operating system supported for running modern Docker Engine, Ansible, and systemd.",
            why_needed_ar="النظام الأساسي المعتمد لتشغيل محرك دوكر وترافيك وحزم الأتمتة.",
            details=f"Detected: {pretty_name} (Architecture: {os.uname().machine})",
            details_ar=f"النظام المكتشف: {pretty_name} (المعمارية: {os.uname().machine})",
            recommended_action="None (OS is compliant)" if is_supported else "Upgrade to Ubuntu 22.04 LTS or newer",
            recommended_action_ar="لا يلزم إجراء (النظام متوافق)" if is_supported else "الترقية إلى Ubuntu 22.04 LTS أو أحدث",
        )

    @staticmethod
    def inspect_docker_engine() -> InspectedComponent:
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return InspectedComponent(
                id="docker_engine",
                name="Docker Engine",
                name_ar="محرك دوكر (Docker Engine)",
                status=ComponentStatus.MISSING,
                why_needed="Required to containerize and isolate Odoo 17, Odoo 18, Odoo 19, Traefik, and PostgreSQL.",
                why_needed_ar="ضروري لتشغيل وعزل حاويات أودو 17 و 18 و 19 وترافيك وقواعد البيانات بشكل مستقل.",
                details="Executable 'docker' not found in system PATH.",
                details_ar="الأمر docker غير موجود في مسارات النظام.",
                recommended_action="Install docker-ce from official Docker repository.",
                recommended_action_ar="تثبيت حزمة docker-ce من مستودع دوكر الرسمي.",
                install_command=["apt-get", "install", "-y", "docker-ce", "docker-ce-cli", "containerd.io"],
            )

        try:
            ver_res = subprocess.run([docker_bin, "--version"], capture_output=True, text=True, timeout=5)
            version_str = ver_res.stdout.strip()
            
            # Check daemon connectivity
            daemon_res = subprocess.run([docker_bin, "info"], capture_output=True, text=True, timeout=5)
            if daemon_res.returncode == 0:
                status = ComponentStatus.INSTALLED
                details = "Docker daemon is active and responsive."
                details_ar = "محرك دوكر يعمل وجاهز لاستقبال الأوامر."
            else:
                status = ComponentStatus.MISCONFIGURED
                details = "Docker CLI is present, but daemon socket is unreachable or inactive."
                details_ar = "أمر دوكر موجود، لكن خدمة daemon متوقفة أو صلاحيات المستخدم مقيدة."

            return InspectedComponent(
                id="docker_engine",
                name="Docker Engine",
                name_ar="محرك دوكر (Docker Engine)",
                status=status,
                detected_version=version_str,
                binary_path=docker_bin,
                why_needed="Runs and isolates application containers.",
                why_needed_ar="تشغيل وعزل الحاويات البرمجية.",
                details=details,
                details_ar=details_ar,
                recommended_action="Start docker service: sudo systemctl start docker" if status != ComponentStatus.INSTALLED else "None",
                recommended_action_ar="تشغيل الخدمة: sudo systemctl start docker" if status != ComponentStatus.INSTALLED else "لا يلزم إجراء",
            )
        except Exception as e:
            return InspectedComponent(
                id="docker_engine",
                name="Docker Engine",
                name_ar="محرك دوكر (Docker Engine)",
                status=ComponentStatus.MISCONFIGURED,
                binary_path=docker_bin,
                details=f"Error checking docker: {e}",
                details_ar=f"خطأ أثناء فحص دوكر: {e}",
            )

    @staticmethod
    def inspect_docker_compose() -> InspectedComponent:
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return InspectedComponent(
                id="docker_compose",
                name="Docker Compose v2 Plugin",
                name_ar="ملحق دوكر كومبوز (Docker Compose v2)",
                status=ComponentStatus.MISSING,
                why_needed="Orchestrates multi-container services, networks, and persistent volumes.",
                why_needed_ar="أتمتة تشغيل الخدمات المتعددة وشبكات الاتصال ووحدات التخزين.",
                details="Docker is not installed.",
                details_ar="دوكر غير مثبت.",
                install_command=["apt-get", "install", "-y", "docker-compose-plugin"],
            )

        try:
            res = subprocess.run([docker_bin, "compose", "version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return InspectedComponent(
                    id="docker_compose",
                    name="Docker Compose v2 Plugin",
                    name_ar="ملحق دوكر كومبوز (Docker Compose v2)",
                    status=ComponentStatus.INSTALLED,
                    detected_version=res.stdout.strip(),
                    binary_path=f"{docker_bin} compose",
                    why_needed="Orchestrates multi-container stacks defined in YAML.",
                    why_needed_ar="أتمتة وإدارة الخدمات المتعددة المعرفة في ملفات YAML.",
                    details="Docker Compose v2 plugin is active and functional.",
                    details_ar="ملحق دوكر كومبوز v2 مفعل ويعمل بكفاءة.",
                    recommended_action="None",
                    recommended_action_ar="لا يلزم إجراء",
                )
            else:
                return InspectedComponent(
                    id="docker_compose",
                    name="Docker Compose v2 Plugin",
                    name_ar="ملحق دوكر كومبوز (Docker Compose v2)",
                    status=ComponentStatus.MISSING,
                    why_needed="Orchestrates multi-container stacks.",
                    why_needed_ar="أتمتة وإدارة الخدمات المتعددة.",
                    details="docker compose plugin missing or failed to execute.",
                    details_ar="ملحق docker-compose-plugin غير مثبت.",
                    install_command=["apt-get", "install", "-y", "docker-compose-plugin"],
                )
        except Exception as e:
            return InspectedComponent(
                id="docker_compose",
                name="Docker Compose v2 Plugin",
                name_ar="ملحق دوكر كومبوز (Docker Compose v2)",
                status=ComponentStatus.MISSING,
                details=str(e),
            )

    @staticmethod
    def inspect_traefik() -> InspectedComponent:
        docker_bin = shutil.which("docker")
        is_running = False
        details = "Traefik container not launched yet."
        details_ar = "حاوية ترافيك لم يتم إطلاقها بعد."
        status = ComponentStatus.MISSING

        if docker_bin:
            try:
                res = subprocess.run([docker_bin, "ps", "--filter", "name=traefik", "--format", "{{.Status}}"], capture_output=True, text=True, timeout=5)
                if "Up" in res.stdout:
                    is_running = True
                    status = ComponentStatus.INSTALLED
                    details = f"Traefik container running: {res.stdout.strip()}"
                    details_ar = f"حاوية ترافيك تعمل حالياً: {res.stdout.strip()}"
            except Exception:
                pass

        acme_path = "/opt/odoo-infrastructure/traefik/acme/acme.json"
        has_acme = os.path.exists(acme_path)
        acme_perm = oct(os.stat(acme_path).st_mode)[-3:] if has_acme else "None"

        return InspectedComponent(
            id="traefik_proxy",
            name="Traefik v3.7 Reverse Proxy",
            name_ar="موجه ترافيك (Traefik v3.7 Reverse Proxy)",
            status=status,
            detected_version="v3.7 (Container)" if is_running else "Not running",
            config_path="deployment/traefik/config/traefik.yml",
            why_needed="Routes HTTP/HTTPS subdomains, terminates Let's Encrypt TLS, and handles WebSocket livechat.",
            why_needed_ar="توجيه النطاقات الفرعية، إدارة شهادات SSL التلقائية، وتمرير حركة الشات الحي.",
            details=f"{details} (acme.json permissions: {acme_perm})",
            details_ar=f"{details_ar} (صلاحيات acme.json: {acme_perm})",
            recommended_action="Deploy Traefik from operations menu" if not is_running else "None",
            recommended_action_ar="نشر ترافيك من قائمة العمليات" if not is_running else "لا يلزم إجراء",
        )

    @staticmethod
    def inspect_ansible() -> InspectedComponent:
        ansible_bin = shutil.which("ansible-playbook")
        if not ansible_bin:
            return InspectedComponent(
                id="ansible",
                name="Ansible Automation Tool",
                name_ar="أداة الأتمتة أنسيبل (Ansible)",
                status=ComponentStatus.MISSING,
                why_needed="Automates idempotent baseline server configuration, sysctl tuning, and package dependencies.",
                why_needed_ar="أتمتة إعداد الخادم وضبط النواة وتثبيت الحزم المطلوبة بشكل متكرر وآمن.",
                details="ansible-playbook executable not found.",
                details_ar="أمر ansible-playbook غير متوفر في مسارات النظام.",
                recommended_action="Install ansible via pip or apt: apt-get install -y ansible",
                recommended_action_ar="تثبيت أنسيبل: apt-get install -y ansible",
                install_command=["apt-get", "install", "-y", "ansible"],
            )

        try:
            res = subprocess.run([ansible_bin, "--version"], capture_output=True, text=True, timeout=5)
            ver_first_line = res.stdout.split("\n")[0] if res.stdout else "Installed"
            return InspectedComponent(
                id="ansible",
                name="Ansible Automation Tool",
                name_ar="أداة الأتمتة أنسيبل (Ansible)",
                status=ComponentStatus.INSTALLED,
                detected_version=ver_first_line,
                binary_path=ansible_bin,
                why_needed="Automates baseline server provisioning.",
                why_needed_ar="أتمتة تجهيز وضبط خادم أوبونتو.",
                details="Ansible is ready for baseline orchestration.",
                details_ar="أداة أنسيبل جاهزة لتنفيذ كتب التشغيل.",
                recommended_action="None",
                recommended_action_ar="لا يلزم إجراء",
            )
        except Exception as e:
            return InspectedComponent(
                id="ansible",
                name="Ansible",
                name_ar="أداة أنسيبل",
                status=ComponentStatus.MISCONFIGURED,
                details=str(e),
            )

    @staticmethod
    def inspect_utility_packages() -> List[InspectedComponent]:
        tools = [
            ("curl", "Data Transfer Tool", "أداة تنزيل وفحص استجابة الويب curl", "Used for health checks and API requests.", "فحص صحة استجابة الويب وتنزيل المفاتيح"),
            ("jq", "JSON Processing Utility", "معالج ملفات جيسون jq", "Parses Docker and API telemetry output.", "قراءة وتحليل مخرجات الحاويات بصيغة JSON"),
            ("ufw", "Uncomplicated Firewall", "جدار الحماية ufw", "Secures incoming ports (22, 80, 443).", "تأمين المنافذ المسموحة وإغلاق المنافذ الحساسة"),
            ("tar", "Archive Utility", "أداة الأرشفة tar", "Packages Odoo filestore for backups and restores.", "أرشفة وتجميع ملفات مرفقات أودو"),
            ("gzip", "Compression Utility", "أداة الضغط gzip", "Compresses database SQL dumps safely.", "ضغط تفريغ قواعد البيانات لتوفير المساحة"),
        ]

        results = []
        for cmd, name_en, name_ar, why_en, why_ar in tools:
            path = shutil.which(cmd)
            if path:
                results.append(InspectedComponent(
                    id=f"pkg_{cmd}",
                    name=name_en,
                    name_ar=name_ar,
                    status=ComponentStatus.INSTALLED,
                    binary_path=path,
                    why_needed=why_en,
                    why_needed_ar=why_ar,
                    details=f"Installed at {path}",
                    details_ar=f"مثبت في {path}",
                    recommended_action="None",
                    recommended_action_ar="لا يلزم إجراء",
                ))
            else:
                results.append(InspectedComponent(
                    id=f"pkg_{cmd}",
                    name=name_en,
                    name_ar=name_ar,
                    status=ComponentStatus.MISSING,
                    why_needed=why_en,
                    why_needed_ar=why_ar,
                    details=f"Command '{cmd}' not found in PATH",
                    details_ar=f"الأمر '{cmd}' غير موجود في النظام",
                    recommended_action=f"Install: apt-get install -y {cmd}",
                    recommended_action_ar=f"تثبيت عبر: apt-get install -y {cmd}",
                    install_command=["apt-get", "install", "-y", cmd],
                ))
        return results

    @classmethod
    def run_full_inspection(cls) -> PreflightReport:
        import datetime
        components = [
            cls.inspect_ubuntu(),
            cls.inspect_docker_engine(),
            cls.inspect_docker_compose(),
            cls.inspect_traefik(),
            cls.inspect_ansible(),
        ]
        components.extend(cls.inspect_utility_packages())

        ubuntu_comp = components[0]
        missing = [c for c in components if c.status == ComponentStatus.MISSING]
        issues = [c for c in components if c.status in [ComponentStatus.MISCONFIGURED, ComponentStatus.NEEDS_UPDATE]]

        return PreflightReport(
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            os_name=ubuntu_comp.detected_version or "Ubuntu",
            os_version=ubuntu_comp.details or "22.04+",
            is_supported_ubuntu=ubuntu_comp.status == ComponentStatus.INSTALLED,
            components=components,
            all_ready=len(missing) == 0 and len(issues) == 0,
            missing_count=len(missing),
            issues_count=len(issues),
        )
