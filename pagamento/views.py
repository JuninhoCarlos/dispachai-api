from rest_framework.generics import ListCreateAPIView
from identity.permissions import IsSuperUser
from rest_framework.permissions import IsAuthenticated

from .models import Processo, PagamentoImplantacao
from .serializers import ProcessoSerializer, PagamentoImplantacaoSerializer


class ProcessoListCreateAPIView(ListCreateAPIView):
    queryset = Processo.objects.all()
    serializer_class = ProcessoSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            # Permissions for GET requests
            return [IsAuthenticated()]
        elif self.request.method == "POST":
            # Permissions for POST requests
            return [IsSuperUser()]
        return super().get_permissions()


class ImplantacaoCreateAPIView(ListCreateAPIView):
    queryset = PagamentoImplantacao.objects.all()
    serializer_class = PagamentoImplantacaoSerializer
    permission_classes = IsSuperUser

    def get_permissions(self):
        if self.request.method == "GET":
            # Permissions for GET requests
            return [IsAuthenticated()]
        elif self.request.method == "POST":
            # Permissions for POST requests
            return [IsSuperUser()]
        return super().get_permissions()
