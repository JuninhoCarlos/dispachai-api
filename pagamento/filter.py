import django_filters
from django.utils import timezone
from django.db.models import Q

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

        # Get the year and month from the filter data or default to the current year/month
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
                parcelas_contrato__data_vencimento__year=year,
                parcelas_contrato__data_vencimento__month=month,
            )
            | Q(
                tipo=TipoPagamento.PARCELA,
                parcelas_contrato__data_vencimento__year=year,
                parcelas_contrato__data_vencimento__month=month,
            )
        ).distinct()

        # Prefetch related data for optimized queries
        return pagamentos_qs.select_related(
            "implantacao",
            "parcelas_contrato__contrato",
        )
