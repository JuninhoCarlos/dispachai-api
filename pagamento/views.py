from django.db import models
from rest_framework.generics import CreateAPIView, ListAPIView
from identity.permissions import IsSuperUser
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from pagamento.filter import ProcessoMonthYearFilter

from .models import Pagamento, Processo, PagamentoImplantacao, PagamentoContrato
from .serializers import (
    ProcessoSerializer,
    ProcessoReaderSerializer,
    PagamentoImplantacaoSerializer,
    PagamentoContratoSerializer,
)


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


class PagamentoListAPIView(ListAPIView):
    # the prefetch related is done in the filter to optimize the queries
    queryset = Processo.objects.select_related("advogado", "corretor")

    serializer_class = ProcessoReaderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProcessoMonthYearFilter
