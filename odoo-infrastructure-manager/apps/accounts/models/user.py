from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    employee_number = models.CharField(max_length=50, blank=True)
    is_active_user = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="utilities_user_set",
        blank=True,
        help_text="The groups this user belongs to.",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="utilities_user_set",
        blank=True,
        help_text="Specific permissions for this user.",
    )

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمين"

    def __str__(self):
        return f"{self.get_full_name() or self.username}"


class UserGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="اسم المجموعة")
    description = models.TextField(blank=True, verbose_name="الوصف")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_groups"
        verbose_name = "مجموعة مستخدمين"
        verbose_name_plural = "مجموعات المستخدمين"

    def __str__(self):
        return self.name


class SystemRole(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم الصلاحية")
    description = models.TextField(blank=True, default="", verbose_name="الوصف")
    permissions = models.JSONField(default=list, blank=True, verbose_name="الصلاحيات")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "system_roles"
        verbose_name = "صلاحية نظام"
        verbose_name_plural = "صلاحيات النظام"

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    group = models.ForeignKey(
        UserGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المجموعة",
    )
    system_role = models.ForeignKey(
        SystemRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="صلاحية النظام",
    )
    permissions = models.JSONField(
        default=list, blank=True, verbose_name="الصلاحيات الفعلية"
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_profiles"
        verbose_name = "ملف مستخدم"
        verbose_name_plural = "ملفات المستخدمين"

    def __str__(self):
        return f"{self.user.username}"
