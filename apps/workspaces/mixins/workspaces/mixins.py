from typing import Any


class WorkspaceFilteringMixin:
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["workspace_options"] = self.organization.workspaces.all()
        return context
