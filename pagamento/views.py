from rest_framework.generics import CreateAPIView, ListAPIView, GenericAPIView
from identity.permissions import IsSuperUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch

from pagamento.filter import ProcessoMonthYearFilter
from .services.pagamento_service import PagamentoService

from .models import (
    Pagamento,
    Processo,
    PagamentoImplantacao,
    PagamentoContrato,
    TipoPagamento,
)
from .serializers import (
    ProcessoSerializer,
    PagamentoImplantacaoSerializer,
    PagamentoContratoSerializer,
    PagarSerializer,
)

from .read.serializers import PagamentoReaderSerializer


class ProcessoListCreateAPIView(CreateAPIView):
    queryset = Processo.objects.all()
    serializer_class = ProcessoSerializer
    permission_classes = [IsSuperUser]


class ImplantacaoCreateAPIView(CreateAPIView):
    queryset = PagamentoImplantacao.objects.all()
    serializer_class = PagamentoImplantacaoSerializer
    permission_classes = [IsSuperUser]


class ContratoCreateAPIView(CreateAPIView):
    queryset = PagamentoContrato.objects.all()
    serializer_class = PagamentoContratoSerializer
    permission_classes = [IsSuperUser]


class PagarImplantacaoGenericView(GenericAPIView):
    serializer_class = PagarSerializer
    permission_classes = [IsSuperUser]

    def post(self, request, pk):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        implantacao = get_object_or_404(PagamentoImplantacao, pagamento_id=pk)

        valor_pago = serializer.validated_data["valor_pago"]
        data_pagamento = serializer.validated_data["data_pagamento"]

        PagamentoService.pagar_implantacao(
            implantacao, valor_pago=valor_pago, data_pagamento=data_pagamento
        )

        return Response({"status": "OK"})


class PagamentoListAPIView(ListAPIView):
    # the prefetch related is done in the filter to optimize the queries
    # Fetch only IMPLANTACAO and ENTRADA types
    queryset = (
        Pagamento.objects.filter(
            tipo__in=[TipoPagamento.IMPLANTACAO, TipoPagamento.ENTRADA]
        )
        .select_related(
            "processo",
            "processo__advogado",
            "processo__corretor",
            "implantacao",
            "parcelas_contrato__contrato",
        )
        .distinct()
    )

    serializer_class = PagamentoReaderSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = ProcessoMonthYearFilter
