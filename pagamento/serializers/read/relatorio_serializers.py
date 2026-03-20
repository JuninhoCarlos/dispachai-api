from rest_framework import serializers


class RelatorioPagamentoItemSerializer(serializers.Serializer):
    pagamento_id = serializers.IntegerField()
    tipo = serializers.CharField()
    receita = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    comissao_porcentagem = serializers.DecimalField(
        max_digits=5, decimal_places=2, coerce_to_string=False
    )
    comissao_valor = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )


class RelatorioProcessoItemSerializer(serializers.Serializer):
    processo_id = serializers.IntegerField()
    cliente = serializers.CharField(allow_null=True)
    pagamentos = RelatorioPagamentoItemSerializer(many=True)


class RelatorioAdvogadoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    total_comissao = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    processos = RelatorioProcessoItemSerializer(many=True)


class RelatorioCorretorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    total_comissao = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    processos = RelatorioProcessoItemSerializer(many=True)


class RelatorioEscritorioSerializer(serializers.Serializer):
    total_comissao = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )


class RelatorioPeriodoSerializer(serializers.Serializer):
    inicio = serializers.DateField()
    fim = serializers.DateField()


class RelatorioReceitaSerializer(serializers.Serializer):
    periodo = RelatorioPeriodoSerializer()
    total_receita = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    escritorio = RelatorioEscritorioSerializer()
    advogados = RelatorioAdvogadoSerializer(many=True)
    corretores = RelatorioCorretorSerializer(many=True)
