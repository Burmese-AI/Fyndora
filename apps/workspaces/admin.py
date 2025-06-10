from django.contrib import admin
from apps.workspaces.models import Workspace, WorkspaceTeam

# Register your models here.
admin.site.register(Workspace)
admin.site.register(WorkspaceTeam)
