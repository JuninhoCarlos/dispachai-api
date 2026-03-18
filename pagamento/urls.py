from django.urls import path

from .views import (
    ContratoCreateAPIView,
    ImplantacaoCreateAPIView,
    PagamentoListAPIView,
    PagarPagamentosGenericView,
    ProcessoDetailAPIView,
    ProcessoListCreateAPIView,
)

urlpatterns = [
    path(
        "pagamento/processo",
        ProcessoListCreateAPIView.as_view(),
        name="processo_list_create",
    ),
    path(
        "pagamento/processo/<int:processo_id>",
        ProcessoDetailAPIView.as_view(),
        name="processo_detail",
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
        "pagamento/<int:pagamento_id>/pagar",
        PagarPagamentosGenericView.as_view(),
        name="pagamento_pagar",
    ),
    path("pagamento", PagamentoListAPIView.as_view(), name="pagamento_list"),
]
