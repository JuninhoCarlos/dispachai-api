from django.db import models


class Advogado(models.Model):
    nome = models.CharField(max_length=100)
    oab_numero = models.CharField(max_length=20, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    comissao_padrao = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome}"


class Corretor(models.Model):
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    advogado = models.ForeignKey(
        Advogado, on_delete=models.CASCADE, related_name="corretores"
    )
    comissao_padrao = models.DecimalField(max_digits=5, decimal_places=2, default=9.00)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} (Advogado: {self.advogado.nome})"


class Processo(models.Model):
    nome_processo = models.TextField(blank=True, null=True)
    advogado = models.ForeignKey(
        Advogado, on_delete=models.CASCADE, related_name="processos"
    )
    corretor = models.ForeignKey(
        Corretor,
        on_delete=models.CASCADE,
        related_name="processos",
        null=True,
        blank=True,
    )

    comissao_ajustada_advogado = models.DecimalField(
        max_digits=3, decimal_places=2, blank=True, null=True
    )
    comissao_ajustada_corretor = models.DecimalField(
        max_digits=3, decimal_places=2, blank=True, null=True
    )

    valor_total = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Processo {self.nome_processo} - Advogado: {self.advogado.nome}"
