from django.contrib import admin

from .models import User, UserGroup, UserProfile, SystemRole


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "get_full_name", "email", "department", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "group", "system_role", "is_active")


@admin.register(SystemRole)
class SystemRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
