from django.urls import path, include

from .views import (
    AdvogadoListCreateAPIView,
    CorretorListCreateAPIView,
    ClienteListAPIView,
)

urlpatterns = [
    path(
        "pessoas/advogado",
        AdvogadoListCreateAPIView.as_view(),
        name="advogado_list_create",
    ),
    path(
        "pessoas/corretor",
        CorretorListCreateAPIView.as_view(),
        name="corretor_list_create",
    ),
    path("pessoas/cliente", ClienteListAPIView.as_view(), name="cliente_list"),
]
