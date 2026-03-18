from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pagamento.tests import create_advogado
from pessoa.models import Corretor


class CorretorListCreateAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("corretor_list_create")
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.user = User.objects.create_user(
            username="user", email="user@example.com", password="userpass"
        )
        self.advogado = create_advogado()
        self.valid_data = {
            "nome": "Corretor Teste",
            "email": "corretor@example.com",
            "advogado": self.advogado.id,
            "comissao_padrao": "30.00",
        }

    def test_get_corretores_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_corretores_with_regular_user_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_corretores_with_superuser_returns_200(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_corretor_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_corretor_unauthenticated_returns_401(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_corretor_with_superuser_returns_201(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Corretor.objects.count(), 1)
        self.assertEqual(Corretor.objects.first().nome, "Corretor Teste")

    def test_create_corretor_unique_email_constraint(self):
        self.client.force_authenticate(user=self.superuser)
        self.client.post(self.url, self.valid_data)
        data = {**self.valid_data, "nome": "Outro Corretor"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_create_corretor_invalid_comissao_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        data = {**self.valid_data, "comissao_padrao": "150.00"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
