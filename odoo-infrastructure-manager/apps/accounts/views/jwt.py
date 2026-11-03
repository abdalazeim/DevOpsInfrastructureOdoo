"""JWT views that emit the unified API envelope used by Android clients."""

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .auth import _user_profile_dict

User = get_user_model()


def _envelope(success, message, data=None, errors=None, extra=None):
    payload = {
        "success": success,
        "message": message,
        "data": data,
        "errors": errors,
        "error": None if success else message,
    }
    if extra:
        payload.update(extra)
    return payload


class EnvelopeTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = _user_profile_dict(self.user)
        return data


class EnvelopeTokenObtainPairView(TokenObtainPairView):
    serializer_class = EnvelopeTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        body = response.data
        if response.status_code >= 400:
            message = "بيانات تسجيل الدخول غير صحيحة"
            if isinstance(body, dict):
                detail = body.get("detail") or body.get("message")
                if detail:
                    message = str(detail)
            response.data = _envelope(False, message, errors=body)
            return response

        access = body.get("access")
        refresh = body.get("refresh")
        user = body.get("user")
        data = {"access": access, "refresh": refresh, "user": user}
        # Keep top-level tokens so older clients that skip the envelope still work.
        response.data = _envelope(
            True,
            "تم تسجيل الدخول بنجاح",
            data=data,
            extra={"access": access, "refresh": refresh},
        )
        return response


class EnvelopeTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        body = response.data
        if response.status_code >= 400:
            message = "تعذر تجديد الجلسة"
            if isinstance(body, dict):
                detail = body.get("detail") or body.get("message")
                if detail:
                    message = str(detail)
            response.data = _envelope(False, message, errors=body)
            return response

        access = body.get("access")
        refresh = body.get("refresh")
        data = {"access": access, "refresh": refresh}
        extra = {"access": access}
        if refresh:
            extra["refresh"] = refresh
        response.data = _envelope(True, "تم تجديد الجلسة", data=data, extra=extra)
        return response
