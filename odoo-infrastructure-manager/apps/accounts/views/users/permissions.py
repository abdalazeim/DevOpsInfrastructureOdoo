from django.http import JsonResponse

from apps.core.utils.decorators import api_login_required
from ...permissions.catalog import get_all_groups, get_all_permissions


@api_login_required
def list_permissions(request):
    return JsonResponse(
        {
            "permissions": get_all_permissions(),
            "groups": get_all_groups(),
        }
    )
