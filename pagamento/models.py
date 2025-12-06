from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from pessoa.models import Advogado, Corretor


class TipoPagamento(models.TextChoices):
    IMPLANTACAO = ("IMPLANTACAO",)
    CONTRATO = ("CONTRATO",)
    PARCELA = ("PARCELA",)
    RPV = ("RPV",)
    AUXILIODOENCA = ("AUXILIODOENCA",)


class StatusPagamento(models.TextChoices):
    PLANEJADO = "PLANEJADO", "Planejado"
    PAGO = "PAGO", "Pago"
    PARCIALMENTE_PAGO = "PARCIALMENTE_PAGO", "Parcialmente Pago"
    ATRASADO = "ATRASADO", "Atrasado"


class Pagamento(models.Model):
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)
    processo = models.ForeignKey(
        "Processo", on_delete=models.DO_NOTHING, related_name="pagamentos"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoPagamento.choices,
        null=False,
        blank=False,
    )

    def cast(self):
        """
        Returns the correct subclass instance.
        """
        if hasattr(self, "pagamentoimplantacao"):
            return self.pagamentoimplantacao
        if hasattr(self, "pagamentocontrato"):
            return self.pagamentocontrato
        if hasattr(self, "pagamentoparcela"):
            return self.pagamentoparcela
        # if hasattr(self, "pagamentoauxiliodoenca"):
        #     return self.pagamentoauxiliodoenca
        return self

    class Meta:
        abstract = False


class PagamentoImplantacao(Pagamento):
    porcentagem_escritorio = models.DecimalField(max_digits=5, decimal_places=2)
    data_vencimento = models.DateField(blank=False, null=False)

    status = models.CharField(
        max_length=20,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PLANEJADO,
    )

    class Meta:
        verbose_name = "Pagamento de Implantação"


class PagamentoContrato(Pagamento):
    entrada = models.DecimalField(max_digits=10, decimal_places=2)
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2)
    numero_parcelas = models.PositiveIntegerField()
    vencimento_entrada = models.DateField(blank=False, null=False)
    status_entrada = models.CharField(
        max_length=20,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PLANEJADO,
    )

    class Meta:
        verbose_name = "Pagamento de Contrato"


class PagamentoParcela(Pagamento):
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2)
    numero_parcela = models.PositiveIntegerField()
    data_vencimento = models.DateField(blank=False, null=False)
    status = models.CharField(
        max_length=20,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PLANEJADO,
    )
    valor_pago = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    contrato = models.ForeignKey(
        PagamentoContrato,
        on_delete=models.CASCADE,
        related_name="parcelas",
        null=False,
        blank=False,
    )

    class Meta:
        verbose_name = "Pagamento de Parcelas"


# class PagamentoAuxilioDoenca(Pagamento):
#     valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
#     ativo = models.BooleanField(default=True)

#     class Meta:
#         verbose_name = "Pagamento Auxílio Doença"


class Processo(models.Model):
    cliente = models.TextField(blank=True, null=True)
    advogado = models.ForeignKey(
        Advogado,
        on_delete=models.CASCADE,
        related_name="processos",
        null=False,
        blank=False,
    )
    corretor = models.ForeignKey(
        Corretor,
        on_delete=models.CASCADE,
        related_name="processos",
        null=True,
        blank=True,
    )

    comissao_ajustada_advogado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal(0.01)),
            MaxValueValidator(Decimal(100.00)),
        ],
    )
    comissao_ajustada_corretor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal(0.01)),
            MaxValueValidator(Decimal(100.00)),
        ],
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Processo {self.nome_processo} - Advogado: {self.advogado.nome}"
