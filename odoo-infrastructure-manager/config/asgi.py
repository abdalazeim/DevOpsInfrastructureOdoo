import os

from django.core.asgi import get_asgi_application

_default = (
    "config.settings.production"
    if (os.environ.get("PORT") or os.environ.get("RENDER"))
    else "config.settings.development"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", _default)

application = get_asgi_application()
