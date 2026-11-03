from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import SystemRole, UserGroup, UserProfile
from apps.accounts.services.permission_service import get_effective_permissions, has_permission


class EffectivePermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("operator", password="long-test-password")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)

    def test_permissions_are_additive_across_user_role_and_application_group(self):
        role = SystemRole.objects.create(name="Infrastructure operator", permissions=["server.view"])
        group = UserGroup.objects.create(name="Operations", permissions=["backup.restore"])
        self.profile.system_role = role
        self.profile.group = group
        self.profile.permissions = ["docker.container.start"]
        self.profile.save()

        grants = get_effective_permissions(self.user)
        self.assertCountEqual(grants, ["server.view", "backup.restore", "docker.container.start"])
        self.assertTrue(has_permission(self.user, "server.view"))
        self.assertTrue(has_permission(self.user, "docker.container.start"))
        self.assertTrue(has_permission(self.user, "backup.restore"))

    def test_legacy_underscore_code_matches_dotted_code(self):
        self.profile.permissions = ["infrastructure_view"]
        self.profile.save(update_fields=["permissions"])
        self.assertTrue(has_permission(self.user, "infrastructure.view"))

    def test_inactive_user_or_profile_never_receives_grants(self):
        self.profile.permissions = ["infrastructure_view"]
        self.profile.save(update_fields=["permissions"])
        self.profile.is_active = False
        self.profile.save(update_fields=["is_active"])
        self.assertEqual(get_effective_permissions(self.user), [])
        self.assertFalse(has_permission(self.user, "*"))

        self.profile.is_active = True
        self.profile.save(update_fields=["is_active"])
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(get_effective_permissions(self.user), [])

    def test_django_auth_group_permissions_are_included(self):
        from django.contrib.auth.models import Group, Permission

        permission = Permission.objects.filter(codename="add_managedhost").first()
        if permission is None:
            self.skipTest("ManagedHost content type permission is unavailable")
        group = Group.objects.create(name="Host editors")
        group.permissions.add(permission)
        self.user.groups.add(group)
        self.assertIn("add_managedhost", get_effective_permissions(self.user))


class PermissionGrantAPITests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user("manager", password="long-test-password")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.manager)
        self.profile.permissions = ["users_manage"]
        self.profile.save(update_fields=["permissions"])
        self.client.force_login(self.manager)

    def test_group_api_rejects_grants_the_actor_does_not_hold(self):
        response = self.client.post(
            "/api/users/groups",
            data='{"name":"Backup Operators","permissions":["backup.restore"]}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserGroup.objects.filter(name="Backup Operators").exists())

    def test_group_api_rejects_unknown_permission_codes(self):
        response = self.client.post(
            "/api/users/groups",
            data='{"name":"Unknown Grants","permissions":["shell.execute_anything"]}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserGroup.objects.filter(name="Unknown Grants").exists())


class AccountActivationAPITests(TestCase):
    def test_profile_disabled_user_cannot_start_a_new_session(self):
        user = get_user_model().objects.create_user("disabled", password="long-test-password")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_active = False
        profile.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/auth/login",
            data='{"username":"disabled","password":"long-test-password"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_auth_status_does_not_report_disabled_profile_as_logged_in(self):
        user = get_user_model().objects.create_user("inactive-profile", password="long-test-password")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_active = False
        profile.save(update_fields=["is_active"])
        self.client.force_login(user)
        response = self.client.get("/api/auth/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["logged_in"])
