import json

from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def infra_json(value):
    """Render nested discovery values as compact, safely escaped JSON."""
    return format_html("<code class=\"discovery-value\">{}</code>", json.dumps(value, ensure_ascii=True, sort_keys=True))
