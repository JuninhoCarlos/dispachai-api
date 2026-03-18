from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from identity.permissions import IsSuperUser


class IsSuperUserPermissionTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsSuperUser()
        self.superuser = User.objects.create_superuser(
            username="su", email="su@example.com", password="pass"
        )
        self.regular_user = User.objects.create_user(
            username="user", email="user@example.com", password="pass"
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass",
            is_staff=True,
        )

    def _make_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_has_permission(self):
        request = self._make_request(self.superuser)
        self.assertTrue(self.permission.has_permission(request, None))

    def test_regular_user_denied(self):
        request = self._make_request(self.regular_user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_staff_user_denied(self):
        # is_staff=True but is_superuser=False must be denied
        request = self._make_request(self.staff_user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_unauthenticated_user_denied(self):
        request = self._make_request(AnonymousUser())
        self.assertFalse(self.permission.has_permission(request, None))
