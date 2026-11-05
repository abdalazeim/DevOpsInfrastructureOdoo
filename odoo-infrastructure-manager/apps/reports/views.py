from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.accounts.services.permission_service import has_permission
from apps.reports.services.reports import report_catalog_item, visible_reports


@login_required
@require_GET
def reports_page(request):
    if not has_permission(request.user, "reports.view"):
        return HttpResponseForbidden("Report view permission required.")
    reports = [
        report_catalog_item(
            report,
            can_export=has_permission(request.user, "reports.export"),
        )
        for report in visible_reports(request.user)
    ]
    return render(
        request,
        "dashboard/reports.html",
        {
            "reports": reports,
            "nav_sections": _dashboard_navigation("reports"),
        },
    )


def _dashboard_navigation(active):
    from apps.dashboard.views import _navigation as dashboard_navigation

    return dashboard_navigation(active=active)
