from django.urls import path, include

from .views import (
    PagamentoListAPIView,
    ProcessoListCreateAPIView,
    ImplantacaoCreateAPIView,
    PagarImplantacaoGenericView,
    ContratoCreateAPIView,
)

urlpatterns = [
    path(
        "pagamento/processo",
        ProcessoListCreateAPIView.as_view(),
        name="processo_list_create",
    ),
    path(
        "pagamento/implantacao",
        ImplantacaoCreateAPIView.as_view(),
        name="implantacao_create",
    ),
    path(
        "pagamento/contrato",
        ContratoCreateAPIView.as_view(),
        name="contrato_create",
    ),
    path(
        "pagamento/implantacao/<int:pk>/pagar",
        PagarImplantacaoGenericView.as_view(),
        name="implantacao_pagar",
    ),
    path("pagamento", PagamentoListAPIView.as_view(), name="pagamento_list"),
]
