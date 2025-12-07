from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from pessoa.models import Advogado, Corretor


class TipoPagamento(models.TextChoices):
    IMPLANTACAO = ("IMPLANTACAO",)
    CONTRATO = ("CONTRATO",)
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
        "Processo", on_delete=models.CASCADE, related_name="pagamentos"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoPagamento.choices,
        null=False,
        blank=False,
    )

    @property
    def detalhes(self):
        if self.tipo == TipoPagamento.IMPLANTACAO:
            return self.implantacao
        if self.tipo == TipoPagamento.CONTRATO:
            return self.contrato
        # if hasattr(self, "pagamentoauxiliodoenca"):
        #     return self.pagamentoauxiliodoenca
        return self

    def __call__(self, *args, **kwds):
        return f"Pagamento {self.id} - Tipo: {self.tipo}"


class PagamentoImplantacao(models.Model):
    pagamento = models.OneToOneField(
        Pagamento,
        on_delete=models.CASCADE,
        related_name="implantacao",
        primary_key=True,
    )
    porcentagem_escritorio = models.DecimalField(max_digits=5, decimal_places=2)
    data_vencimento = models.DateField(blank=False, null=False)

    status = models.CharField(
        max_length=20,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PLANEJADO,
    )

    class Meta:
        verbose_name = "Pagamento de Implantação"


class PagamentoContrato(models.Model):
    pagamento = models.OneToOneField(
        Pagamento,
        on_delete=models.CASCADE,
        related_name="contrato",
        primary_key=True,
    )
    entrada = models.DecimalField(max_digits=10, decimal_places=2)
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2)
    numero_parcelas = models.PositiveIntegerField()
    vencimento_entrada = models.DateField(blank=False, null=False)
    vencimento_parcela = models.DateField(blank=True, null=True)

    status_entrada = models.CharField(
        max_length=20,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PLANEJADO,
    )

    class Meta:
        verbose_name = "Pagamento de Contrato"


class PagamentoParcela(models.Model):
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
