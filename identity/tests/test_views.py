from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class LoginViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("knox_login")
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_login_with_valid_credentials_returns_200_and_token(self):
        response = self.client.post(
            self.url,
            {"username": "testuser", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_with_invalid_password_returns_400(self):
        response = self.client.post(
            self.url,
            {"username": "testuser", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_nonexistent_user_returns_400(self):
        response = self.client.post(
            self.url,
            {"username": "ghost", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_does_not_require_authentication(self):
        # AllowAny — unauthenticated requests must reach the view
        response = self.client.post(
            self.url,
            {"username": "testuser", "password": "testpass123"},
        )
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user_register")
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.user = User.objects.create_user(
            username="user", email="user@example.com", password="userpass"
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staffpass",
            is_staff=True,
        )
        self.valid_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
        }

    def test_unauthenticated_returns_401(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_returns_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_non_superuser_returns_403(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_create_user_returns_201(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_created_user_password_is_hashed(self):
        self.client.force_authenticate(user=self.superuser)
        self.client.post(self.url, self.valid_data)
        created_user = User.objects.get(username="newuser")
        self.assertTrue(created_user.check_password("newpass123"))
        self.assertNotEqual(created_user.password, "newpass123")
