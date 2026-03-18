from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pessoa.models import Advogado


class AdvogadoListCreateAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("advogado_list_create")
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.user = User.objects.create_user(
            username="user", email="user@example.com", password="userpass"
        )
        self.advogado_data = {
            "nome": "Advogado Teste",
            "oab_numero": "123456",
            "email": "advogado@example.com",
            "telefone": "123456789",
            "comissao_padrao": 50.00,
        }

    def test_get_advogados_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_advogados_with_authentication(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_advogado_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.advogado_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_advogado_with_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url, self.advogado_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Advogado.objects.count(), 1)
        advogado = Advogado.objects.first()
        self.assertEqual(advogado.nome, self.advogado_data["nome"])

    def test_advogado_model_validation(self):
        self.client.force_authenticate(user=self.superuser)
        invalid_data = self.advogado_data.copy()
        invalid_data["comissao_padrao"] = 150.00  # Invalid commission
        response = self.client.post(self.url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comissao_padrao", response.data)

    def test_advogado_unique_oab(self):
        self.client.force_authenticate(user=self.superuser)
        # Create the first Advogado
        self.client.post(self.url, self.advogado_data)
        # Attempt to create another Advogado with the same OAB number
        duplicate_oab_data = self.advogado_data.copy()
        duplicate_oab_data["email"] = "new_email@example.com"  # Ensure email is unique
        response = self.client.post(self.url, duplicate_oab_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("oab_numero", response.data)

    def test_advogado_unique_email(self):
        self.client.force_authenticate(user=self.superuser)
        # Create the first Advogado
        self.client.post(self.url, self.advogado_data)
        # Attempt to create another Advogado with the same email
        duplicate_email_data = self.advogado_data.copy()
        duplicate_email_data["oab_numero"] = "654321"  # Ensure OAB number is unique
        response = self.client.post(self.url, duplicate_email_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
