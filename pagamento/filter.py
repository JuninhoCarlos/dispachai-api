# filters.py
import django_filters
from django.utils import timezone
from django.db.models import Q, Prefetch
from .models import PagamentoParcela, Processo


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

        qs = qs.filter(
            Q(
                pagamentos__implantacao__data_vencimento__year=year,
                pagamentos__implantacao__data_vencimento__month=month,
            )
            | Q(
                pagamentos__contrato__vencimento_entrada__year=year,
                pagamentos__contrato__vencimento_entrada__month=month,
            )
            | Q(
                pagamentos__contrato__parcelas__data_vencimento__year=year,
                pagamentos__contrato__parcelas__data_vencimento__month=month,
            )
        ).distinct()

        return qs.prefetch_related(
            Prefetch(
                "pagamentos__contrato__parcelas",
                queryset=PagamentoParcela.objects.filter(
                    data_vencimento__year=year,
                    data_vencimento__month=month,
                ),
                to_attr="parcelas_filtradas",
            )
        )
