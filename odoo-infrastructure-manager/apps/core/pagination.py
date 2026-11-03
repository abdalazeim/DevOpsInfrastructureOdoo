"""DRF pagination classes that emit the unified API response envelope."""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EnvelopePageNumberPagination(PageNumberPagination):
    """PageNumberPagination that wraps results in the standard envelope.

    Output shape matches ``api_response_paginated`` from apps.core.utils.http::

        {"success": true, "message": "", "data": {"items": [...], "meta": {...}}, "errors": null}
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "message": "",
                "data": {
                    "items": data,
                    "meta": {
                        "page": self.page.number,
                        "page_size": self.get_page_size(self.request),
                        "total": self.page.paginator.count,
                        "pages": self.page.paginator.num_pages,
                        "has_next": self.page.has_next(),
                        "has_previous": self.page.has_previous(),
                    },
                },
                "errors": None,
            }
        )
