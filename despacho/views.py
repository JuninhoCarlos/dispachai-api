from rest_framework.generics import ListCreateAPIView
from identity.permissions import IsSuperUser
from rest_framework.permissions import IsAuthenticated

from .models import Advogado, Corretor
from .serializers import AdvogadoSerializer, CorretorSerializer


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
