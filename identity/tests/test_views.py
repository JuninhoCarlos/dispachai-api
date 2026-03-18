from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase


class UserAPIViewTestCase(APITestCase):
    def setUp(self):
        # Create a superuser for testing
        self.superuser = get_user_model().objects.create_superuser(
            username="superuser",
            email="superuser@example.com",
            password="superpassword",
        )

        # Create a regular staff user for testing
        self.staff_user = get_user_model().objects.create_user(
            username="staffuser",
            email="staffuser@example.com",
            password="staffpassword",
            is_staff=True,
        )

        # Create a regular user for testing
        self.regular_user = get_user_model().objects.create_user(
            username="regularuser",
            email="regularuser@example.com",
            password="regularpassword",
        )

        self.url = reverse("user_register")

    def test_superuser_can_create_user(self):
        pass
        # self.client.login(username="superuser", password="superpassword")
        # response = self.client.get(self.url)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_user_cannot_create_user(self):
        pass
        # self.client.login(username="staffuser", password="staffpassword")
        # response = self.client.get(self.url)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_create_user(self):
        pass
        # self.client.login(username="regularuser", password="regularpassword")
        # response = self.client.get(self.url)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_create_user(self):
        pass
        # response = self.client.get(self.url)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
