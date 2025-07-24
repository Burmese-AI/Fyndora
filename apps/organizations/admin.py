from django.contrib import admin
from apps.organizations.models import Organization, OrganizationMember, OrganizationExchangeRate

admin.site.register(Organization)
admin.site.register(OrganizationMember)
admin.site.register(OrganizationExchangeRate)
