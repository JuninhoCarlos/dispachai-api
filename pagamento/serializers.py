from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from rest_framework import serializers
from .models import (
    PagamentoImplantacao,
    PagamentoContrato,
    Processo,
    TipoPagamento,
    TipoParcela,
    PagamentoParcela,
    StatusPagamento,
    Pagamento,
)


class ProcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Processo
        fields = [
            "id",
            "cliente",
            "advogado",
            "corretor",
        ]


class PagamentoBaseSerializer(serializers.ModelSerializer):
    processo = serializers.PrimaryKeyRelatedField(
        queryset=Processo.objects.all(), write_only=True
    )

    tipo = None  # to be defined in subclasses

    class Meta:
        model = Pagamento
        fields = ["processo", "valor_total"]

    def create_pagamento(self, validated_data, tipo=None):
        processo = validated_data.pop("processo")

        return Pagamento.objects.create(
            processo=processo,
            tipo=tipo or self.tipo,
        )


class PagamentoContratoSerializer(PagamentoBaseSerializer):
    vencimento_parcela = serializers.DateField(
        write_only=True,
        required=True,
        help_text="Data de vencimento da primeira parcela.",
    )

    valor_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, write_only=True
    )

    class Meta:
        model = PagamentoContrato
        fields = [
            "processo",
            "valor_total",
            "entrada",
            "valor_parcela",
            "numero_parcelas",
            "vencimento_entrada",
            "vencimento_parcela",
        ]

    def validate(self, data):
        """
        Validações de alto nível envolvendo múltiplos campos.
        """

        # 1. Validar data do pagamento: deve ser uma data futura
        vencimento = data.get("vencimento_entrada")
        if vencimento and vencimento <= date.today():
            raise serializers.ValidationError(
                {"vencimento_entrada": "A data deve ser futura."}
            )

        # 2. Validar: entrada + valor_parcela * numero_parcelas == valor_total
        valor_total = data.get("valor_total")
        entrada = data.get("entrada")
        valor_parcela = data.get("valor_parcela")
        numero_parcelas = data.get("numero_parcelas")

        if all([valor_total, entrada, valor_parcela, numero_parcelas]):
            calculado = entrada + (valor_parcela * numero_parcelas)
            if calculado != valor_total:
                raise serializers.ValidationError(
                    {
                        "valor_total": (
                            "O valor_total deve ser igual a entrada + "
                            "valor_parcela * numero_parcelas."
                        )
                    }
                )

        return data

    def create(self, validated_data):
        vencimento_parcela = validated_data.get("vencimento_parcela")
        processo = validated_data.pop("processo")
        valor_total = validated_data.pop("valor_total")

        contrato = super().create(validated_data)

        self._create_entrada(contrato, processo)
        self._create_parcelas(contrato, processo, vencimento_parcela)

        return contrato

    def _create_entrada(self, contrato, processo):
        pagamento_entrada = Pagamento.objects.create(
            processo=processo, tipo=TipoPagamento.ENTRADA
        )

        PagamentoParcela.objects.create(
            pagamento=pagamento_entrada,
            contrato=contrato,
            valor_parcela=contrato.entrada,
            tipo=TipoParcela.ENTRADA,
            numero_parcela=None,
            data_vencimento=contrato.vencimento_entrada,
            status=StatusPagamento.PLANEJADO,
        )

    def _create_parcelas(self, contrato, processo, vencimento_parcela):
        parcelas = []

        for i in range(contrato.numero_parcelas):
            pagamento = Pagamento.objects.create(
                processo=processo, tipo=TipoPagamento.PARCELA
            )
            parcelas.append(
                PagamentoParcela(
                    pagamento=pagamento,
                    contrato=contrato,
                    valor_parcela=contrato.valor_parcela,
                    numero_parcela=i + 1,
                    data_vencimento=vencimento_parcela + relativedelta(months=i),
                    tipo=TipoParcela.PARCELA,
                    status=StatusPagamento.PLANEJADO,
                )
            )

        PagamentoParcela.objects.bulk_create(parcelas, batch_size=200)


class PagamentoImplantacaoSerializer(PagamentoBaseSerializer):
    tipo = TipoPagamento.IMPLANTACAO
    porcentagem_escritorio = serializers.DecimalField(max_digits=5, decimal_places=2)
    data_vencimento = serializers.DateField()

    class Meta:
        model = PagamentoImplantacao
        fields = [
            "processo",
            "valor_total",
            "porcentagem_escritorio",
            "data_vencimento",
        ]

    def validate(self, data):
        # validar valor_total > 0
        valor_total = data.get("valor_total")
        if valor_total is not None and valor_total <= 0:
            raise serializers.ValidationError(
                {"valor_total": "O valor total deve ser maior que zero."}
            )

        # validar porcentagem_escritorio entre 0 e 100
        porcentagem = data.get("porcentagem_escritorio")
        if porcentagem is not None and not (0 < porcentagem <= 100):
            raise serializers.ValidationError(
                {"porcentagem_escritorio": "A porcentagem deve estar entre 0 e 100."}
            )

        # validar data_vencimento no futuro
        vencimento = data.get("data_vencimento")
        if vencimento is not None and vencimento < date.today():
            raise serializers.ValidationError(
                {"data_vencimento": "A data de vencimento deve ser futura."}
            )

        return data

    def create(self, validated_data):

        pagamento = self.create_pagamento(validated_data)
        validated_data["pagamento"] = pagamento

        return super().create(validated_data)


class PagamentoImplantacaoReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoImplantacao
        fields = [
            "pagamento",
            "porcentagem_escritorio",
            "data_vencimento",
            "status",
        ]


class ParcelasSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoParcela
        fields = [
            "numero_parcela",
            "valor_parcela",
            "data_vencimento",
            "status",
            "valor_pago",
        ]


class EntradaSerializer(serializers.Serializer):
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)
    vencimento = serializers.DateField()
    status = serializers.ChoiceField(choices=StatusPagamento.choices)


class PagamentoContratoReaderSerializer(serializers.ModelSerializer):
    parcelas = ParcelasSerializer(
        source="parcelas_filtradas",
        many=True,
        read_only=True,
    )
    entrada = serializers.SerializerMethodField()

    class Meta:
        model = PagamentoContrato
        fields = [
            "pagamento",
            "valor_parcela",
            "numero_parcelas",
            "entrada",
            "parcelas",
        ]

    def get_entrada(self, obj):
        if not getattr(obj, "entrada_filter", False):
            return None

        return EntradaSerializer(
            {
                "valor": obj.entrada,
                "vencimento": obj.vencimento_entrada,
                "status": obj.status_entrada,
            }
        ).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.entrada_filter:
            data.pop("entrada", None)
        return data


class PagamentoSerializer(serializers.ModelSerializer):
    detalhe = serializers.SerializerMethodField()

    class Meta:
        model = Pagamento
        fields = [
            "valor_total",
            "criado_em",
            "tipo",
            "detalhe",
        ]

    def get_detalhe(self, obj):
        if obj.tipo == TipoPagamento.IMPLANTACAO:
            return PagamentoImplantacaoReaderSerializer(obj.detalhes).data

        if obj.tipo == TipoPagamento.CONTRATO:
            contrato = getattr(obj, "contrato_annotado", None) or obj.detalhes
            return PagamentoContratoReaderSerializer(contrato).data

        # fallback
        return None


class ProcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Processo
        fields = [
            "id",
            "cliente",
            "advogado",
            "corretor",
            "criado_em",
            "observacao",
        ]


class ProcessoReaderSerializer(serializers.ModelSerializer):
    id_processo = serializers.IntegerField(source="id", read_only=True)
    pagamentos = serializers.SerializerMethodField()
    advogado = serializers.CharField(source="advogado.nome", read_only=True)
    corretor = serializers.CharField(source="corretor.nome", read_only=True)

    class Meta:
        model = Processo
        fields = [
            "id_processo",
            "cliente",
            "advogado",
            "corretor",
            "pagamentos",
        ]

    def get_pagamentos(self, obj):
        pagamentos = obj.pagamentos.all()
        return PagamentoSerializer(pagamentos, many=True).data


class PagarSerializer(serializers.Serializer):
    valor_pago = serializers.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = serializers.DateField()

    def validate_valor_pago(self, value):
        if value <= 0:
            raise serializers.ValidationError("O valor pago deve ser maior que zero.")
        return value
