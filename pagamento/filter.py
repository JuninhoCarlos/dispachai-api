# filters.py
import django_filters
from django.utils import timezone
from django.db.models import Q, Prefetch, BooleanField, Case, When, Value

from .models import (
    Processo,
    Pagamento,
    PagamentoContrato,
    PagamentoParcela,
)


class ProcessoMonthYearFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter(method="filter_noop")
    month = django_filters.NumberFilter(method="filter_noop")

    class Meta:
        model = Processo
        fields = []

    def filter_noop(self, queryset, name, value):
        return queryset

    @property
    def qs(self):
        qs = super().qs
        now = timezone.now()

        year = int(self.data.get("year", now.year))
        month = int(self.data.get("month", now.month))

        pagamentos_qs = (
            Pagamento.objects.select_related(
                "implantacao",
                "contrato",
            )
            .filter(
                Q(
                    implantacao__data_vencimento__year=year,
                    implantacao__data_vencimento__month=month,
                )
                | Q(
                    contrato__vencimento_entrada__year=year,
                    contrato__vencimento_entrada__month=month,
                )
                | Q(
                    contrato__parcelas__data_vencimento__year=year,
                    contrato__parcelas__data_vencimento__month=month,
                )
            )
            .distinct()
        )

        qs = qs.filter(pagamentos__in=pagamentos_qs).distinct()

        parcelas_qs = PagamentoParcela.objects.filter(
            data_vencimento__year=year,
            data_vencimento__month=month,
        )

        contratos_qs = PagamentoContrato.objects.annotate(
            entrada_filter=Case(
                When(
                    vencimento_entrada__year=year,
                    vencimento_entrada__month=month,
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).prefetch_related(
            Prefetch(
                "parcelas",
                queryset=parcelas_qs,
                to_attr="parcelas_filtradas",
            )
        )

        return qs.prefetch_related(
            Prefetch(
                "pagamentos",
                queryset=pagamentos_qs,
            ),
            Prefetch(
                "pagamentos__contrato",
                queryset=contratos_qs,
                to_attr="contrato_annotado",
            ),
        )
