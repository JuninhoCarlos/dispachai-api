from rest_framework import serializers

from ...models import Repasse


class RepasseReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repasse
        fields = [
            "id",
            "pagamento",
            "tipo",
            "advogado",
            "corretor",
            "valor_repassado",
            "valor_total",
            "comissao_porcentagem",
            "data_repasse",
            "criado_em",
        ]
