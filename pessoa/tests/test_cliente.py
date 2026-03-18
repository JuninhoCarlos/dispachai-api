from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pessoa.models import Cliente


class ClienteListAPIViewTestCase(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.url = reverse("cliente_list")
        self.user = User.objects.create_user(
            username="user", email="user@example.com", password="userpass"
        )
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        Cliente.objects.create(nome="Cliente Um", cpf="529.982.247-25")
        Cliente.objects.create(nome="Cliente Dois")

    def test_get_clientes_requires_authentication(self):
        response = self.api_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_clientes_with_regular_user_returns_200(self):
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_clientes_returns_all_records(self):
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get(self.url)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_response_contains_expected_fields(self):
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get(self.url)
        first = response.data["results"][0]
        for field in ["id", "nome", "cpf", "criado_em"]:
            self.assertIn(field, first)

    def test_post_method_not_allowed(self):
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.post(self.url, {"nome": "Novo"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
