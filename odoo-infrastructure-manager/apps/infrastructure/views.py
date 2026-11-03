import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


def dashboard(request):
    return render(request, 'pages/infrastructure.html')


@require_http_methods(["GET"])
def api_health(request):
    return JsonResponse({"status": "ok", "service": "odoo-infrastructure-manager-django"})


@require_http_methods(["GET"])
def api_profiles(request):
    # Return from the original app
    try:
        from app.models.profile import InfrastructureProfile
        import os, yaml
        profiles = []
        for path in ['profiles/example.yaml', 'profiles/devops-odoo-prod.yaml', 'profiles/local-dev.yaml']:
            full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), path)
            if not os.path.exists(full_path):
                # try relative
                full_path = path
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r') as f:
                        data = yaml.safe_load(f) or {}
                    profiles.append(InfrastructureProfile.from_dict(data).__dict__)
                except:
                    pass
        if not profiles:
            profiles.append(InfrastructureProfile(profile_name="example").__dict__)
        return JsonResponse(profiles, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def api_containers(request):
    try:
        import subprocess
        res = subprocess.run(["docker", "ps", "-a", "--format", "{{json .}}"], capture_output=True, text=True, timeout=10)
        containers = []
        for line in res.stdout.strip().splitlines():
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except:
                    pass
        return JsonResponse(containers, safe=False)
    except Exception as e:
        return JsonResponse([], safe=False)


@require_http_methods(["GET"])
def api_preflight(request):
    try:
        from app.services.smart_inspector import SmartInspectorService
        report = SmartInspectorService.run_full_inspection()
        # Convert to dict
        from dataclasses import asdict
        return JsonResponse(asdict(report), safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET", "POST"])
def api_operations(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return JsonResponse({"status": "accepted", "data": data})
        except:
            return JsonResponse({"status": "accepted"}, status=202)
    return JsonResponse([])


@require_http_methods(["GET"])
def api_operation_detail(request, op_id):
    return JsonResponse({"id": op_id, "status": "pending"})
