import csv
from io import StringIO

from django.http import HttpResponse


MAX_CELL_LENGTH = 30000
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def build_csv_response(report, rows, filename):
    output = StringIO(newline="")
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow([label for _, label in report.columns])
    for row in rows:
        writer.writerow(
            [_safe_cell(row.get(key)) for key, _ in report.columns]
        )
    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _safe_cell(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    value = value[:MAX_CELL_LENGTH]
    if value.lstrip("\ufeff \t\r\n").startswith(_FORMULA_PREFIXES):
        value = "'" + value
    return value
