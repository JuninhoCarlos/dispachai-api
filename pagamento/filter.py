import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import (
    Pagamento,
    TipoPagamento,
)


class PagamentoMonthYearFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter(method="filter_noop")
    month = django_filters.NumberFilter(method="filter_noop")

    class Meta:
        model = Pagamento
        fields = ["year", "month"]

    def filter_noop(self, queryset, name, value):
        return queryset

    @property
    def qs(self):
        qs = super().qs
        now = timezone.now()

        # Get year and month from filter data, defaulting to current
        year = int(self.data.get("year", now.year))
        month = int(self.data.get("month", now.month))

        # Filter pagamentos by their respective types and date fields
        pagamentos_qs = qs.filter(
            Q(
                tipo=TipoPagamento.IMPLANTACAO,
                implantacao__data_vencimento__year=year,
                implantacao__data_vencimento__month=month,
            )
            | Q(
                tipo=TipoPagamento.ENTRADA,
                parcela__data_vencimento__year=year,
                parcela__data_vencimento__month=month,
            )
            | Q(
                tipo=TipoPagamento.PARCELA,
                parcela__data_vencimento__year=year,
                parcela__data_vencimento__month=month,
            )
        ).distinct()

        # Prefetch related data for optimized queries
        return pagamentos_qs.select_related(
            "implantacao",
            "parcela__contrato",
        )
