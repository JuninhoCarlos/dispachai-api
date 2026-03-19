from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from identity.permissions import IsSuperUser
from pagamento.filter import PagamentoMonthYearFilter

from .models import (
    Pagamento,
    PagamentoContrato,
    PagamentoImplantacao,
    PagamentoParcela,
    Processo,
    StatusPagamento,
)
from .serializers.read import (
    PagamentoReaderSerializer,
    PendentesImplantacaoSerializer,
    PendentesParcelaSerializer,
    ProcessoDetailSerializer,
)
from .serializers.write import (
    PagamentoContratoSerializer,
    PagamentoImplantacaoSerializer,
    PagarSerializer,
    ProcessoSerializer,
)
from .services.pagamento_service import PagamentoService


class ProcessoListCreateAPIView(ListCreateAPIView):
    queryset = Processo.objects.all()
    permission_classes = [IsSuperUser]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProcessoDetailSerializer
        elif self.request.method == "POST":
            return ProcessoSerializer

        return super().get_serializer_class()


class ProcessoDetailAPIView(GenericAPIView):
    queryset = Processo.objects.prefetch_related(
        Prefetch(
            "pagamentos",
            queryset=Pagamento.objects.select_related(
                "implantacao", "parcela"
            ).order_by("criado_em"),
        )
    )

    serializer_class = ProcessoDetailSerializer
    permission_classes = [IsSuperUser]

    def get(self, request, processo_id):
        processo = get_object_or_404(self.get_queryset(), id=processo_id)
        serializer = self.get_serializer(processo)
        return Response(serializer.data)


class ImplantacaoCreateAPIView(CreateAPIView):
    queryset = PagamentoImplantacao.objects.all()
    serializer_class = PagamentoImplantacaoSerializer
    permission_classes = [IsSuperUser]


class ContratoCreateAPIView(CreateAPIView):
    queryset = PagamentoContrato.objects.all()
    serializer_class = PagamentoContratoSerializer
    permission_classes = [IsSuperUser]


class PagarPagamentosGenericView(GenericAPIView):
    serializer_class = PagarSerializer
    permission_classes = [IsSuperUser]

    queryset = Pagamento.objects.select_related(
        "implantacao",  # Only include fields that are used
        "parcela__contrato",
    )

    def post(self, request, pagamento_id):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pagamento = get_object_or_404(self.get_queryset(), id=pagamento_id)

        valor_pago = serializer.validated_data["valor_pago"]
        data_pagamento = serializer.validated_data["data_pagamento"]

        PagamentoService.pagar(
            pagamento, valor_pago=valor_pago, data_pagamento=data_pagamento
        )

        return Response({"status": "OK"})


class PagamentoListAPIView(ListAPIView):
    # the prefetch related is done in the filter to optimize the queries
    # Fetch only IMPLANTACAO and ENTRADA types
    queryset = Pagamento.objects.select_related(
        "processo",
        "processo__advogado",
        "processo__corretor",
        "implantacao",
        "parcela__contrato",
    ).distinct()

    serializer_class = PagamentoReaderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PagamentoMonthYearFilter


class ProcessoPendentesAPIView(GenericAPIView):
    permission_classes = [IsSuperUser]

    def get(self, request, processo_id):
        get_object_or_404(Processo, pk=processo_id)
        today = now().date()
        pending_filter = Q(status=StatusPagamento.PARCIALMENTE_PAGO) | Q(
            status=StatusPagamento.PLANEJADO, data_vencimento__lt=today
        )
        implantacoes = (
            PagamentoImplantacao.objects.filter(pagamento__processo_id=processo_id)
            .filter(pending_filter)
            .select_related("pagamento")
        )
        parcelas = (
            PagamentoParcela.objects.filter(pagamento__processo_id=processo_id)
            .filter(pending_filter)
            .select_related("pagamento")
        )
        data = PendentesImplantacaoSerializer(implantacoes, many=True).data
        data += PendentesParcelaSerializer(parcelas, many=True).data
        return Response(data)
