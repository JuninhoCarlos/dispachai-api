from rest_framework.generics import ListCreateAPIView
from identity.permissions import IsSuperUser
from rest_framework.permissions import IsAuthenticated

from .models import Advogado
from .serializers import AdvogadoSerializer


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
