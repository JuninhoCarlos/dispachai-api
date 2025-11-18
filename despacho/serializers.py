from rest_framework import serializers
from .models import Advogado


class AdvogadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advogado
        fields = ["id", "nome", "oab_numero", "email", "telefone", "comissao_padrao"]
