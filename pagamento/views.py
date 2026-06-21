from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.openapi import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from identity.permissions import IsSuperUser
from pagamento.filter import (
    PagamentoMonthYearFilter,
    RelatorioReceitaFilter,
    RelatorioRecolhimentoFilter,
)

from .models import (
    Pagamento,
    PagamentoContrato,
    PagamentoEvento,
    PagamentoImplantacao,
    Processo,
    StatusPagamento,
)
from .serializers.read import (
    PagamentoReaderSerializer,
    PendentesSerializer,
    ProcessoDetailSerializer,
    RelatorioReceitaSerializer,
    RelatorioRecolhimentoSerializer,
    RepasseReadSerializer,
)
from .serializers.write import (
    PagamentoContratoSerializer,
    PagamentoImplantacaoSerializer,
    PagarSerializer,
    ProcessoSerializer,
    RepasseInputSerializer,
)
from .services.pagamento_service import PagamentoService
from .services.relatorio_service import build_recolhimento, build_relatorio
from .services.repasse_service import RepasseService


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
        quitar = serializer.validated_data.get("quitar", False)

        PagamentoService.pagar(
            pagamento,
            valor_pago=valor_pago,
            data_pagamento=data_pagamento,
            quitar=quitar,
        )

        return Response({"status": "OK"})


class PagamentoListAPIView(ListAPIView):
    # the prefetch related is done in the filter to optimize the queries
    # Fetch only IMPLANTACAO and ENTRADA types
    queryset = (
        Pagamento.objects.select_related(
            "processo",
            "processo__advogado",
            "processo__corretor",
            "implantacao",
            "parcela__contrato",
        )
        .prefetch_related("repasses")
        .distinct()
    )

    serializer_class = PagamentoReaderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PagamentoMonthYearFilter


class ProcessoPendentesAPIView(GenericAPIView):
    permission_classes = [IsSuperUser]
    serializer_class = PendentesSerializer
    queryset = Pagamento.objects.none()

    @extend_schema(responses=PendentesSerializer(many=True))
    def get(self, request, processo_id):
        get_object_or_404(Processo, pk=processo_id)
        today = now().date()
        pending_filter = (
            Q(implantacao__status=StatusPagamento.PARCIALMENTE_PAGO)
            | Q(
                implantacao__status=StatusPagamento.PLANEJADO,
                implantacao__data_vencimento__lt=today,
            )
            | Q(parcela__status=StatusPagamento.PARCIALMENTE_PAGO)
            | Q(
                parcela__status=StatusPagamento.PLANEJADO,
                parcela__data_vencimento__lt=today,
            )
        )
        pagamentos = (
            Pagamento.objects.filter(processo_id=processo_id)
            .filter(pending_filter)
            .select_related("implantacao", "parcela")
            .order_by("id")
        )
        serializer = self.get_serializer(pagamentos, many=True)
        return Response(serializer.data)


class RepassarView(GenericAPIView):
    serializer_class = RepasseInputSerializer
    permission_classes = [IsSuperUser]
    queryset = Pagamento.objects.select_related(
        "processo__advogado",
        "processo__corretor",
        "implantacao",
        "parcela",
    )

    def post(self, request, pagamento_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pagamento = get_object_or_404(self.get_queryset(), id=pagamento_id)

        repasse = RepasseService.repassar(
            pagamento=pagamento,
            tipo=serializer.validated_data["tipo"],
            data_repasse=serializer.validated_data["data_repasse"],
        )

        return Response(
            RepasseReadSerializer(repasse).data, status=status.HTTP_201_CREATED
        )


class ReceitaRelatorioAPIView(GenericAPIView):
    permission_classes = [IsSuperUser]
    serializer_class = RelatorioReceitaSerializer

    @extend_schema(
        responses=RelatorioReceitaSerializer,
        parameters=[
            OpenApiParameter(
                name="data_inicio",
                type={"type": "string", "format": "date"},
                location=OpenApiParameter.QUERY,
                required=False,
                description="Start date (YYYY-MM-DD). Default: first day of month.",
            ),
            OpenApiParameter(
                name="data_fim",
                type={"type": "string", "format": "date"},
                location=OpenApiParameter.QUERY,
                required=False,
                description="End date (YYYY-MM-DD). Default: last day of month.",
            ),
            OpenApiParameter(
                name="advogado_id",
                type={"type": "integer"},
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter events by advogado ID.",
            ),
            OpenApiParameter(
                name="repasse_status",
                type={"type": "string"},
                location=OpenApiParameter.QUERY,
                required=False,
                description='Pass "ALL" to include payments with an existing repasse.',
            ),
        ],
    )
    def get(self, request):
        base_qs = PagamentoEvento.objects.select_related(
            "pagamento__processo__advogado",
            "pagamento__processo__corretor",
            "pagamento__processo__cliente",
            "pagamento__implantacao",
            "pagamento__parcela",
        )
        f = RelatorioReceitaFilter(request.GET, queryset=base_qs)
        relatorio = build_relatorio(f.qs, f.data_inicio_effective, f.data_fim_effective)
        serializer = RelatorioReceitaSerializer(relatorio)
        return Response(serializer.data)


class RecolhimentoRelatorioAPIView(GenericAPIView):
    permission_classes = [IsSuperUser]
    serializer_class = RelatorioRecolhimentoSerializer

    @extend_schema(
        responses=RelatorioRecolhimentoSerializer,
        parameters=[
            OpenApiParameter(
                name="advogado_id",
                type={"type": "integer"},
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by advogado ID.",
            ),
            OpenApiParameter(
                name="data_inicio",
                type={"type": "string", "format": "date"},
                location=OpenApiParameter.QUERY,
                required=False,
                description="Start of data_vencimento filter (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="data_fim",
                type={"type": "string", "format": "date"},
                location=OpenApiParameter.QUERY,
                required=False,
                description="End of data_vencimento filter (YYYY-MM-DD).",
            ),
        ],
    )
    def get(self, request):
        base_qs = Pagamento.objects.select_related(
            "processo__advogado",
            "processo__corretor",
            "processo__cliente",
            "implantacao",
            "parcela",
            "parcela__contrato",
        )
        f = RelatorioRecolhimentoFilter(request.GET, queryset=base_qs)
        relatorio = build_recolhimento(
            f.qs, f.data_inicio_effective, f.data_fim_effective
        )
        serializer = RelatorioRecolhimentoSerializer(relatorio)
        return Response(serializer.data)
