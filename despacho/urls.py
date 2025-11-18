from django.urls import path, include

from .views import AdvogadoListCreateAPIView

urlpatterns = [
    path(
        "despacho/advogado",
        AdvogadoListCreateAPIView.as_view(),
        name="advogado_list_create",
    ),
]
