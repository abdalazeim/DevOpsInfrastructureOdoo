"""Read-only Docker client, daemon and Compose diagnostics."""
import json
import shutil

from app.services.runtime_inspector import probe


def inspect_engine():
    path = shutil.which("docker")
    daemon_path = shutil.which("dockerd")
    report = {"status": "missing", "path": path, "daemon_path": daemon_path,
              "client_version": "", "server_version": "", "compose": "",
              "context": "", "details": {}, "errors": []}
    if not path:
        if daemon_path:
            report["status"] = "client_missing"
        return report
    code, output = probe([path, "--version"])
    if code:
        report["status"] = "client_error"
        report["errors"].append(output)
        return report
    report["client_version"] = output
    code, output = probe([path, "context", "show"])
    if code == 0:
        report["context"] = output
    else:
        report["errors"].append(output)
    code, output = probe([path, "compose", "version"])
    report["compose"] = output if code == 0 else "غير متاح أو تعذر تشغيله"
    if code:
        report["errors"].append(output)
    code, output = probe([path, "info", "--format", "{{json .}}"])
    if code:
        report["status"] = "permission_denied" if "permission denied" in output.lower() else "unreachable"
        report["errors"].append(output)
        return report
    try:
        data = json.loads(output)
        if not isinstance(data, dict) or not data.get("ServerVersion"):
            raise ValueError("Missing Docker server version")
    except ValueError:
        report["status"] = "invalid_response"
        report["errors"].append("تعذر قراءة تفاصيل المحرك من نتيجة docker info.")
        return report
    report["status"] = "running"
    report["server_version"] = data["ServerVersion"]
    report["details"] = {key: data[key] for key in
                         ("Name", "OperatingSystem", "Architecture", "DockerRootDir",
                          "Driver", "Containers", "ContainersRunning", "ContainersStopped", "Images")
                         if key in data}
    return report


STATUS_TEXT = {
    "missing": "لم يُعثر على docker أو dockerd في PATH؛ التثبيت غير مكتشف.",
    "client_missing": "dockerd موجود، لكن عميل docker غير موجود في PATH.",
    "client_error": "عميل Docker موجود لكن تعذر تشغيله.",
    "permission_denied": "عميل Docker مثبت، لكن الوصول إلى المحرك مرفوض بسبب الصلاحيات.",
    "unreachable": "عميل Docker مثبت، لكن المحرك غير متاح: قد تكون الخدمة متوقفة أو الاتصال غير صحيح.",
    "invalid_response": "عميل Docker مثبت، لكن تفاصيل المحرك غير صالحة.",
    "running": "عميل Docker مثبت والمحرك المحدد بالاتصال الحالي يعمل ويستجيب.",
}
