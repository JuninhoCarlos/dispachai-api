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
    repasse_status = serializers.CharField()
    data_vencimento = serializers.DateField()
    data_pagamento = serializers.DateField()
    numero_parcela = serializers.IntegerField(required=False)
    total_parcelas = serializers.IntegerField(required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "numero_parcela" not in instance:
            data.pop("numero_parcela", None)
        if "total_parcelas" not in instance:
            data.pop("total_parcelas", None)
        return data


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


class RecolhimentoPagamentoItemSerializer(serializers.Serializer):
    pagamento_id = serializers.IntegerField()
    cliente = serializers.CharField(allow_null=True)
    tipo = serializers.CharField()
    status = serializers.CharField()
    valor_pendente = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    comissao_advogado_porcentagem = serializers.DecimalField(
        max_digits=5, decimal_places=2, coerce_to_string=False
    )
    comissao_advogado_valor = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    valor_escritorio = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    corretor_nome = serializers.CharField(allow_null=True)
    comissao_corretor_porcentagem = serializers.DecimalField(
        max_digits=5, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    comissao_corretor_valor = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False, allow_null=True
    )
    data_vencimento = serializers.DateField()
    numero_parcela = serializers.IntegerField(required=False)
    total_parcelas = serializers.IntegerField(required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "numero_parcela" not in instance:
            data.pop("numero_parcela", None)
        if "total_parcelas" not in instance:
            data.pop("total_parcelas", None)
        return data


class RecolhimentoAdvogadoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    total_recolhimento = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    pagamentos = RecolhimentoPagamentoItemSerializer(many=True)


class RecolhimentoPeriodoSerializer(serializers.Serializer):
    inicio = serializers.DateField(allow_null=True)
    fim = serializers.DateField(allow_null=True)


class RelatorioRecolhimentoSerializer(serializers.Serializer):
    periodo = RecolhimentoPeriodoSerializer()
    advogados = RecolhimentoAdvogadoSerializer(many=True)
