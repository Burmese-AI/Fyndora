"""
Unit tests for Workspace permissions.

Tests cover:
- assign_workspace_permissions function
- update_workspace_admin_group function
- check_create_workspace_permission function
- check_change_workspace_admin_permission function
- check_change_workspace_permission function
- assign_workspace_team_permissions function
- remove_workspace_team_permissions function
"""

import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.http import HttpResponse

from apps.workspaces.permissions import (
    assign_workspace_permissions,
    update_workspace_admin_group,
    check_create_workspace_permission,
    check_change_workspace_admin_permission,
    check_change_workspace_permission,
    assign_workspace_team_permissions,
    remove_workspace_team_permissions,
)
from apps.core.permissions import (
    OrganizationPermissions,
    WorkspacePermissions,
    WorkspaceTeamPermissions,
)
from tests.factories.organization_factories import (
    OrganizationWithOwnerFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory
from tests.factories.user_factories import CustomUserFactory
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceTeamFactory,
)

User = get_user_model()


@pytest.mark.unit
class TestAssignWorkspacePermissions(TestCase):
    """Test the assign_workspace_permissions function."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.workspace_admin = OrganizationMemberFactory(organization=self.organization)
        self.operations_reviewer = OrganizationMemberFactory(organization=self.organization)
        
        # Set workspace admin and operations reviewer
        self.workspace.workspace_admin = self.workspace_admin
        self.workspace.operations_reviewer = self.operations_reviewer
        self.workspace.save()

    @pytest.mark.django_db
    def test_assign_workspace_permissions_success(self):
        """Test successful assignment of workspace permissions."""
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.side_effect = [
                ['perm1', 'perm2'],  # WORKSPACE_ADMIN permissions
                ['perm3', 'perm4'],  # OPERATIONS_REVIEWER permissions
                ['perm5', 'perm6'],  # ORG_OWNER permissions
            ]
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    assign_workspace_permissions(self.workspace, self.organization.owner.user)
                    
                    # Check that groups were created
                    self.assertTrue(Group.objects.filter(
                        name=f"Workspace Admins - {self.workspace.workspace_id}"
                    ).exists())
                    self.assertTrue(Group.objects.filter(
                        name=f"Operations Reviewer - {self.workspace.workspace_id}"
                    ).exists())
                    self.assertTrue(Group.objects.filter(
                        name=f"Org Owner - {self.organization.organization_id}"
                    ).exists())
                    
                    # Check that permissions were assigned
                    self.assertTrue(mock_assign_perm.called)
                    
                    # Check that audit logging was called
                    mock_log.assert_called()

    @pytest.mark.django_db
    def test_assign_workspace_permissions_no_admin_no_reviewer(self):
        """Test assignment when workspace has no admin or reviewer."""
        workspace = WorkspaceFactory(organization=self.organization)
        # No workspace_admin or operations_reviewer set
        
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.side_effect = [
                ['perm1', 'perm2'],  # WORKSPACE_ADMIN permissions
                ['perm3', 'perm4'],  # OPERATIONS_REVIEWER permissions
                ['perm5', 'perm6'],  # ORG_OWNER permissions
            ]
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    assign_workspace_permissions(workspace, self.organization.owner.user)
                    
                    # Groups should still be created
                    self.assertTrue(Group.objects.filter(
                        name=f"Workspace Admins - {workspace.workspace_id}"
                    ).exists())
                    
                    # Audit logging should still be called
                    mock_log.assert_called()

    @pytest.mark.django_db
    def test_assign_workspace_permissions_exception_handling(self):
        """Test exception handling in permission assignment."""
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.side_effect = Exception("Permission error")
            
            with patch('apps.workspaces.permissions.logger.error') as mock_logger:
                with self.assertRaises(Exception):
                    assign_workspace_permissions(self.workspace, self.organization.owner.user)
                
                # Error should be logged
                mock_logger.assert_called()

    @pytest.mark.django_db
    def test_assign_workspace_permissions_audit_logging_failure(self):
        """Test that permission assignment continues even if audit logging fails."""
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.side_effect = [
                ['perm1'],  # WORKSPACE_ADMIN permissions
                ['perm2'],  # OPERATIONS_REVIEWER permissions
                ['perm3'],  # ORG_OWNER permissions
            ]
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    mock_log.side_effect = Exception("Audit logging failed")
                    
                    # Should not raise exception
                    assign_workspace_permissions(self.workspace, self.organization.owner.user)
                    
                    # Groups should still be created
                    self.assertTrue(Group.objects.filter(
                        name=f"Workspace Admins - {self.workspace.workspace_id}"
                    ).exists())


@pytest.mark.unit
class TestUpdateWorkspaceAdminGroup(TestCase):
    """Test the update_workspace_admin_group function."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.previous_admin = OrganizationMemberFactory(organization=self.organization)
        self.new_admin = OrganizationMemberFactory(organization=self.organization)
        self.previous_reviewer = OrganizationMemberFactory(organization=self.organization)
        self.new_reviewer = OrganizationMemberFactory(organization=self.organization)

    @pytest.mark.django_db
    def test_update_workspace_admin_group_no_changes(self):
        """Test update when no changes are made."""
        result = update_workspace_admin_group(
            self.workspace,
            self.previous_admin,
            self.previous_admin,  # Same admin
            self.previous_reviewer,
            self.previous_reviewer,  # Same reviewer
            self.organization.owner.user
        )
        
        # Should return early without making changes
        self.assertIsNone(result)

    @pytest.mark.django_db
    def test_update_workspace_admin_group_admin_change(self):
        """Test update when admin changes."""
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            update_workspace_admin_group(
                self.workspace,
                self.previous_admin,
                self.new_admin,
                self.previous_reviewer,
                self.previous_reviewer,
                self.organization.owner.user
            )
            
            # Check that groups were created/updated
            workspace_admins_group = Group.objects.get(
                name=f"Workspace Admins - {self.workspace.workspace_id}"
            )
            
            # Previous admin should be removed
            self.assertNotIn(self.previous_admin.user, workspace_admins_group.user_set.all())
            # New admin should be added
            self.assertIn(self.new_admin.user, workspace_admins_group.user_set.all())
            
            # Audit logging should be called for admin change
            mock_log.assert_called()

    @pytest.mark.django_db
    def test_update_workspace_admin_group_reviewer_change(self):
        """Test update when operations reviewer changes."""
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            update_workspace_admin_group(
                self.workspace,
                self.previous_admin,
                self.previous_admin,
                self.previous_reviewer,
                self.new_reviewer,
                self.organization.owner.user
            )
            
            # Check that groups were created/updated
            operations_reviewer_group = Group.objects.get(
                name=f"Operations Reviewer - {self.workspace.workspace_id}"
            )
            
            # Previous reviewer should be removed
            self.assertNotIn(self.previous_reviewer.user, operations_reviewer_group.user_set.all())
            # New reviewer should be added
            self.assertIn(self.new_reviewer.user, operations_reviewer_group.user_set.all())
            
            # Audit logging should be called for reviewer change
            mock_log.assert_called()

    @pytest.mark.django_db
    def test_update_workspace_admin_group_both_changes(self):
        """Test update when both admin and reviewer change."""
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            update_workspace_admin_group(
                self.workspace,
                self.previous_admin,
                self.new_admin,
                self.previous_reviewer,
                self.new_reviewer,
                self.organization.owner.user
            )
            
            # Check both groups were updated
            workspace_admins_group = Group.objects.get(
                name=f"Workspace Admins - {self.workspace.workspace_id}"
            )
            operations_reviewer_group = Group.objects.get(
                name=f"Operations Reviewer - {self.workspace.workspace_id}"
            )
            
            # Admin changes
            self.assertNotIn(self.previous_admin.user, workspace_admins_group.user_set.all())
            self.assertIn(self.new_admin.user, workspace_admins_group.user_set.all())
            
            # Reviewer changes
            self.assertNotIn(self.previous_reviewer.user, operations_reviewer_group.user_set.all())
            self.assertIn(self.new_reviewer.user, operations_reviewer_group.user_set.all())
            
            # Audit logging should be called for both changes
            self.assertEqual(mock_log.call_count, 2)

    @pytest.mark.django_db
    def test_update_workspace_admin_group_audit_logging_failure(self):
        """Test that group updates continue even if audit logging fails."""
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            mock_log.side_effect = Exception("Audit logging failed")
            
            # Should not raise exception
            update_workspace_admin_group(
                self.workspace,
                self.previous_admin,
                self.new_admin,
                self.previous_reviewer,
                self.previous_reviewer,
                self.organization.owner.user
            )
            
            # Groups should still be updated
            workspace_admins_group = Group.objects.get(
                name=f"Workspace Admins - {self.workspace.workspace_id}"
            )
            self.assertIn(self.new_admin.user, workspace_admins_group.user_set.all())


@pytest.mark.unit
class TestPermissionCheckFunctions(TestCase):
    """Test the permission check functions."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.user = CustomUserFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )

    @pytest.mark.django_db
    def test_check_create_workspace_permission_denied(self):
        """Test permission check when user lacks permission."""
        request = self.factory.get('/')
        request.user = self.user
        
        with patch('apps.workspaces.permissions.permission_denied_view') as mock_denied:
            mock_denied.return_value = HttpResponse("Permission denied")
            
            result = check_create_workspace_permission(request, self.organization)
            
            # Should return permission denied response
            self.assertEqual(result.status_code, 200)
            mock_denied.assert_called()

    @pytest.mark.django_db
    def test_check_create_workspace_permission_allowed(self):
        """Test permission check when user has permission."""
        request = self.factory.get('/')
        request.user = self.organization.owner.user
        
        # Mock the permission check to return True
        with patch.object(request.user, 'has_perm') as mock_has_perm:
            mock_has_perm.return_value = True
            
            result = check_create_workspace_permission(request, self.organization)
            
            # Should return None (no action needed)
            self.assertIsNone(result)

    @pytest.mark.django_db
    def test_check_change_workspace_admin_permission_denied(self):
        """Test permission check when user lacks permission to change workspace admin."""
        request = self.factory.get('/')
        request.user = self.user
        
        with patch('apps.workspaces.permissions.permission_denied_view') as mock_denied:
            mock_denied.return_value = HttpResponse("Permission denied")
            
            result = check_change_workspace_admin_permission(request, self.organization)
            
            # Should return permission denied response
            self.assertEqual(result.status_code, 200)
            mock_denied.assert_called()

    @pytest.mark.django_db
    def test_check_change_workspace_admin_permission_allowed(self):
        """Test permission check when user has permission to change workspace admin."""
        request = self.factory.get('/')
        request.user = self.organization.owner.user
        
        # Mock the permission check to return True
        with patch.object(request.user, 'has_perm') as mock_has_perm:
            mock_has_perm.return_value = True
            
            result = check_change_workspace_admin_permission(request, self.organization)
            
            # Should return None (no action needed)
            self.assertIsNone(result)

    @pytest.mark.django_db
    def test_check_change_workspace_permission_denied(self):
        """Test permission check when user lacks permission to change workspace."""
        request = self.factory.get('/')
        request.user = self.user
        
        with patch('apps.workspaces.permissions.permission_denied_view') as mock_denied:
            mock_denied.return_value = HttpResponse("Permission denied")
            
            result = check_change_workspace_permission(request, self.workspace)
            
            # Should return permission denied response
            self.assertEqual(result.status_code, 200)
            mock_denied.assert_called()

    @pytest.mark.django_db
    def test_check_change_workspace_permission_allowed(self):
        """Test permission check when user has permission to change workspace."""
        request = self.factory.get('/')
        request.user = self.organization.owner.user
        
        # Mock the permission check to return True
        with patch.object(request.user, 'has_perm') as mock_has_perm:
            mock_has_perm.return_value = True
            
            result = check_change_workspace_permission(request, self.workspace)
            
            # Should return None (no action needed)
            self.assertIsNone(result)


@pytest.mark.unit
class TestAssignWorkspaceTeamPermissions(TestCase):
    """Test the assign_workspace_team_permissions function."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        
        # Create team members
        self.team_member1 = OrganizationMemberFactory(organization=self.organization)
        self.team_member2 = OrganizationMemberFactory(organization=self.organization)
        TeamMemberFactory(team=self.team, organization_member=self.team_member1)
        TeamMemberFactory(team=self.team, organization_member=self.team_member2)

    @pytest.mark.django_db
    def test_assign_workspace_team_permissions_success(self):
        """Test successful assignment of workspace team permissions."""
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.return_value = ['perm1', 'perm2']
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    result = assign_workspace_team_permissions(
                        self.workspace_team, 
                        self.organization.owner.user
                    )
                    
                    # Should return the group
                    self.assertIsNotNone(result)
                    self.assertEqual(result.name, f"Workspace Team - {self.workspace_team.workspace_team_id}")
                    
                    # Check that permissions were assigned
                    self.assertTrue(mock_assign_perm.called)
                    
                    # Check that audit logging was called
                    mock_log.assert_called()

    @pytest.mark.django_db
    def test_assign_workspace_team_permissions_with_team_coordinator(self):
        """Test permission assignment when team has a coordinator."""
        self.team.team_coordinator = self.team_member1
        self.team.save()
        
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.return_value = ['perm1', 'perm2']
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    result = assign_workspace_team_permissions(
                        self.workspace_team, 
                        self.organization.owner.user
                    )
                    
                    # Should return the group
                    self.assertIsNotNone(result)
                    
                    # Check that team coordinator permission was assigned
                    mock_assign_perm.assert_any_call(
                        WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE,
                        self.team_member1.user,
                        self.workspace
                    )

    @pytest.mark.django_db
    def test_assign_workspace_team_permissions_team_coordinator_error(self):
        """Test that permission assignment continues even if team coordinator permission fails."""
        self.team.team_coordinator = self.team_member1
        self.team.save()
        
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.return_value = ['perm1', 'perm2']
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                # Make the team coordinator permission assignment fail
                def side_effect(perm, user, obj):
                    if perm == WorkspacePermissions.VIEW_WORKSPACE_TEAMS_UNDER_WORKSPACE:
                        raise Exception("Permission assignment failed")
                    return None
                
                mock_assign_perm.side_effect = side_effect
                
                with patch('apps.workspaces.permissions.logger.error') as mock_logger:
                    result = assign_workspace_team_permissions(
                        self.workspace_team, 
                        self.organization.owner.user
                    )
                    
                    # Should still return the group
                    self.assertIsNotNone(result)
                    
                    # Error should be logged
                    mock_logger.assert_called()

    @pytest.mark.django_db
    def test_assign_workspace_team_permissions_audit_logging_failure(self):
        """Test that permission assignment continues even if audit logging fails."""
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.return_value = ['perm1', 'perm2']
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    mock_log.side_effect = Exception("Audit logging failed")
                    
                    with patch('apps.workspaces.permissions.logger.error') as mock_logger:
                        result = assign_workspace_team_permissions(
                            self.workspace_team, 
                            self.organization.owner.user
                        )
                        
                        # Should still return the group
                        self.assertIsNotNone(result)
                        
                        # Error should be logged
                        mock_logger.assert_called()

    @pytest.mark.django_db
    def test_assign_workspace_team_permissions_no_team_members(self):
        """Test permission assignment when team has no members."""
        # Remove all team members
        self.team.members.all().delete()
        
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.return_value = ['perm1', 'perm2']
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    result = assign_workspace_team_permissions(
                        self.workspace_team, 
                        self.organization.owner.user
                    )
                    
                    # Should still return the group
                    self.assertIsNotNone(result)
                    
                    # Audit logging should still be called (with org owner as target)
                    mock_log.assert_called()


@pytest.mark.unit
class TestRemoveWorkspaceTeamPermissions(TestCase):
    """Test the remove_workspace_team_permissions function."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )
        
        # Create team members
        self.team_member = OrganizationMemberFactory(organization=self.organization)
        TeamMemberFactory(team=self.team, organization_member=self.team_member)

    @pytest.mark.django_db
    def test_remove_workspace_team_permissions_success(self):
        """Test successful removal of workspace team permissions."""
        # First create the group
        group_name = f"Workspace Team - {self.workspace_team.workspace_team_id}"
        group = Group.objects.create(name=group_name)
        group.user_set.add(self.team_member.user)
        
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            remove_workspace_team_permissions(
                self.workspace_team, 
                self.organization.owner.user
            )
            
            # Group should be deleted
            self.assertFalse(Group.objects.filter(name=group_name).exists())
            
            # Audit logging should be called
            mock_log.assert_called()

    @pytest.mark.django_db
    def test_remove_workspace_team_permissions_group_not_found(self):
        """Test removal when group doesn't exist."""
        with patch('apps.workspaces.permissions.logger.debug') as mock_debug:
            remove_workspace_team_permissions(
                self.workspace_team, 
                self.organization.owner.user
            )
            
            # Debug message should be logged
            mock_debug.assert_called()

    @pytest.mark.django_db
    def test_remove_workspace_team_permissions_audit_logging_failure(self):
        """Test that group removal continues even if audit logging fails."""
        # First create the group
        group_name = f"Workspace Team - {self.workspace_team.workspace_team_id}"
        group = Group.objects.create(name=group_name)
        group.user_set.add(self.team_member.user)
        
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            mock_log.side_effect = Exception("Audit logging failed")
            
            with patch('apps.workspaces.permissions.logger.error') as mock_logger:
                remove_workspace_team_permissions(
                    self.workspace_team, 
                    self.organization.owner.user
                )
                
                # Group should still be deleted
                self.assertFalse(Group.objects.filter(name=group_name).exists())
                
                # Error should be logged
                mock_logger.assert_called()

    @pytest.mark.django_db
    def test_remove_workspace_team_permissions_exception_handling(self):
        """Test exception handling in permission removal."""
        with patch('apps.workspaces.permissions.Group.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")
            
            with patch('apps.workspaces.permissions.logger.error') as mock_logger:
                # Should not raise exception
                remove_workspace_team_permissions(
                    self.workspace_team, 
                    self.organization.owner.user
                )
                
                # Error should be logged
                mock_logger.assert_called()


@pytest.mark.unit
class TestPermissionEdgeCases(TestCase):
    """Test edge cases and error scenarios."""

    def setUp(self):
        """Set up test data."""
        self.organization = OrganizationWithOwnerFactory()
        self.workspace = WorkspaceFactory(organization=self.organization)
        self.team = TeamFactory(organization=self.organization)
        self.workspace_team = WorkspaceTeamFactory(
            workspace=self.workspace, team=self.team
        )

    @pytest.mark.django_db
    def test_assign_workspace_permissions_no_request_user(self):
        """Test permission assignment without request user."""
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.side_effect = [
                ['perm1'],  # WORKSPACE_ADMIN permissions
                ['perm2'],  # OPERATIONS_REVIEWER permissions
                ['perm3'],  # ORG_OWNER permissions
            ]
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    assign_workspace_permissions(self.workspace)
                    
                    # Groups should still be created
                    self.assertTrue(Group.objects.filter(
                        name=f"Workspace Admins - {self.workspace.workspace_id}"
                    ).exists())
                    
                    # Audit logging should not be called
                    mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_update_workspace_admin_group_no_request_user(self):
        """Test admin group update without request user."""
        previous_admin = OrganizationMemberFactory(organization=self.organization)
        new_admin = OrganizationMemberFactory(organization=self.organization)
        
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            update_workspace_admin_group(
                self.workspace,
                previous_admin,
                new_admin,
                None,
                None
            )
            
            # Groups should still be updated
            workspace_admins_group = Group.objects.get(
                name=f"Workspace Admins - {self.workspace.workspace_id}"
            )
            self.assertIn(new_admin.user, workspace_admins_group.user_set.all())
            
            # Audit logging should not be called
            mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_assign_workspace_team_permissions_no_request_user(self):
        """Test team permission assignment without request user."""
        with patch('apps.workspaces.permissions.get_permissions_for_role') as mock_get_perms:
            mock_get_perms.return_value = ['perm1', 'perm2']
            
            with patch('apps.workspaces.permissions.assign_perm') as mock_assign_perm:
                with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
                    result = assign_workspace_team_permissions(self.workspace_team)
                    
                    # Should still return the group
                    self.assertIsNotNone(result)
                    
                    # Audit logging should not be called
                    mock_log.assert_not_called()

    @pytest.mark.django_db
    def test_remove_workspace_team_permissions_no_request_user(self):
        """Test team permission removal without request user."""
        # First create the group
        group_name = f"Workspace Team - {self.workspace_team.workspace_team_id}"
        group = Group.objects.create(name=group_name)
        
        with patch('apps.workspaces.permissions.BusinessAuditLogger.log_permission_change') as mock_log:
            remove_workspace_team_permissions(self.workspace_team)
            
            # Group should still be deleted
            self.assertFalse(Group.objects.filter(name=group_name).exists())
            
            # Audit logging should not be called
            mock_log.assert_not_called()
