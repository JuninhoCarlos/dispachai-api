from rest_framework import serializers
from .models import Advogado, Corretor


class AdvogadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advogado
        fields = ["id", "nome", "oab_numero", "email", "telefone", "comissao_padrao"]


class CorretorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Corretor
        fields = ["id", "nome", "email", "advogado", "comissao_padrao"]
