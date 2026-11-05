from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.accounts.services.permission_service import has_permission
from apps.core.services.audit_service import log_audit
from apps.core.utils.decorators import api_login_required
from apps.core.utils.http import api_error, api_response
from apps.reports.exports.csv_export import build_csv_response
from apps.reports.exports.pdf_export import build_pdf_response
from apps.reports.services.reports import (
    ReportInputError,
    can_export_report,
    can_view_report,
    export_report_rows,
    get_report,
    parse_report_filters,
    preview_report,
    report_catalog_item,
    visible_reports,
)


@api_login_required
@require_GET
def catalog(request):
    if not has_permission(request.user, "reports.view"):
        return api_error("Report view permission required.", status=403)
    return api_response(
        [
            report_catalog_item(
                report,
                can_export=has_permission(request.user, "reports.export"),
            )
            for report in visible_reports(request.user)
        ],
        message="Available reports loaded.",
    )


@api_login_required
@require_GET
def preview(request, report_slug):
    report = get_report(report_slug)
    if report is None:
        return api_error("Report not found.", status=404)
    if not can_view_report(request.user, report):
        return api_error("Report view permission required.", status=403)
    try:
        filters = parse_report_filters(
            request.GET,
            allowed_parameters={"from", "to", "host", "page", "page_size"},
        )
        result = preview_report(
            report,
            filters,
            request.GET.get("page", "1"),
            request.GET.get("page_size", "25"),
        )
    except ReportInputError as exc:
        return api_error(str(exc), status=400)
    return api_response(result, message="Report preview loaded.")


@api_login_required
@require_GET
def export(request, report_slug):
    report = get_report(report_slug)
    if report is None:
        return api_error("Report not found.", status=404)
    if not can_export_report(request.user, report):
        return api_error("Report export and source view permissions are required.", status=403)
    try:
        filters = parse_report_filters(
            request.GET,
            allowed_parameters={"from", "to", "host", "format"},
        )
        file_format = request.GET.get("format", "").strip().lower()
        rows = export_report_rows(report, filters, file_format)
    except ReportInputError as exc:
        return api_error(str(exc), status=400)

    filename = f"reports-{report.slug}-{timezone.localdate().isoformat()}.{file_format}"
    if file_format == "csv":
        response = build_csv_response(report, rows, filename)
    else:
        response = build_pdf_response(report, rows, filename, filters["audit"])

    log_audit(
        request,
        action="other",
        module="reports.export",
        object_id=report.slug,
        object_repr=f"{report.slug}:{file_format}",
        new_value={"filters": filters["audit"], "row_count": len(rows)},
    )
    return response
