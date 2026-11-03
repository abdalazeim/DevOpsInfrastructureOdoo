from django.conf import settings


def site_context(request):
    """Expose site-wide template variables.

    - ``site_title`` / ``site_subtitle``: brand names (from settings).
    - ``html_lang``: active language code (``ar`` / ``en``).
    - ``html_dir``: ``rtl`` for Arabic, ``ltr`` otherwise.
    - ``app_font_family``: configured UI font (Cairo / Tajawal / ...),
      resolved from the ``ui_font_family`` SystemSetting when set.
    """
    lang = getattr(request, "LANGUAGE_CODE", None) or settings.LANGUAGE_CODE

    font_family = getattr(settings, "APP_FONT_FAMILY", "Cairo")
    try:
        from apps.core.services.system_settings import get_setting

        db_font = get_setting("ui_font_family", "").strip()
        if db_font:
            font_family = db_font
        db_lang = get_setting("ui_language", "").strip()
        if db_lang in ("ar", "en"):
            lang = db_lang
    except Exception:
        pass

    return {
        "site_title": getattr(settings, "SITE_TITLE", "Django Enterprise Template"),
        "site_subtitle": getattr(settings, "SITE_SUBTITLE", "Enterprise Starter"),
        "html_lang": lang,
        "html_dir": "rtl" if lang.startswith("ar") else "ltr",
        "app_font_family": font_family,
    }
