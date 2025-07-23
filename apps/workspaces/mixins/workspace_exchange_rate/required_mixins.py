from typing import Any
from django.shortcuts import get_object_or_404
from apps.workspaces.models import WorkspaceExchangeRate


class WorkspaceExchangeRateRequiredMixin:
    exchange_rate = None
    instance = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        workspace_exchange_rate_id = kwargs.get("pk")
        self.exchange_rate = get_object_or_404(
            WorkspaceExchangeRate,
            workspace=self.workspace,
            pk=workspace_exchange_rate_id,
        )
        self.instance = self.exchange_rate

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["exchange_rate"] = self.exchange_rate
        return context