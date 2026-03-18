from django.contrib.auth import get_user_model
from django.test import TestCase

from identity.serializers import UserSerializer

User = get_user_model()


class UserSerializerTestCase(TestCase):
    def test_create_hashes_password(self):
        serializer = UserSerializer(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password": "plaintext",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        db_user = User.objects.get(pk=user.pk)
        self.assertTrue(db_user.check_password("plaintext"))
        self.assertNotEqual(db_user.password, "plaintext")

    def test_password_field_is_write_only(self):
        user = User.objects.create_user(username="u", password="pass")
        serializer = UserSerializer(user)
        self.assertNotIn("password", serializer.data)

    def test_create_superuser_flag(self):
        serializer = UserSerializer(
            data={
                "username": "su",
                "email": "su@example.com",
                "password": "pass",
                "is_superuser": True,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertTrue(user.is_superuser)
