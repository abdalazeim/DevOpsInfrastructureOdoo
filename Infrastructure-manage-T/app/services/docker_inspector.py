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
    report["compose"] = output if code == 0 else "unavailable or could not be run"
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
        report["errors"].append("Could not read engine details from docker info output.")
        return report
    report["status"] = "running"
    report["server_version"] = data["ServerVersion"]
    report["details"] = {key: data[key] for key in
                         ("Name", "OperatingSystem", "Architecture", "DockerRootDir",
                          "Driver", "Containers", "ContainersRunning", "ContainersStopped", "Images")
                         if key in data}
    return report


STATUS_TEXT = {
    "missing": "docker or dockerd not found in PATH; installation not detected.",
    "client_missing": "dockerd exists, but docker client is not found in PATH.",
    "client_error": "Docker client exists but could not be run.",
    "permission_denied": "Docker client is installed, but access to the engine is denied due to permissions.",
    "unreachable": "Docker client is installed, but the engine is unavailable; service may be stopped or connection is incorrect.",
    "invalid_response": "Docker client is installed, but engine details are invalid.",
    "running": "Docker client is installed and the specified connection engine is running and responding.",
}
