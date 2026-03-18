from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from pagamento.models import (
    Pagamento,
    PagamentoContrato,
    PagamentoImplantacao,
    PagamentoParcela,
    Processo,
    StatusPagamento,
    TipoPagamento,
    TipoParcela,
)
from pessoa.models import Advogado, Cliente


def create_advogado(**kwargs):
    defaults = {
        "nome": "Advogado Teste",
        "oab_numero": "123456",
        "email": "advogado@example.com",
        "comissao_padrao": Decimal("30.00"),
    }
    defaults.update(kwargs)
    return Advogado.objects.create(**defaults)


def create_cliente(**kwargs):
    defaults = {"nome": "Cliente Teste", "cpf": "529.982.247-25"}
    defaults.update(kwargs)
    return Cliente.objects.create(**defaults)


def create_processo(advogado, cliente=None, **kwargs):
    return Processo.objects.create(advogado=advogado, cliente=cliente, **kwargs)


def create_implantacao(processo, **kwargs):
    pagamento = Pagamento.objects.create(
        processo=processo, tipo=TipoPagamento.IMPLANTACAO
    )
    defaults = {
        "valor_total": Decimal("1000.00"),
        "porcentagem_escritorio": Decimal("30.00"),
        "data_vencimento": date(2025, 6, 1),
        "status": StatusPagamento.PLANEJADO,
    }
    defaults.update(kwargs)
    implantacao = PagamentoImplantacao.objects.create(pagamento=pagamento, **defaults)
    return pagamento, implantacao


def create_parcela(processo, valor_parcela=Decimal("500.00"), **kwargs):
    contrato = PagamentoContrato.objects.create(
        entrada=Decimal("200.00"),
        valor_parcela=valor_parcela,
        numero_parcelas=1,
        vencimento_entrada=date(2025, 6, 1),
    )
    pagamento = Pagamento.objects.create(processo=processo, tipo=TipoPagamento.PARCELA)
    defaults = {
        "valor_parcela": valor_parcela,
        "data_vencimento": date(2025, 6, 1),
        "status": StatusPagamento.PLANEJADO,
        "tipo": TipoParcela.PARCELA,
        "numero_parcela": 1,
    }
    defaults.update(kwargs)
    parcela = PagamentoParcela.objects.create(
        pagamento=pagamento, contrato=contrato, **defaults
    )
    return pagamento, parcela


def create_full_fixture():
    """Returns a dict with advogado, cliente, processo, pagamento, implantacao."""
    advogado = create_advogado()
    cliente = create_cliente()
    processo = create_processo(advogado=advogado, cliente=cliente)
    pagamento, implantacao = create_implantacao(processo)
    return {
        "advogado": advogado,
        "cliente": cliente,
        "processo": processo,
        "pagamento": pagamento,
        "implantacao": implantacao,
    }


def create_superuser(**kwargs):
    defaults = {
        "username": "admin",
        "email": "admin@example.com",
        "password": "adminpass",
    }
    defaults.update(kwargs)
    return User.objects.create_superuser(**defaults)


def create_user(**kwargs):
    defaults = {
        "username": "user",
        "email": "user@example.com",
        "password": "userpass",
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)
