from typing import Any

class ExchangeRateUrlIdentifierMixin:
    def get_exchange_rate_level(self):
        raise NotImplementedError("You must implement get_exchange_rate_level() in the subclass")

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["url_identifier"] = self.get_exchange_rate_level()
        return context