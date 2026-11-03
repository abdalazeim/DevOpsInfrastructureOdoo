"""Language selection middleware.

Extends Django's LocaleMiddleware so the UI language can be switched via a
``?lang=ar`` / ``?lang=en`` query parameter (and persisted in a cookie).
This keeps API URLs clean (no i18n URL prefix).
"""

from django.conf import settings
from django.utils import translation


class LanguageSwitchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.GET.get("lang")
        if lang and lang in [code for code, _ in settings.LANGUAGES]:
            translation.activate(lang)
            request.LANGUAGE_CODE = translation.get_language()
            request.session["app_language"] = lang
            response = self.get_response(request)
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
            return response

        session_lang = request.session.get("app_language")
        if session_lang:
            translation.activate(session_lang)
            request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)
        return response
