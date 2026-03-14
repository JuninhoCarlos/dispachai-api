from rest_framework.generics import ListCreateAPIView, ListAPIView
from identity.permissions import IsSuperUser
from rest_framework.permissions import IsAuthenticated

from .models import Advogado, Corretor, Cliente
from .serializers import AdvogadoSerializer, CorretorSerializer, ClienteSerializer


class AdvogadoListCreateAPIView(ListCreateAPIView):
    queryset = Advogado.objects.all()
    serializer_class = AdvogadoSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            # Permissions for GET requests
            return [IsAuthenticated()]
        elif self.request.method == "POST":
            # Permissions for POST requests
            return [IsSuperUser()]
        return super().get_permissions()


class CorretorListCreateAPIView(ListCreateAPIView):
    queryset = Corretor.objects.all()
    serializer_class = CorretorSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            # Permissions for GET requests
            return [IsAuthenticated()]
        elif self.request.method == "POST":
            # Permissions for POST requests
            return [IsSuperUser()]
        return super().get_permissions()


class ClienteListAPIView(ListAPIView):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

    def get_permissions(self):
        # Permissions for GET requests
        return [IsAuthenticated()]
