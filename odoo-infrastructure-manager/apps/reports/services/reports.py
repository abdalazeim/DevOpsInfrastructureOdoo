from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.accounts.services.permission_service import has_permission
from apps.backup.models import BackupArtifact
from apps.infrastructure.models import ManagedHost
from apps.monitoring.models import AlertEvent
from apps.tasks.models import Task

MAX_PREVIEW_PAGE_SIZE = 100
MAX_CSV_ROWS = 5000
MAX_PDF_ROWS = 300
MAX_DATE_RANGE_DAYS = 365


@dataclass(frozen=True)
class ReportDefinition:
    slug: str
    title: str
    permission: str
    columns: tuple
    date_field: str
    host_filter_field: str


REPORTS = (
    ReportDefinition(
        slug="servers",
        title="Server inventory",
        permission="server.view",
        date_field="created_at",
        host_filter_field="pk",
        columns=(
            ("id", "ID"), ("name", "Name"), ("hostname", "Hostname"),
            ("server_type", "Type"), ("environment", "Environment"),
            ("connection_status", "Connection status"),
            ("operating_system", "Operating system"), ("os_version", "OS version"),
            ("architecture", "Architecture"), ("location", "Location"),
            ("enabled", "Enabled"), ("created_at", "Created at"),
        ),
    ),
    ReportDefinition(
        slug="alerts",
        title="Alert history",
        permission="monitoring.view",
        date_field="created_at",
        host_filter_field="host_id",
        columns=(
            ("id", "ID"), ("created_at", "Created at"), ("host", "Host"),
            ("title", "Alert"), ("status", "Status"), ("occurrences", "Occurrences"),
            ("acknowledged", "Acknowledged"), ("resolved_at", "Resolved at"),
        ),
    ),
    ReportDefinition(
        slug="tasks",
        title="Task history",
        permission="task.view",
        date_field="created_at",
        host_filter_field="target_server_id",
        columns=(
            ("id", "ID"), ("name", "Task"), ("operation", "Operation"),
            ("status", "Status"), ("priority", "Priority"), ("target", "Target"),
            ("requested_by", "Requested by"), ("created_at", "Created at"),
            ("started_at", "Started at"), ("finished_at", "Finished at"),
        ),
    ),
    ReportDefinition(
        slug="backups",
        title="Backup history",
        permission="backup.view",
        date_field="created_at",
        host_filter_field="host_id",
        columns=(
            ("id", "ID"), ("created_at", "Created at"), ("status", "Status"),
            ("host", "Host"), ("service", "Service"), ("policy", "Policy"),
            ("file_name", "File name"), ("size_bytes", "Size (bytes)"),
        ),
    ),
)

_REPORTS_BY_SLUG = {report.slug: report for report in REPORTS}


class ReportInputError(ValueError):
    """Raised when a report filter or pagination value is invalid."""


@dataclass(frozen=True)
class DateBound:
    raw: str
    value: datetime
    lookup: str


def get_report(slug):
    return _REPORTS_BY_SLUG.get(slug)


def can_view_report(user, report):
    return has_permission(user, "reports.view") and has_permission(
        user, report.permission
    )


def can_export_report(user, report):
    return can_view_report(user, report) and has_permission(user, "reports.export")


def visible_reports(user):
    if not has_permission(user, "reports.view"):
        return []
    return [report for report in REPORTS if has_permission(user, report.permission)]


def report_catalog_item(report, *, can_export=False):
    return {
        "slug": report.slug,
        "title": report.title,
        "columns": [{"key": key, "label": label} for key, label in report.columns],
        "supports_host_filter": True,
        "can_export": can_export,
    }


def parse_report_filters(params, *, allowed_parameters):
    unexpected = set(params.keys()) - set(allowed_parameters)
    if unexpected:
        raise ReportInputError(
            f"Unsupported filter parameter: {sorted(unexpected)[0]}."
        )

    start = _parse_bound(params.get("from", ""), "from")
    end = _parse_bound(params.get("to", ""), "to")
    if start and end:
        start_day = start.value.date()
        end_day = end.value.date() - (
            timedelta(days=1) if end.lookup == "lt" else timedelta()
        )
        if start_day > end_day or (
            start.lookup == "gte"
            and end.lookup == "lte"
            and start_day == end_day
            and start.value > end.value
        ):
            raise ReportInputError("'from' must not be later than 'to'.")
        if (end_day - start_day).days > MAX_DATE_RANGE_DAYS:
            raise ReportInputError(
                f"The date range cannot exceed {MAX_DATE_RANGE_DAYS} days."
            )

    host_id = None
    raw_host = (params.get("host") or "").strip()
    if raw_host:
        try:
            host_id = int(raw_host)
        except (TypeError, ValueError):
            raise ReportInputError("'host' must be a positive host ID.") from None
        if host_id < 1:
            raise ReportInputError("'host' must be a positive host ID.")
    return {
        "start": start,
        "end": end,
        "host_id": host_id,
        "audit": {
            key: value
            for key, value in (
                ("from", start.raw if start else ""),
                ("to", end.raw if end else ""),
                ("host", host_id),
            )
            if value not in ("", None)
        },
    }


def _parse_bound(raw, name):
    raw = (raw or "").strip()
    if not raw:
        return None

    parsed_date = parse_date(raw)
    if parsed_date is not None:
        value = datetime.combine(parsed_date, time.min)
        lookup = "gte"
        if name == "to":
            value += timedelta(days=1)
            lookup = "lt"
        return DateBound(
            raw,
            timezone.make_aware(value, timezone.get_current_timezone()),
            lookup,
        )

    parsed_datetime = parse_datetime(raw)
    if parsed_datetime is None:
        raise ReportInputError(f"'{name}' must be an ISO-8601 date or datetime.")
    if timezone.is_naive(parsed_datetime):
        parsed_datetime = timezone.make_aware(
            parsed_datetime, timezone.get_current_timezone()
        )
    return DateBound(raw, parsed_datetime, "gte" if name == "from" else "lte")


def report_queryset(report, filters):
    if report.slug == "servers":
        queryset = ManagedHost.objects.all().order_by("name", "pk")
    elif report.slug == "alerts":
        queryset = AlertEvent.objects.select_related("host").all().order_by(
            "-created_at", "-pk"
        )
    elif report.slug == "tasks":
        queryset = Task.objects.select_related(
            "target_server", "requested_by"
        ).all().order_by("-created_at", "-pk")
    elif report.slug == "backups":
        queryset = BackupArtifact.objects.select_related(
            "host", "service", "policy"
        ).all().order_by("-created_at", "-pk")
    else:
        raise ValueError(f"Unsupported report definition: {report.slug}")

    if filters["start"]:
        queryset = queryset.filter(**{
            f"{report.date_field}__{filters['start'].lookup}": filters["start"].value
        })
    if filters["end"]:
        queryset = queryset.filter(**{
            f"{report.date_field}__{filters['end'].lookup}": filters["end"].value
        })
    if filters["host_id"] is not None:
        queryset = queryset.filter(**{report.host_filter_field: filters["host_id"]})
    return queryset


def serialize_report_row(report, obj):
    if report.slug == "servers":
        values = {
            "id": obj.pk,
            "name": obj.name,
            "hostname": obj.hostname,
            "server_type": obj.server_type,
            "environment": obj.environment,
            "connection_status": obj.connection_status,
            "operating_system": obj.operating_system,
            "os_version": obj.os_version,
            "architecture": obj.architecture,
            "location": obj.location,
            "enabled": obj.enabled,
            "created_at": _iso(obj.created_at),
        }
    elif report.slug == "alerts":
        values = {
            "id": obj.pk,
            "created_at": _iso(obj.created_at),
            "host": obj.host.name if obj.host else "",
            "title": obj.title,
            "status": "resolved" if obj.resolved_at else "open",
            "occurrences": obj.occurrences,
            "acknowledged": obj.acknowledged_at is not None,
            "resolved_at": _iso(obj.resolved_at),
        }
    elif report.slug == "tasks":
        values = {
            "id": str(obj.pk),
            "name": obj.name,
            "operation": obj.operation,
            "status": obj.status,
            "priority": obj.priority,
            "target": obj.target_server.name if obj.target_server else "",
            "requested_by": obj.requested_by.username if obj.requested_by else "",
            "created_at": _iso(obj.created_at),
            "started_at": _iso(obj.started_at),
            "finished_at": _iso(obj.finished_at),
        }
    elif report.slug == "backups":
        values = {
            "id": obj.pk,
            "created_at": _iso(obj.created_at),
            "status": obj.status,
            "host": obj.host.name if obj.host else "",
            "service": obj.service.name if obj.service else "",
            "policy": obj.policy.name if obj.policy else "",
            "file_name": obj.file_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
            "size_bytes": obj.size_bytes,
        }
    else:
        raise ValueError(f"Unsupported report definition: {report.slug}")
    return values


def preview_report(report, filters, page_number, page_size):
    try:
        page_number = int(page_number)
        page_size = int(page_size)
    except (TypeError, ValueError):
        raise ReportInputError("'page' and 'page_size' must be integers.") from None
    if page_number < 1:
        raise ReportInputError("'page' must be a positive integer.")
    if not 1 <= page_size <= MAX_PREVIEW_PAGE_SIZE:
        raise ReportInputError(
            f"'page_size' must be between 1 and {MAX_PREVIEW_PAGE_SIZE}."
        )

    paginator = Paginator(report_queryset(report, filters), page_size)
    if page_number > max(1, paginator.num_pages):
        raise ReportInputError("'page' is outside the available results.")
    page = paginator.page(page_number)
    return {
        "report": report_catalog_item(report),
        "items": [
            serialize_report_row(report, item) for item in page.object_list
        ],
        "meta": {
            "page": page.number,
            "page_size": page_size,
            "total": paginator.count,
            "pages": paginator.num_pages,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        },
    }


def export_report_rows(report, filters, file_format):
    if file_format not in {"csv", "pdf"}:
        raise ReportInputError("'format' must be either 'csv' or 'pdf'.")
    limit = MAX_CSV_ROWS if file_format == "csv" else MAX_PDF_ROWS
    objects = list(report_queryset(report, filters)[: limit + 1])
    if len(objects) > limit:
        raise ReportInputError(
            f"This export exceeds the {limit}-row {file_format.upper()} limit. "
            "Narrow the filters and try again."
        )
    return [serialize_report_row(report, obj) for obj in objects]


def _iso(value):
    return value.isoformat() if value is not None else ""
