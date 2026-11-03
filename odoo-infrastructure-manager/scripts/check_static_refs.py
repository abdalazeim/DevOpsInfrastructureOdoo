import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.test import Client

c = Client()
html = c.get("/", HTTP_HOST="localhost").content.decode("utf-8", "ignore")
refs = set(re.findall(r'(?:src|href)="([^"]*static[^"]*)"', html))
print("total refs:", len(refs))
missing = 0
for r in sorted(refs):
    p = "static/" + r.split("/static/")[-1].split("?")[0]
    if os.path.exists(p):
        print("OK       " + r)
    else:
        missing += 1
        print("MISSING  " + r)
print("missing:", missing)
