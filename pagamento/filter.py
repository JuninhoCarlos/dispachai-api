import calendar
from datetime import date

import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import (
    Pagamento,
    PagamentoEvento,
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


class RelatorioReceitaFilter(django_filters.FilterSet):
    data_inicio = django_filters.DateFilter(
        field_name="data_pagamento", lookup_expr="gte"
    )
    data_fim = django_filters.DateFilter(field_name="data_pagamento", lookup_expr="lte")
    advogado_id = django_filters.NumberFilter(
        field_name="pagamento__processo__advogado_id"
    )

    class Meta:
        model = PagamentoEvento
        fields = ["data_inicio", "data_fim", "advogado_id"]

    @property
    def data_inicio_effective(self):
        val = self.form.cleaned_data.get("data_inicio") if self.is_bound else None
        if val:
            return val
        today = date.today()
        return today.replace(day=1)

    @property
    def data_fim_effective(self):
        val = self.form.cleaned_data.get("data_fim") if self.is_bound else None
        if val:
            return val
        today = date.today()
        return today.replace(day=calendar.monthrange(today.year, today.month)[1])

    @property
    def qs(self):
        qs = super().qs
        if not (self.is_bound and self.form.cleaned_data.get("data_inicio")):
            qs = qs.filter(data_pagamento__gte=self.data_inicio_effective)
        if not (self.is_bound and self.form.cleaned_data.get("data_fim")):
            qs = qs.filter(data_pagamento__lte=self.data_fim_effective)
        return qs
