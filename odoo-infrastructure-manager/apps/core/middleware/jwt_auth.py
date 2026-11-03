"""Authenticate Django function views with a Bearer JWT.

Session authentication remains first. If the request is still anonymous and
an ``Authorization: Bearer`` header is present, SimpleJWT is used so Android
and other API clients can call the same ``/api/v1/`` function views as the web UI.
"""

from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self._jwt = JWTAuthentication()

    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return None
        try:
            result = self._jwt.authenticate(request)
        except Exception:
            return None
        if result is None:
            return None
        request.user, request.auth = result
        return None
