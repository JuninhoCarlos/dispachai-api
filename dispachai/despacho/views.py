from .models import Partner
from .serializers import PartnerSerializer
from rest_framework import viewsets

class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer