from rest_framework.generics import ListCreateAPIView, CreateAPIView, ListAPIView
from identity.permissions import IsSuperUser
from rest_framework.permissions import IsAuthenticated

from .models import Processo, PagamentoImplantacao, PagamentoContrato
from .serializers import (
    ProcessoSerializer,
    ProcessoSerializer,
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
    queryset = Processo.objects.select_related("advogado", "corretor").prefetch_related(
        "pagamentos__pagamentoimplantacao",
        "pagamentos__pagamentocontrato",
    )
    serializer_class = ProcessoSerializer
    permission_classes = [IsAuthenticated]
