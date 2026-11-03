from django.urls import path
from django.views.generic import RedirectView

app_name = 'infrastructure'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard:index', permanent=False), name='dashboard'),
]
