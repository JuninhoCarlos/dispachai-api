from django.urls import path, include

from .views import ProcessoListCreateAPIView, ImplantacaoCreateAPIView

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
]
