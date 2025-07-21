from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def get_update_exchange_rate_url(
    exchange_rate_level, exchange_rate, organization, workspace=None
):
    if exchange_rate_level == "organization":
        return reverse(
            "organization_exchange_rate_update",
            kwargs={"organization_id": organization.pk, "pk": exchange_rate.pk},
        )

    elif exchange_rate_level == "workspace":
        pass
        # return reverse("workspace_exchange_rate_update", kwargs={"workspace_id": workspace.workspace_id, "pk": exchange_rate.pk})


@register.simple_tag
def get_delete_exchange_rate_url(
    exchange_rate_level, exchange_rate, organization, workspace=None
):
    if exchange_rate_level == "organization":
        return reverse(
            "organization_exchange_rate_delete",
            kwargs={"organization_id": organization.pk, "pk": exchange_rate.pk},
        )
    elif exchange_rate_level == "workspace":
        pass


@register.simple_tag
def get_detail_exchange_rate_url(
    exchange_rate_level, exchange_rate, organization, workspace=None
):
    if exchange_rate_level == "organization":
        return reverse(
            "organization_exchange_rate_detail",
            kwargs={"organization_id": organization.pk, "pk": exchange_rate.pk},
        )

    elif exchange_rate_level == "workspace":
        pass
        # return reverse("workspace_exchange_rate_update", kwargs={"workspace_id": workspace.workspace_id, "pk": exchange_rate.pk})
