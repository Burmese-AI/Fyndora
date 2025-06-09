from django.contrib import admin
from apps.organizations.models import Organization, OrganizationMember

admin.site.register(Organization)
admin.site.register(OrganizationMember)
