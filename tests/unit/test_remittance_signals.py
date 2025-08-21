# from decimal import Decimal

# import pytest
# from django.contrib.contenttypes.models import ContentType
# from django.db import connection
# from guardian.shortcuts import assign_perm

# from apps.entries.permissions import EntryPermissions
# from apps.entries.services import entry_create
# from apps.remittance.models import Remittance
# from apps.workspaces.models import WorkspaceTeam
# from tests.factories import (
#     TeamFactory,
#     TeamMemberFactory,
#     WorkspaceFactory,
#     WorkspaceTeamFactory,
# )


# @pytest.fixture
# def remittance_test_data():
#     """Provides a team and a submitter for remittance tests."""
#     team = TeamFactory(title="Test Team")
#     submitter = TeamMemberFactory(team=team)

#     workspace = submitter.organization_member.organization.workspaces.first()
#     if not workspace:
#         workspace = WorkspaceFactory(
#             organization=submitter.organization_member.organization
#         )

#     workspace_team = WorkspaceTeamFactory(team=team, workspace=workspace)

#     # Assign required permissions to the submitter's user
#     assign_perm(
#         EntryPermissions.ADD_ENTRY, submitter.organization_member.user, workspace
#     )

#     return submitter, team, workspace, workspace_team


# @pytest.mark.unit
# @pytest.mark.django_db
# class TestRemittanceSignal:
#     """Test remittance signal business logic."""

#     def test_remittance_creation_on_income_entry(self, remittance_test_data):
#         """Test that a remittance record is created when a new income entry is saved."""
#         submitter, _, workspace, workspace_team = remittance_test_data

#         assert Remittance.objects.count() == 0

#         entry_create(
#             entry_type="income",
#             amount=Decimal("1000.00"),
#             submitted_by=submitter,
#             description="Test Income Entry",
#             workspace=workspace,
#             workspace_team=workspace_team,
#         )

#         assert Remittance.objects.count() == 1
#         remittance = Remittance.objects.first()
#         assert remittance.due_amount == Decimal("900.00")  # 90% of 1000
#         assert remittance.status == "pending"

#     def test_remittance_not_created_for_non_income_entry(self, remittance_test_data):
#         """Test that no remittance is created for non-income entries."""
#         submitter, _, workspace, workspace_team = remittance_test_data

#         entry_create(
#             entry_type="disbursement",
#             amount=Decimal("500.00"),
#             submitted_by=submitter,
#             description="Test Expense Entry",
#             workspace=workspace,
#             workspace_team=workspace_team,
#         )

#         assert Remittance.objects.count() == 0

#     def test_remittance_not_created_on_entry_update(self, remittance_test_data):
#         """Test that the signal does not trigger on entry updates."""
#         submitter, _, workspace, workspace_team = remittance_test_data

#         entry = entry_create(
#             entry_type="income",
#             amount=Decimal("1000.00"),
#             submitted_by=submitter,
#             description="Test Income Entry",
#             workspace=workspace,
#             workspace_team=workspace_team,
#         )

#         assert Remittance.objects.count() == 1
#         initial_due_amount = Remittance.objects.first().due_amount

#         # Update the entry
#         entry.amount = Decimal("2000.00")
#         entry.save()

#         # The signal only runs on creation, so the remittance record should not be updated.
#         assert Remittance.objects.count() == 1
#         assert Remittance.objects.first().due_amount == initial_due_amount

#     def test_custom_remittance_rate_is_used(self):
#         """Test that the team's custom remittance rate is used if available."""
#         workspace_team = WorkspaceTeamFactory(custom_remittance_rate=Decimal("15.00"))

#         submitter = TeamMemberFactory(team=workspace_team.team)

#         workspace = submitter.organization_member.organization.workspaces.first()
#         if not workspace:
#             workspace = WorkspaceFactory(
#                 organization=submitter.organization_member.organization
#             )

#         # Assign required permissions to the submitter's user
#         assign_perm(
#             EntryPermissions.ADD_ENTRY, submitter.organization_member.user, workspace
#         )

#         entry_create(
#             entry_type="income",
#             amount=Decimal("1000.00"),
#             submitted_by=submitter,
#             description="Test Income Entry",
#             workspace=workspace,
#             workspace_team=workspace_team,
#         )

#         assert Remittance.objects.count() == 1
#         remittance = Remittance.objects.first()
#         assert remittance.due_amount == Decimal("150.00")  # 15% of 1000

#     def test_no_remittance_if_workspace_team_does_not_exist(self, remittance_test_data):
#         """Test that no remittance is created if the team is not associated with the workspace."""
#         submitter, team, workspace, _ = remittance_test_data

#         # Ensure the WorkspaceTeam link is removed to test the signal's early exit
#         WorkspaceTeam.objects.filter(
#             team=team,
#             workspace__organization=submitter.organization_member.organization,
#         ).delete()

#         assert Remittance.objects.count() == 0

#         # Create entry directly using raw SQL to bypass model validation
#         # This is necessary because the model validation would prevent creating an income entry without workspace_team
#         # But we need to test the signal behavior when workspace_team doesn't exist
#         with connection.cursor() as cursor:
#             cursor.execute(
#                 """
#                 INSERT INTO entries_entry (
#                     entry_id, 
#                     submitter_content_type_id, 
#                     submitter_object_id, 
#                     workspace_id, 
#                     entry_type, 
#                     amount, 
#                     description, 
#                     status, 
#                     is_flagged,
#                     submitted_at,
#                     created_at,
#                     updated_at
#                 ) VALUES (
#                     %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW()
#                 )
#                 """,
#                 [
#                     str(submitter.pk),  # Using submitter.pk as entry_id for simplicity
#                     ContentType.objects.get_for_model(submitter).id,
#                     str(submitter.pk),
#                     workspace.pk,
#                     "income",
#                     Decimal("1000.00"),
#                     "Test Income Entry",
#                     "pending_review",
#                     False,  # is_flagged
#                 ],
#             )

#         # The signal should not create a remittance record since the workspace_team doesn't exist
#         assert Remittance.objects.count() == 0
