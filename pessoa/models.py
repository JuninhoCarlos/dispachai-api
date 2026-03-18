from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Advogado(models.Model):
    nome = models.CharField(max_length=100)
    oab_numero = models.CharField(max_length=20, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    comissao_padrao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        validators=[
            MinValueValidator(Decimal(0.01)),
            MaxValueValidator(Decimal(100.00)),
        ],
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    chave_pix = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.nome}"


class Corretor(models.Model):
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    advogado = models.ForeignKey(
        Advogado, on_delete=models.CASCADE, related_name="corretores"
    )
    comissao_padrao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        validators=[
            MinValueValidator(Decimal(0.01)),
            MaxValueValidator(Decimal(100.00)),
        ],
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    chave_pix = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.nome} (Advogado: {self.advogado.nome})"


class Cliente(models.Model):
    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome
