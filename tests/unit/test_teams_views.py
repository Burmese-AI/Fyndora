"""
Unit tests for Team views.
"""

from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.teams.constants import TeamMemberRole
from apps.teams.views import (
    add_team_member_view,
    create_team_view,
    delete_team_view,
    edit_team_view,
    edit_team_member_role_view,
    get_team_members_view,
    remove_team_member_view,
    teams_view,
)
from tests.factories.organization_factories import (
    OrganizationFactory,
    OrganizationMemberFactory,
)
from tests.factories.team_factories import TeamFactory, TeamMemberFactory
from tests.factories.user_factories import CustomUserFactory

User = get_user_model()


class FakeMessages:
    """Fake messages framework for testing."""
    
    def __init__(self):
        self.messages = []
    
    def add(self, level, message, extra_tags=''):
        self.messages.append({'level': level, 'message': message, 'extra_tags': extra_tags})
    
    def __iter__(self):
        return iter(self.messages)


class BaseTeamViewTest(TestCase):
    """Base test class for team view tests with common setup and utilities."""
    
    def setUp(self):
        """Set up common test data."""
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            organization=self.organization, user=self.user
        )

    def _add_messages_to_request(self, request):
        """Add messages middleware to request."""
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))

    def _create_request(self, method='GET', path='/', data=None, htmx=False, headers=None):
        """Create a request with common setup."""
        if method.upper() == 'GET':
            request = self.factory.get(path, data or {})
        elif method.upper() == 'POST':
            request = self.factory.post(path, data or {})
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        request.user = self.user
        self._add_messages_to_request(request)
        
        # Add custom headers if provided
        if headers:
            for key, value in headers.items():
                if key == 'HX-Request':
                    request.META["HTTP_HX_REQUEST"] = value
                else:
                    request.META[f"HTTP_{key.upper().replace('-', '_')}"] = value
        
        if htmx:
            request.META["HTTP_HX_REQUEST"] = "true"
            # Mock the htmx attribute that django-htmx adds
            request.htmx = Mock()
            request.htmx.__bool__ = Mock(return_value=True)
        else:
            request.htmx = Mock()
            request.htmx.__bool__ = Mock(return_value=False)
        
        return request


class TeamsViewTest(BaseTeamViewTest):
    """Test teams_view function."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.teams = TeamFactory.create_batch(3, organization=self.organization)

    @patch("apps.workspaces.models.WorkspaceTeam.objects.filter")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.core.utils.can_manage_organization")
    def test_teams_view_success(self, mock_can_manage, mock_get_teams, mock_get_org, mock_workspace_filter):
        """Test successful teams view."""
        # Mock data
        mock_teams = [TeamFactory.build(), TeamFactory.build()]
        mock_get_teams.return_value = mock_teams
        mock_get_org.return_value = self.organization
        mock_can_manage.return_value = True
        mock_workspace_filter.return_value = []

        # Create request
        request = self._create_request()

        # Mock the user permission check that happens in the view
        with patch.object(request.user, 'has_perm', return_value=True):
            # Call view
            with patch("apps.teams.views.render") as mock_render:
                teams_view(request, self.organization.organization_id)

                # Verify render was called with correct context
                mock_render.assert_called_once()
                args, kwargs = mock_render.call_args

                self.assertEqual(args[0], request)
                self.assertEqual(args[1], "teams/index.html")

                context = args[2]
                self.assertEqual(context["teams"], mock_teams)
                self.assertEqual(context["organization"], self.organization)

    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.core.utils.can_manage_organization")
    def test_teams_view_no_permission(self, mock_can_manage, mock_get_teams, mock_get_org):
        """Test teams view when user has no manage permission."""
        # Mock data
        mock_teams = []
        mock_get_teams.return_value = mock_teams
        mock_get_org.return_value = self.organization
        mock_can_manage.return_value = False

        # Create request
        request = self._create_request()

        # Call view
        with patch("apps.teams.views.permission_denied_view") as mock_permission_denied:
            mock_permission_denied.return_value = Mock()  # Mock the response
            result = teams_view(request, self.organization.organization_id)

            # Verify permission denied was called
            mock_permission_denied.assert_called_once()
            # Verify the result is what permission_denied_view returned
            self.assertEqual(result, mock_permission_denied.return_value)


class CreateTeamViewTest(BaseTeamViewTest):
    """Test create_team_view function."""

    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.teams.views.check_add_team_permission_view")
    def test_create_team_view_get_success(self, mock_check_permission, mock_get_org_member, mock_get_org, mock_form):
        """Test successful GET request to create team view."""
        # Mock permission check
        mock_check_permission.return_value = None  # No redirect means permission granted
        mock_get_org.return_value = self.organization
        mock_get_org_member.return_value = self.org_member
        mock_form_instance = Mock()
        mock_form.return_value = mock_form_instance

        # Create request
        request = self._create_request()

        with patch("apps.teams.views.render") as mock_render:
            create_team_view(request, self.organization.organization_id)

            # Verify render was called
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args

            self.assertEqual(args[0], request)
            self.assertEqual(args[1], "teams/partials/create_team_form.html")

    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.teams.views.check_add_team_permission_view")
    def test_create_team_view_no_permission(self, mock_check_permission, mock_get_org_member, mock_get_org):
        """Test create team view when user has no permission."""
        from django.http import HttpResponse
        
        # Mock permission check to return redirect
        mock_redirect = HttpResponse("Redirect")
        mock_check_permission.return_value = mock_redirect
        mock_get_org.return_value = self.organization
        mock_get_org_member.return_value = self.org_member

        # Create request
        request = self._create_request()

        # Call view
        response = create_team_view(request, self.organization.organization_id)

        # Verify redirect was returned
        self.assertEqual(response, mock_redirect)

    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.teams.views.create_team_from_form")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.teams.views.check_add_team_permission_view")
    def test_create_team_view_post_success(self, mock_check_permission, mock_get_org_member, 
                                         mock_get_org, mock_create_team, mock_get_teams, mock_form):
        """Test successful POST request to create team view."""
        # Mock permission check
        mock_check_permission.return_value = None
        mock_get_org.return_value = self.organization
        mock_get_org_member.return_value = self.org_member
        mock_get_teams.return_value = []
        
        # Mock form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form.return_value = mock_form_instance
        
        # Mock successful team creation
        mock_team = TeamFactory.build()
        mock_create_team.return_value = mock_team

        # Create POST request
        request = self._create_request(
            method='POST',
            data={
                "title": "Test Team",
                "description": "Test Description",
            }
        )

        with patch("apps.teams.views.redirect") as mock_redirect:
            create_team_view(request, self.organization.organization_id)

            # Verify team creation was called
            mock_create_team.assert_called_once_with(
                mock_form_instance, organization=self.organization, orgMember=self.org_member
            )
            # Verify redirect was called
            mock_redirect.assert_called_once_with(
                "teams", organization_id=self.organization.organization_id
            )

    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.teams.views.check_add_team_permission_view")
    def test_create_team_view_post_invalid_form(self, mock_check_permission, mock_get_org_member, mock_get_org, mock_form):
        """Test POST request with invalid form."""
        # Mock permission check
        mock_check_permission.return_value = None
        mock_get_org.return_value = self.organization
        mock_get_org_member.return_value = self.org_member
        
        # Mock invalid form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {"title": ["This field is required."]}
        mock_form.return_value = mock_form_instance
        
        # Create POST request with invalid data (missing required fields)
        request = self._create_request(method='POST', data={})

        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_http_response:
                mock_render_to_string.return_value = "<div>error</div>"
                mock_response = Mock()
                mock_http_response.return_value = mock_response
                
                create_team_view(request, self.organization.organization_id)

                # Verify HttpResponse was called for form errors
                mock_http_response.assert_called_once()


class EditTeamViewTest(BaseTeamViewTest):
    """Test edit_team_view function."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.team = TeamFactory(organization=self.organization)

    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.check_change_team_permission_view")
    def test_edit_team_view_get(self, mock_check_permission, mock_get_team, mock_get_org, mock_form):
        """Test GET request to edit team view."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        mock_form_instance = Mock()
        mock_form.return_value = mock_form_instance

        request = self._create_request()

        with patch("apps.teams.views.render") as mock_render:
            edit_team_view(
                request, self.organization.organization_id, self.team.team_id
            )

            # Verify render was called
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args

            self.assertEqual(args[1], "teams/partials/edit_team_form.html")
            context = args[2]
            self.assertIn("form", context)
            self.assertIn("organization", context)

    @patch("apps.workspaces.models.WorkspaceTeam.objects.filter")
    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.update_team_from_form")
    @patch("apps.teams.views.check_change_team_permission_view")
    def test_edit_team_view_post_success(self, mock_check_permission, mock_update_team, 
                                       mock_get_team, mock_get_org, mock_form, mock_get_teams, mock_workspace_filter):
        """Test successful POST request to edit team view."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        mock_update_team.return_value = self.team
        mock_get_teams.return_value = [self.team]  # Return a list with the team
        mock_workspace_filter.return_value = []
        
        # Mock form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form.return_value = mock_form_instance

        request = self._create_request(
            method='POST',
            data={
                "title": "Updated Team",
                "description": "Updated Description",
            }
        )

        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_http_response:
                mock_render_to_string.return_value = "<div>success</div>"
                mock_response = Mock()
                mock_http_response.return_value = mock_response
                
                edit_team_view(
                    request, self.organization.organization_id, self.team.team_id
                )

                # Verify HttpResponse was called
                mock_http_response.assert_called_once()

    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.check_change_team_permission_view")
    def test_edit_team_view_post_error(self, mock_check_permission, mock_get_team, mock_get_org, mock_form):
        """Test POST request with invalid form."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        
        # Mock invalid form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {"title": ["This field is required."]}
        mock_form.return_value = mock_form_instance

        request = self._create_request(
            method='POST',
            data={}  # Invalid data
        )

        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_http_response:
                mock_render_to_string.return_value = "<div>error</div>"
                mock_response = Mock()
                mock_http_response.return_value = mock_response
                
                edit_team_view(
                    request, self.organization.organization_id, self.team.team_id
                )

                # Verify HttpResponse was called for error case
                mock_http_response.assert_called_once()


class DeleteTeamViewTest(BaseTeamViewTest):
    """Test delete_team_view function."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.team = TeamFactory(organization=self.organization)

    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.check_delete_team_permission_view")
    def test_delete_team_view_get(self, mock_check_permission, mock_get_team, mock_get_org):
        """Test GET request to delete team view."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None

        request = self._create_request()

        with patch("apps.teams.views.render") as mock_render:
            delete_team_view(
                request, self.organization.organization_id, self.team.team_id
            )

            # Verify render was called
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args

            self.assertEqual(args[1], "teams/partials/delete_team_form.html")
            context = args[2]
            self.assertEqual(context["team"], self.team)
            self.assertEqual(context["organization"], self.organization)

    @patch("apps.workspaces.models.WorkspaceTeam.objects.filter")
    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.remove_team_permissions")
    @patch("apps.teams.views.check_delete_team_permission_view")
    def test_delete_team_view_post_success(
        self, mock_check_permission, mock_remove_permissions, mock_get_team, 
        mock_get_org, mock_get_teams, mock_workspace_teams
    ):
        """Test successful POST request to delete team view."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        mock_get_teams.return_value = []
        
        # Mock workspace teams
        mock_workspace_teams_qs = Mock()
        mock_workspace_teams.return_value = mock_workspace_teams_qs

        request = self._create_request(method='POST')

        with patch("apps.teams.views.HttpResponse") as mock_response:
            with patch.object(self.team, "delete") as mock_delete:
                delete_team_view(
                    request, self.organization.organization_id, self.team.team_id
                )

                # Verify permissions were removed
                mock_remove_permissions.assert_called_once_with(self.team)
                
                # Verify team was deleted
                mock_delete.assert_called_once()

                # Verify HttpResponse was called
                mock_response.assert_called_once()


class GetTeamMembersViewTest(BaseTeamViewTest):
    """Test get_team_members_view function."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.team = TeamFactory(organization=self.organization)

    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.get_team_members_by_team_id")
    @patch("apps.teams.views.check_view_team_permission_view")
    def test_get_team_members_view_success(self, mock_check_permission, mock_get_members, 
                                         mock_get_team, mock_get_org):
        """Test successful get team members view."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        mock_members = [TeamMemberFactory.build(), TeamMemberFactory.build()]
        mock_get_members.return_value = mock_members

        request = self._create_request()

        with patch("apps.teams.views.render") as mock_render:
            get_team_members_view(
                request, self.organization.organization_id, self.team.team_id
            )

            # Verify render was called
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args

            self.assertEqual(args[1], "team_members/index.html")
            context = args[2]
            self.assertEqual(context["team"], self.team)
            self.assertEqual(context["organization"], self.organization)
            self.assertEqual(context["team_members"], mock_members)


class AddTeamMemberViewTest(BaseTeamViewTest):
    """Test add_team_member_view function."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.team = TeamFactory(organization=self.organization)
        self.org_member = OrganizationMemberFactory(organization=self.organization)

    @patch("apps.teams.views.TeamMemberForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.check_add_team_member_permission_view")
    def test_add_team_member_view_get(self, mock_check_permission, mock_get_team, mock_get_org, mock_form):
        """Test GET request to add team member view."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        mock_form_instance = Mock()
        mock_form.return_value = mock_form_instance

        request = self._create_request()

        with patch("apps.teams.views.render") as mock_render:
            add_team_member_view(
                request, self.organization.organization_id, self.team.team_id
            )

            # Verify render was called
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args

            self.assertEqual(args[1], "team_members/partials/add_team_member_form.html")
            context = args[2]
            self.assertIn("form", context)
            self.assertEqual(context["team"], self.team)
            self.assertEqual(context["organization"], self.organization)

    @patch("apps.teams.views.TeamMemberForm")
    @patch("apps.teams.views.get_team_members_by_team_id")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.create_team_member_from_form")
    @patch("apps.teams.views.check_add_team_member_permission_view")
    def test_add_team_member_view_post_success(self, mock_check_permission, mock_create_member, 
                                             mock_get_team, mock_get_org, mock_get_members, mock_form):
        """Test successful POST request to add team member view."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        mock_get_members.return_value = []
        mock_member = TeamMemberFactory.build()
        mock_create_member.return_value = mock_member
        
        # Mock form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form.return_value = mock_form_instance

        request = self._create_request(
            method='POST',
            data={
                "organization_member": self.org_member.pk,
                "role": TeamMemberRole.SUBMITTER,
            }
        )

        with patch("apps.teams.views.HttpResponse") as mock_response:
            add_team_member_view(
                request, self.organization.organization_id, self.team.team_id
            )

            # Verify HttpResponse was called
            mock_response.assert_called_once()

    @patch("apps.teams.views.TeamMemberForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.check_add_team_member_permission_view")
    def test_add_team_member_view_post_error(self, mock_check_permission, mock_get_team, mock_get_org, mock_form):
        """Test POST request with invalid form."""
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None
        
        # Mock invalid form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {"organization_member": ["This field is required."]}
        mock_form.return_value = mock_form_instance

        request = self._create_request(
            method='POST',
            data={'invalid': 'data'}
        )

        # Call view and expect HttpResponse with error content
        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_http_response:
                mock_render_to_string.return_value = "<div>error</div>"
                mock_response = Mock()
                mock_http_response.return_value = mock_response
                
                add_team_member_view(request, self.organization.organization_id, self.team.team_id)

                # Verify HttpResponse was called for error case
                mock_http_response.assert_called_once()


class RemoveTeamMemberViewTest(BaseTeamViewTest):
    """Test remove_team_member_view function."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(team=self.team)

    @patch("apps.teams.models.TeamMember.objects.filter")
    @patch("apps.teams.views.get_team_members_by_team_id")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.get_team_member_by_id")
    @patch("apps.teams.views.remove_team_member")
    def test_remove_team_member_view_success(self, mock_remove_member, 
                                           mock_get_member, mock_get_team, mock_get_org, mock_get_members, mock_filter_members):
        """Test successful remove team member view."""
        mock_get_member.return_value = self.team_member
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_get_members.return_value = []
        mock_filter_members.return_value = []

        request = self._create_request(method='POST')

        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_response:
                mock_render_to_string.return_value = "<div>test</div>"
                mock_response_obj = Mock()
                mock_response.return_value = mock_response_obj
                
                remove_team_member_view(
                    request,
                    self.organization.organization_id,
                    self.team.team_id,
                    self.team_member.team_member_id,
                )

                # Verify member removal was called
                mock_remove_member.assert_called_once_with(self.team_member)

                # Verify HttpResponse was called
                mock_response.assert_called_once()


class EditTeamMemberRoleViewTest(BaseTeamViewTest):
    """Test edit_team_member_role_view function."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.team = TeamFactory(organization=self.organization)
        self.team_member = TeamMemberFactory(team=self.team, role=TeamMemberRole.SUBMITTER)

    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.get_team_member_by_id")
    def test_edit_team_member_role_view_get(self, mock_get_member, mock_get_team, mock_get_org):
        """Test GET request to edit team member role view."""
        mock_get_member.return_value = self.team_member
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization

        request = self._create_request()

        with patch("apps.teams.views.render") as mock_render:
            edit_team_member_role_view(
                request, 
                self.organization.organization_id, 
                self.team.team_id,
                self.team_member.team_member_id
            )

            # Verify render was called
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args

            self.assertEqual(args[1], "team_members/partials/edit_team_member_role_form.html")
            context = args[2]
            self.assertIn("form", context)
            self.assertEqual(context["team"], self.team)
            self.assertEqual(context["organization"], self.organization)
            self.assertEqual(context["team_member"], self.team_member)

    @patch("apps.teams.models.TeamMember.objects.filter")
    @patch("apps.teams.views.get_team_members_by_team_id")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.get_team_member_by_id")
    @patch("apps.teams.views.update_team_member_role")
    def test_edit_team_member_role_view_post_success(self, mock_update_role, mock_get_member, 
                                                   mock_get_team, mock_get_org, mock_get_members, mock_filter_members):
        """Test successful POST request to edit team member role view."""
        mock_get_member.return_value = self.team_member
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization
        mock_get_members.return_value = []
        mock_filter_members.return_value = []

        request = self._create_request(
            method='POST',
            data={
                "role": TeamMemberRole.AUDITOR,
            }
        )

        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_response:
                mock_render_to_string.return_value = "<div>test</div>"
                mock_response_obj = Mock()
                mock_response.return_value = mock_response_obj
                
                edit_team_member_role_view(
                    request, 
                    self.organization.organization_id, 
                    self.team.team_id,
                    self.team_member.team_member_id
                )

                # Verify role update was called
                mock_update_role.assert_called_once()

                # Verify HttpResponse was called
                mock_response.assert_called_once()

    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.get_team_member_by_id")
    def test_edit_team_member_role_view_post_error(self, mock_get_member, mock_get_team, mock_get_org):
        """Test POST request with invalid form."""
        mock_get_member.return_value = self.team_member
        mock_get_team.return_value = self.team
        mock_get_org.return_value = self.organization

        request = self._create_request(
            method='POST',
            data={}  # Invalid data
        )

        with patch("apps.teams.views.HttpResponse") as mock_response:
            edit_team_member_role_view(
                request, 
                self.organization.organization_id, 
                self.team.team_id,
                self.team_member.team_member_id
            )

            # Verify HttpResponse was called for form errors
            mock_response.assert_called_once()


class ViewsErrorHandlingTest(BaseTeamViewTest):
    """Test error handling in views."""

    @patch("apps.workspaces.models.WorkspaceTeam.objects.filter")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.core.utils.can_manage_organization")
    def test_teams_view_exception_handling(self, mock_can_manage, mock_get_teams, mock_get_org, mock_workspace_filter):
        """Test teams view handles exceptions gracefully."""
        mock_get_teams.side_effect = Exception("Database error")
        mock_get_org.return_value = self.organization
        mock_can_manage.return_value = True
        mock_workspace_filter.return_value = []

        request = self._create_request()

        with patch.object(request.user, 'has_perm', return_value=True):
            with patch("apps.teams.views.redirect") as mock_redirect:
                teams_view(request, self.organization.organization_id)

                # Verify redirect was called due to exception
                mock_redirect.assert_called_once_with("teams", organization_id=self.organization.organization_id)

    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_team_by_id")
    @patch("apps.teams.views.check_change_team_permission_view")
    def test_edit_team_view_team_not_found(self, mock_check_permission, mock_get_team, mock_get_org):
        """Test edit team view when team not found."""
        mock_get_team.return_value = None
        mock_get_org.return_value = self.organization
        mock_check_permission.return_value = None

        request = self._create_request()

        with patch("apps.teams.views.redirect") as mock_redirect:
            edit_team_view(request, self.organization.organization_id, "invalid-id")

            # Verify redirect was called
            mock_redirect.assert_called_once()

    @patch("apps.workspaces.models.WorkspaceTeam.objects.filter")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.core.utils.can_manage_organization")
    def test_view_functions_with_invalid_organization_id(self, mock_can_manage, mock_get_teams, mock_get_org, mock_workspace_filter):
        """Test view functions handle invalid organization IDs."""
        mock_get_org.side_effect = Exception("Organization not found")
        mock_can_manage.return_value = False
        mock_get_teams.return_value = []
        mock_workspace_filter.return_value = []
        
        request = self._create_request()

        # Test with non-existent organization ID
        with patch.object(request.user, 'has_perm', return_value=True):
            with patch("apps.teams.views.redirect") as mock_redirect:
                teams_view(request, "invalid-org-id")

                # Verify redirect was called due to exception
                mock_redirect.assert_called_once()


class ViewsHTMXHandlingTest(BaseTeamViewTest):
    """Test HTMX-specific handling in views."""

    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.teams.views.create_team_from_form")
    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.teams.views.check_add_team_permission_view")
    def test_htmx_request_detection(self, mock_check_permission, mock_get_org_member, mock_get_org, 
                                   mock_form, mock_create_team, mock_get_teams):
        """Test HTMX request detection in views."""
        # Mock permission check
        mock_check_permission.return_value = None
        mock_get_org.return_value = self.organization
        mock_get_org_member.return_value = self.org_member
        mock_get_teams.return_value = []
        
        # Mock form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form.return_value = mock_form_instance
        
        # Mock team creation
        mock_team = TeamFactory.build()
        mock_create_team.return_value = mock_team
        
        # Regular request
        request = self._create_request(method='POST', data={})

        with patch("apps.teams.views.redirect") as mock_redirect:
            create_team_view(request, self.organization.organization_id)
            # Should redirect for regular request
            mock_redirect.assert_called_once()

        # HTMX request
        request = self._create_request(method='POST', data={}, htmx=True)

        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_response:
                mock_render_to_string.return_value = "<div>test</div>"
                mock_response_obj = Mock()
                mock_response.return_value = mock_response_obj
                
                create_team_view(request, self.organization.organization_id)
                # Should return HTMX response
                mock_response.assert_called_once()

    @patch("apps.teams.views.get_teams_by_organization_id")
    @patch("apps.teams.views.create_team_from_form")
    @patch("apps.teams.views.TeamForm")
    @patch("apps.teams.views.get_organization_by_id")
    @patch("apps.teams.views.get_orgMember_by_user_id_and_organization_id")
    @patch("apps.teams.views.check_add_team_permission_view")
    def test_htmx_response_headers(self, mock_check_permission, mock_get_org_member, mock_get_org, 
                                  mock_form, mock_create_team, mock_get_teams):
        """Test HTMX response headers are set correctly."""
        # Mock permission check
        mock_check_permission.return_value = None
        mock_get_org.return_value = self.organization
        mock_get_org_member.return_value = self.org_member
        mock_get_teams.return_value = []
        
        # Mock form
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form.return_value = mock_form_instance
        
        # Mock team creation
        mock_team = TeamFactory.build()
        mock_create_team.return_value = mock_team
        
        request = self._create_request(
            method='POST',
            data={
                "title": "Test Team",
            },
            htmx=True
        )

        with patch("apps.teams.views.render_to_string") as mock_render_to_string:
            with patch("apps.teams.views.HttpResponse") as mock_http_response:
                mock_render_to_string.return_value = "<div>test</div>"
                mock_response = Mock()
                mock_response.__setitem__ = Mock()  # Mock the headers assignment
                mock_http_response.return_value = mock_response
                
                create_team_view(request, self.organization.organization_id)
                
                # Verify response was created and headers were set
                mock_http_response.assert_called_once()
                mock_response.__setitem__.assert_called_with("HX-trigger", "success")
