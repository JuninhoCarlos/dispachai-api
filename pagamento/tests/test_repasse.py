from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pagamento.models import PagamentoEvento, Repasse, TipoRepasse
from pagamento.services.repasse_service import RepasseService
from pagamento.tests import (
    create_advogado,
    create_implantacao,
    create_parcela,
    create_processo,
    create_superuser,
    create_user,
)
from pessoa.models import Corretor


def create_corretor(advogado, **kwargs):
    defaults = {
        "nome": "Corretor Teste",
        "email": "corretor@example.com",
        "comissao_padrao": Decimal("20.00"),
    }
    defaults.update(kwargs)
    return Corretor.objects.create(advogado=advogado, **defaults)


def create_evento(pagamento, valor_recebido, data_pagamento):
    return PagamentoEvento.objects.create(
        pagamento=pagamento,
        valor_recebido=valor_recebido,
        data_pagamento=data_pagamento,
    )


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class RepasseModelTestCase(TestCase):
    def setUp(self):
        self.advogado = create_advogado()
        self.processo = create_processo(advogado=self.advogado)
        self.pagamento, _ = create_implantacao(self.processo)
        self.evento = create_evento(
            self.pagamento, Decimal("500.00"), date(2026, 4, 10)
        )

    def test_tipo_repasse_choices_exist(self):
        self.assertEqual(TipoRepasse.ADVOGADO, "ADVOGADO")
        self.assertEqual(TipoRepasse.CORRETOR, "CORRETOR")

    def test_repasse_can_be_created_and_linked_to_pagamento(self):
        repasse = Repasse.objects.create(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            advogado=self.advogado,
            valor_repassado=Decimal("45.00"),
            valor_total=Decimal("500.00"),
            comissao_porcentagem=Decimal("30.00"),
            data_repasse=date(2026, 4, 13),
        )
        repasse.eventos.add(self.evento)

        self.assertEqual(Repasse.objects.count(), 1)
        self.assertEqual(repasse.pagamento, self.pagamento)
        self.assertEqual(repasse.tipo, TipoRepasse.ADVOGADO)
        self.assertIn(self.evento, repasse.eventos.all())

    def test_repasse_accessible_via_pagamento_related_manager(self):
        repasse = Repasse.objects.create(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            advogado=self.advogado,
            valor_repassado=Decimal("45.00"),
            valor_total=Decimal("500.00"),
            comissao_porcentagem=Decimal("30.00"),
            data_repasse=date(2026, 4, 13),
        )
        self.assertIn(repasse, self.pagamento.repasses.all())


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RepasseServiceTestCase(TestCase):
    def setUp(self):
        # create_advogado default: comissao_padrao=30.00
        # create_implantacao default: valor_beneficio=1000.00, pct_escritorio=30.00
        self.advogado = create_advogado()
        self.processo = create_processo(advogado=self.advogado)
        self.pagamento, _ = create_implantacao(self.processo)
        # event records the office amount directly (escritorio_base)
        self.evento_abril = create_evento(
            self.pagamento, Decimal("150.00"), date(2026, 4, 10)
        )

    def test_repassar_advogado_implantacao_sem_corretor(self):
        # escritorio_base = event = 150
        # advogado_valor  = 150 × 30% = 45
        repasse = RepasseService.repassar(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            data_repasse=date(2026, 4, 13),
        )

        self.assertEqual(Repasse.objects.count(), 1)
        self.assertEqual(repasse.tipo, TipoRepasse.ADVOGADO)
        self.assertEqual(repasse.advogado, self.advogado)
        self.assertIsNone(repasse.corretor)
        self.assertEqual(repasse.valor_repassado, Decimal("45.00"))
        self.assertEqual(repasse.valor_total, Decimal("150.00"))
        self.assertEqual(repasse.comissao_porcentagem, Decimal("30.00"))
        self.assertIn(self.evento_abril, repasse.eventos.all())

    def test_repassar_advogado_implantacao_com_corretor(self):
        corretor = create_corretor(self.advogado)  # comissao_padrao=20.00
        self.processo.corretor = corretor
        self.processo.save()
        # escritorio_base = event = 150
        # corretor_valor  = 150 × 20% = 30
        # restante        = 120
        # advogado_valor  = 120 × 30% = 36
        repasse = RepasseService.repassar(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            data_repasse=date(2026, 4, 13),
        )

        self.assertEqual(repasse.valor_repassado, Decimal("36.00"))
        self.assertEqual(repasse.comissao_porcentagem, Decimal("30.00"))

    def test_repassar_corretor_implantacao(self):
        corretor = create_corretor(self.advogado)  # comissao_padrao=20.00
        self.processo.corretor = corretor
        self.processo.save()
        # escritorio_base = event = 150
        # corretor_valor  = 150 × 20% = 30
        repasse = RepasseService.repassar(
            pagamento=self.pagamento,
            tipo=TipoRepasse.CORRETOR,
            data_repasse=date(2026, 4, 13),
        )

        self.assertEqual(repasse.tipo, TipoRepasse.CORRETOR)
        self.assertEqual(repasse.corretor, corretor)
        self.assertIsNone(repasse.advogado)
        self.assertEqual(repasse.valor_repassado, Decimal("30.00"))
        self.assertEqual(repasse.valor_total, Decimal("150.00"))
        self.assertEqual(repasse.comissao_porcentagem, Decimal("20.00"))
        self.assertIn(self.evento_abril, repasse.eventos.all())

    def test_repassar_advogado_parcela_sem_corretor(self):
        pagamento_parcela, _ = create_parcela(self.processo)  # valor_parcela=500.00
        create_evento(pagamento_parcela, Decimal("500.00"), date(2026, 4, 5))
        # contrato: corretor_valor = 0; restante = 500; advogado_valor = 500 × 30% = 150
        repasse = RepasseService.repassar(
            pagamento=pagamento_parcela,
            tipo=TipoRepasse.ADVOGADO,
            data_repasse=date(2026, 4, 13),
        )

        self.assertEqual(repasse.valor_repassado, Decimal("150.00"))
        self.assertEqual(repasse.valor_total, Decimal("500.00"))

    def test_repassar_agrega_multiplos_eventos_no_mes(self):
        create_evento(self.pagamento, Decimal("60.00"), date(2026, 4, 20))
        # Total April: 150 + 60 = 210 (office amounts)
        # escritorio_base = 210; advogado_valor = 210 × 30% = 63
        repasse = RepasseService.repassar(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            data_repasse=date(2026, 4, 13),
        )

        self.assertEqual(repasse.valor_total, Decimal("210.00"))
        self.assertEqual(repasse.valor_repassado, Decimal("63.00"))
        self.assertEqual(repasse.eventos.count(), 2)

    def test_repassar_ignora_eventos_de_outros_meses(self):
        create_evento(self.pagamento, Decimal("300.00"), date(2026, 3, 15))
        # Only April's 150.00 is included; March's 300.00 is ignored
        repasse = RepasseService.repassar(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            data_repasse=date(2026, 4, 13),
        )

        self.assertEqual(repasse.valor_total, Decimal("150.00"))
        self.assertEqual(repasse.eventos.count(), 1)

    def test_repassar_sem_eventos_no_mes_raises_error(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            RepasseService.repassar(
                pagamento=self.pagamento,
                tipo=TipoRepasse.ADVOGADO,
                data_repasse=date(2026, 3, 1),  # March — no eventos
            )
        self.assertIn("data_repasse", ctx.exception.detail)

    def test_repassar_corretor_sem_corretor_no_processo_raises_error(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            RepasseService.repassar(
                pagamento=self.pagamento,
                tipo=TipoRepasse.CORRETOR,
                data_repasse=date(2026, 4, 13),
            )
        self.assertIn("tipo", ctx.exception.detail)

    def test_repassar_duplicado_mesmo_mes_raises_error(self):
        from rest_framework.exceptions import ValidationError

        RepasseService.repassar(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            data_repasse=date(2026, 4, 13),
        )
        with self.assertRaises(ValidationError) as ctx:
            RepasseService.repassar(
                pagamento=self.pagamento,
                tipo=TipoRepasse.ADVOGADO,
                data_repasse=date(2026, 4, 20),  # same month, different day
            )
        self.assertIn("non_field_errors", ctx.exception.detail)

    def test_repassar_com_comissao_ajustada_advogado(self):
        self.processo.comissao_ajustada_advogado = Decimal("50.00")
        self.processo.save()
        # escritorio_base = event = 150; advogado_valor = 150 × 50% = 75
        repasse = RepasseService.repassar(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            data_repasse=date(2026, 4, 13),
        )

        self.assertEqual(repasse.valor_repassado, Decimal("75.00"))
        self.assertEqual(repasse.comissao_porcentagem, Decimal("50.00"))


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


class RepassarAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = create_superuser()
        self.user = create_user()
        self.advogado = create_advogado()
        self.processo = create_processo(advogado=self.advogado)
        self.pagamento, _ = create_implantacao(self.processo)
        self.url = reverse(
            "pagamento_repassar", kwargs={"pagamento_id": self.pagamento.id}
        )
        # event records the office amount directly (escritorio_base)
        create_evento(self.pagamento, Decimal("150.00"), date(2026, 4, 10))

    def test_repassar_requires_authentication(self):
        response = self.client.post(
            self.url,
            {"tipo": "ADVOGADO", "data_repasse": "2026-04-13"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_repassar_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"tipo": "ADVOGADO", "data_repasse": "2026-04-13"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_repassar_advogado_happy_path(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url,
            {"tipo": "ADVOGADO", "data_repasse": "2026-04-13"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Repasse.objects.count(), 1)
        repasse = Repasse.objects.first()
        self.assertEqual(repasse.tipo, TipoRepasse.ADVOGADO)
        self.assertEqual(repasse.valor_repassado, Decimal("45.00"))
        self.assertEqual(response.data["tipo"], "ADVOGADO")
        self.assertEqual(Decimal(response.data["valor_repassado"]), Decimal("45.00"))

    def test_repassar_corretor_happy_path(self):
        corretor = create_corretor(self.advogado)
        self.processo.corretor = corretor
        self.processo.save()
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url,
            {"tipo": "CORRETOR", "data_repasse": "2026-04-13"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Repasse.objects.count(), 1)
        repasse = Repasse.objects.first()
        self.assertEqual(repasse.tipo, TipoRepasse.CORRETOR)
        # escritorio_base = event = 150; corretor_valor = 150 × 20% = 30
        self.assertEqual(repasse.valor_repassado, Decimal("30.00"))

    def test_repassar_missing_tipo(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url,
            {"data_repasse": "2026-04-13"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tipo", response.data)

    def test_repassar_missing_data_repasse(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url,
            {"tipo": "ADVOGADO"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("data_repasse", response.data)

    def test_repassar_no_eventos_in_month(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url,
            {"tipo": "ADVOGADO", "data_repasse": "2026-03-01"},  # March — no eventos
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_repassar_corretor_sem_corretor_no_processo(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url,
            {"tipo": "CORRETOR", "data_repasse": "2026-04-13"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_repassar_duplicado_mesmo_mes(self):
        self.client.force_authenticate(user=self.superuser)
        self.client.post(
            self.url,
            {"tipo": "ADVOGADO", "data_repasse": "2026-04-01"},
            format="json",
        )
        response = self.client.post(
            self.url,
            {"tipo": "ADVOGADO", "data_repasse": "2026-04-13"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Repasse.objects.count(), 1)

    def test_repassar_pagamento_not_found(self):
        self.client.force_authenticate(user=self.superuser)
        url = reverse("pagamento_repassar", kwargs={"pagamento_id": 9999})
        response = self.client.post(
            url,
            {"tipo": "ADVOGADO", "data_repasse": "2026-04-13"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Read serializer — repasse status fields
# ---------------------------------------------------------------------------


class RepasseStatusReadTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = create_superuser()
        self.advogado = create_advogado()
        self.processo = create_processo(advogado=self.advogado)
        self.pagamento, _ = create_implantacao(self.processo)
        self.url = reverse("pagamento_list")
        self.client.force_authenticate(user=self.superuser)

    def test_list_pagamento_includes_repasse_status_fields(self):
        response = self.client.get(self.url, {"year": 2025, "month": 6})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        pagamento_data = response.data["results"][0]
        self.assertIn("status_repasse_advogado", pagamento_data)
        self.assertIn("status_repasse_corretor", pagamento_data)

    def test_repasse_status_advogado_pendente_when_no_repasses(self):
        response = self.client.get(self.url, {"year": 2025, "month": 6})
        self.assertEqual(
            response.data["results"][0]["status_repasse_advogado"], "PENDENTE"
        )

    def test_repasse_status_advogado_repassado_when_repasse_exists(self):
        Repasse.objects.create(
            pagamento=self.pagamento,
            tipo=TipoRepasse.ADVOGADO,
            advogado=self.advogado,
            valor_repassado=Decimal("45.00"),
            valor_total=Decimal("500.00"),
            comissao_porcentagem=Decimal("30.00"),
            data_repasse=date(2026, 4, 13),
        )
        response = self.client.get(self.url, {"year": 2025, "month": 6})
        self.assertEqual(
            response.data["results"][0]["status_repasse_advogado"], "REPASSADO"
        )

    def test_repasse_status_corretor_na_when_processo_has_no_corretor(self):
        response = self.client.get(self.url, {"year": 2025, "month": 6})
        self.assertEqual(response.data["results"][0]["status_repasse_corretor"], "N/A")

    def test_repasse_status_corretor_pendente_when_corretor_exists_but_no_repasse(self):
        corretor = create_corretor(self.advogado)
        self.processo.corretor = corretor
        self.processo.save()
        response = self.client.get(self.url, {"year": 2025, "month": 6})
        self.assertEqual(
            response.data["results"][0]["status_repasse_corretor"], "PENDENTE"
        )

    def test_repasse_status_corretor_repassado_when_repasse_exists(self):
        corretor = create_corretor(self.advogado)
        self.processo.corretor = corretor
        self.processo.save()
        Repasse.objects.create(
            pagamento=self.pagamento,
            tipo=TipoRepasse.CORRETOR,
            corretor=corretor,
            valor_repassado=Decimal("30.00"),
            valor_total=Decimal("500.00"),
            comissao_porcentagem=Decimal("20.00"),
            data_repasse=date(2026, 4, 13),
        )
        response = self.client.get(self.url, {"year": 2025, "month": 6})
        self.assertEqual(
            response.data["results"][0]["status_repasse_corretor"], "REPASSADO"
        )
