from django.urls import path
from . import views

app_name = 'infrastructure'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/health/', views.api_health, name='api_health'),
    path('api/profiles/', views.api_profiles, name='api_profiles'),
    path('api/containers/', views.api_containers, name='api_containers'),
    path('api/preflight/', views.api_preflight, name='api_preflight'),
    path('api/operations/', views.api_operations, name='api_operations'),
    path('api/operations/<str:op_id>/', views.api_operation_detail, name='api_operation_detail'),
]
