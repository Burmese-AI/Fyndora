"""
Unit tests for apps.reports.permissions
"""

import pytest
from unittest.mock import Mock, patch

from apps.reports.permissions import can_view_report_page
from apps.core.permissions import OrganizationPermissions


@pytest.mark.unit
class TestCanViewReportPage:
    def test_can_view_report_page_with_permission(self):
        """Test that user with VIEW_REPORT_PAGE permission can view report page."""
        user = Mock()
        organization = Mock()
        user.has_perm.return_value = True
        
        result = can_view_report_page(user, organization)
        
        assert result is True
        user.has_perm.assert_called_once_with(OrganizationPermissions.VIEW_REPORT_PAGE, organization)

    def test_can_view_report_page_without_permission(self):
        """Test that user without VIEW_REPORT_PAGE permission cannot view report page."""
        user = Mock()
        organization = Mock()
        user.has_perm.return_value = False
        
        result = can_view_report_page(user, organization)
        
        assert result is False
        user.has_perm.assert_called_once_with(OrganizationPermissions.VIEW_REPORT_PAGE, organization)

    def test_can_view_report_page_with_none_user(self):
        """Test that None user cannot view report page."""
        user = None
        organization = Mock()
        
        with pytest.raises(AttributeError):
            can_view_report_page(user, organization)

    def test_can_view_report_page_with_none_organization(self):
        """Test that user with None organization cannot view report page."""
        user = Mock()
        organization = None
        user.has_perm.return_value = False
        
        result = can_view_report_page(user, organization)
        
        assert result is False
        user.has_perm.assert_called_once_with(OrganizationPermissions.VIEW_REPORT_PAGE, organization)

    def test_can_view_report_page_permission_check_called_once(self):
        """Test that has_perm is called exactly once."""
        user = Mock()
        organization = Mock()
        user.has_perm.return_value = True
        
        can_view_report_page(user, organization)
        
        assert user.has_perm.call_count == 1

    def test_can_view_report_page_returns_boolean(self):
        """Test that function always returns a boolean value."""
        user = Mock()
        organization = Mock()
        
        # Test with permission
        user.has_perm.return_value = True
        result = can_view_report_page(user, organization)
        assert isinstance(result, bool)
        assert result is True
        
        # Test without permission
        user.has_perm.return_value = False
        result = can_view_report_page(user, organization)
        assert isinstance(result, bool)
        assert result is False

    def test_can_view_report_page_with_exception_from_has_perm(self):
        """Test behavior when has_perm raises an exception."""
        user = Mock()
        organization = Mock()
        user.has_perm.side_effect = Exception("Permission check failed")
        
        with pytest.raises(Exception, match="Permission check failed"):
            can_view_report_page(user, organization)

    def test_can_view_report_page_with_different_organization_objects(self):
        """Test that function works with different organization objects."""
        user = Mock()
        user.has_perm.return_value = True
        
        # Test with different organization types
        org1 = Mock()
        org2 = Mock()
        
        result1 = can_view_report_page(user, org1)
        result2 = can_view_report_page(user, org2)
        
        assert result1 is True
        assert result2 is True
        assert user.has_perm.call_count == 2
        
        # Verify correct organizations were passed
        calls = user.has_perm.call_args_list
        assert calls[0][0][1] == org1
        assert calls[1][0][1] == org2

    def test_can_view_report_page_permission_constant_used(self):
        """Test that the correct permission constant is used."""
        user = Mock()
        organization = Mock()
        user.has_perm.return_value = True
        
        can_view_report_page(user, organization)
        
        # Verify the correct permission constant was used
        call_args = user.has_perm.call_args[0]
        assert call_args[0] == OrganizationPermissions.VIEW_REPORT_PAGE

    def test_can_view_report_page_with_mock_user_attributes(self):
        """Test with user that has additional attributes."""
        user = Mock()
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.has_perm.return_value = True
        
        organization = Mock()
        organization.title = "Test Org"
        
        result = can_view_report_page(user, organization)
        
        assert result is True
        user.has_perm.assert_called_once_with(OrganizationPermissions.VIEW_REPORT_PAGE, organization)
