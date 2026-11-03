from django.conf import settings


def site_context(request):
    """Expose site-wide template variables.

    - ``site_title`` / ``site_subtitle``: brand names (from settings).
    - ``html_lang`` and ``html_dir``: fixed to English and left-to-right.
    - ``app_font_family``: configured UI font when set.
    """
    font_family = getattr(settings, "APP_FONT_FAMILY", "Arial")
    try:
        from apps.core.services.system_settings import get_setting

        db_font = get_setting("ui_font_family", "").strip()
        if db_font:
            font_family = db_font
    except Exception:
        pass

    return {
        "site_title": getattr(settings, "SITE_TITLE", "Django Enterprise Template"),
        "site_subtitle": getattr(settings, "SITE_SUBTITLE", "Enterprise Starter"),
        "html_lang": "en",
        "html_dir": "ltr",
        "app_font_family": font_family,
    }
