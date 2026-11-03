"""Force the single supported interface language: English."""

from django.conf import settings
from django.utils import translation


class LanguageSwitchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        translation.activate("en")
        request.LANGUAGE_CODE = "en"
        return self.get_response(request)
