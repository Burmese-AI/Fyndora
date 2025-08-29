"""
Integration tests for Core App workflows.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connection, models
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views.generic import TemplateView

from apps.core.models import SoftDeleteModel, baseModel
from apps.core.permissions import OrganizationPermissions, WorkspacePermissions
from apps.core.services.organizations import get_organization_by_id
from apps.core.utils import get_paginated_context, model_update, permission_denied_view
from apps.core.views.crud_base_views import (
    BaseListView,
)
from apps.core.views.mixins import (
    HtmxModalFormInvalidFormResponseMixin,
    HtmxOobResponseMixin,
    OrganizationRequiredMixin,
    WorkspaceRequiredMixin,
)
from apps.organizations.models import Organization
from tests.factories import (
    CustomUserFactory,
    OrganizationFactory,
    OrganizationMemberFactory,
    WorkspaceFactory,
)


# Test models for integration testing
class CoreIntegrationTestModel(baseModel, SoftDeleteModel):
    """Test model combining baseModel and SoftDeleteModel for integration testing."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        app_label = "core"


@pytest.mark.integration
class TestSoftDeleteModelIntegration(TestCase):
    """Integration tests for SoftDeleteModel workflows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create table for test model
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(CoreIntegrationTestModel)

    @classmethod
    def tearDownClass(cls):
        # Drop table for test model
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(CoreIntegrationTestModel)
        super().tearDownClass()

    @pytest.mark.django_db
    def test_soft_delete_workflow(self):
        """Test complete soft delete workflow."""
        # Create instance
        instance = CoreIntegrationTestModel.objects.create(
            name="Test Instance", description="Test Description"
        )
        instance_id = instance.id

        # Verify instance exists in default manager
        self.assertEqual(CoreIntegrationTestModel.objects.count(), 1)
        self.assertEqual(CoreIntegrationTestModel.all_objects.count(), 1)
        self.assertEqual(CoreIntegrationTestModel.deleted_objects.count(), 0)

        # Soft delete
        instance.delete()

        # Verify soft delete behavior
        self.assertIsNotNone(instance.deleted_at)
        self.assertEqual(
            CoreIntegrationTestModel.objects.count(), 0
        )  # Default manager excludes deleted
        self.assertEqual(
            CoreIntegrationTestModel.all_objects.count(), 1
        )  # All objects includes deleted
        self.assertEqual(
            CoreIntegrationTestModel.deleted_objects.count(), 1
        )  # Deleted objects only

        # Verify instance still exists in database
        deleted_instance = CoreIntegrationTestModel.all_objects.get(id=instance_id)
        self.assertIsNotNone(deleted_instance.deleted_at)

        # Test restore workflow
        deleted_instance.restore()

        # Verify restore behavior
        self.assertIsNone(deleted_instance.deleted_at)
        self.assertEqual(CoreIntegrationTestModel.objects.count(), 1)
        self.assertEqual(CoreIntegrationTestModel.all_objects.count(), 1)
        self.assertEqual(CoreIntegrationTestModel.deleted_objects.count(), 0)

    @pytest.mark.django_db
    def test_hard_delete_workflow(self):
        """Test hard delete workflow."""
        instance = CoreIntegrationTestModel.objects.create(name="Test Instance")
        instance_id = instance.id

        # Hard delete
        instance.hard_delete()

        # Verify complete removal
        self.assertEqual(CoreIntegrationTestModel.objects.count(), 0)
        self.assertEqual(CoreIntegrationTestModel.all_objects.count(), 0)
        self.assertEqual(CoreIntegrationTestModel.deleted_objects.count(), 0)

        # Verify instance doesn't exist
        with self.assertRaises(CoreIntegrationTestModel.DoesNotExist):
            CoreIntegrationTestModel.all_objects.get(id=instance_id)


@pytest.mark.integration
class TestOrganizationRequiredMixinIntegration(TestCase):
    """Integration tests for OrganizationRequiredMixin workflows."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )

        # Set organization owner
        self.organization.owner = self.org_member
        self.organization.save()

    @pytest.mark.django_db
    def test_organization_mixin_setup_workflow(self):
        """Test OrganizationRequiredMixin setup workflow."""

        class TestView(OrganizationRequiredMixin, TemplateView):
            def get_context_data(self, **kwargs):
                return super().get_context_data(**kwargs)

        view = TestView()
        request = self.factory.get("/")
        request.user = self.user

        # Setup view
        view.setup(request, organization_id=self.organization.organization_id)

        # Verify mixin setup
        self.assertEqual(view.organization, self.organization)
        self.assertEqual(view.org_member, self.org_member)
        self.assertTrue(view.is_org_admin)  # User is owner

        # Test context data
        context = view.get_context_data()
        self.assertEqual(context["organization"], self.organization)
        self.assertEqual(context["org_member"], self.org_member)
        self.assertTrue(context["is_org_admin"])

    @pytest.mark.django_db
    def test_organization_mixin_non_admin_workflow(self):
        """Test OrganizationRequiredMixin with non-admin user."""
        # Create another user who is not admin
        non_admin_user = CustomUserFactory()
        non_admin_member = OrganizationMemberFactory(
            user=non_admin_user, organization=self.organization
        )

        class TestView(OrganizationRequiredMixin, TemplateView):
            def get_context_data(self, **kwargs):
                return super().get_context_data(**kwargs)

        view = TestView()
        request = self.factory.get("/")
        request.user = non_admin_user

        view.setup(request, organization_id=self.organization.organization_id)

        # Verify non-admin setup
        self.assertEqual(view.organization, self.organization)
        self.assertEqual(view.org_member, non_admin_member)
        self.assertFalse(view.is_org_admin)  # Not owner

        context = view.get_context_data()
        self.assertFalse(context["is_org_admin"])


@pytest.mark.integration
class TestWorkspaceRequiredMixinIntegration(TestCase):
    """Integration tests for WorkspaceRequiredMixin workflows."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )
        self.workspace = WorkspaceFactory(
            organization=self.organization,
            workspace_admin=self.org_member,
            operations_reviewer=self.org_member,
        )

    @pytest.mark.django_db
    def test_workspace_mixin_setup_workflow(self):
        """Test WorkspaceRequiredMixin setup workflow."""

        class TestView(WorkspaceRequiredMixin, TemplateView):
            def get_context_data(self, **kwargs):
                return super().get_context_data(**kwargs)

        view = TestView()
        request = self.factory.get("/")
        request.user = self.user

        # Setup view
        view.setup(
            request,
            organization_id=self.organization.organization_id,
            workspace_id=self.workspace.workspace_id,
        )

        # Verify mixin setup
        self.assertEqual(view.organization, self.organization)
        self.assertEqual(view.workspace, self.workspace)
        self.assertEqual(view.org_member, self.org_member)
        self.assertTrue(view.is_workspace_admin)
        self.assertTrue(view.is_operation_reviewer)

        # Test context data with permissions
        context = view.get_context_data()
        self.assertEqual(context["workspace"], self.workspace)
        self.assertTrue(context["is_workspace_admin"])
        self.assertTrue(context["is_operation_reviewer"])
        self.assertIn("permissions", context)


@pytest.mark.integration
class TestHtmxMixinIntegration(TestCase):
    """Integration tests for HTMX mixin workflows."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_htmx_oob_response_mixin_workflow(self):
        """Test HtmxOobResponseMixin workflow."""

        class TestView(HtmxOobResponseMixin, TemplateView):
            def get_context_data(self, **kwargs):
                return super().get_context_data(**kwargs)

        view = TestView()

        # Test with HTMX request
        request = self.factory.get("/", HTTP_HX_REQUEST="true")
        request.htmx = True  # Add htmx attribute
        view.request = request

        context = view.get_context_data()
        self.assertTrue(context["is_oob"])

        # Test without HTMX request
        request = self.factory.get("/")
        request.htmx = False  # Add htmx attribute
        view.request = request

        context = view.get_context_data()
        self.assertNotIn("is_oob", context)

    @patch("apps.core.views.mixins.render_to_string")
    def test_htmx_modal_form_invalid_response_workflow(self, mock_render):
        """Test HtmxModalFormInvalidFormResponseMixin workflow."""
        mock_render.return_value = "<div>Mock HTML</div>"

        class TestView(HtmxModalFormInvalidFormResponseMixin, TemplateView):
            message_template_name = "test_message.html"
            modal_template_name = "test_modal.html"

            def get_context_data(self, **kwargs):
                return {"test": "context"}

        view = TestView()
        request = self.factory.post("/")

        # Add session and messages middleware
        middleware = SessionMiddleware(lambda req: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        setattr(request, "_messages", FallbackStorage(request))
        view.request = request

        # Mock form with errors
        mock_form = Mock()
        mock_form.errors = {"field": ["Error message"]}

        response = view.form_invalid(mock_form)

        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(mock_render.call_count, 2)  # Called for message and modal


@pytest.mark.integration
class TestCoreServiceIntegration(TestCase):
    """Integration tests for core service workflows."""

    @pytest.mark.django_db
    def test_get_organization_by_id_workflow(self):
        """Test get_organization_by_id service workflow."""
        organization = OrganizationFactory()

        # Test successful retrieval
        result = get_organization_by_id(organization.organization_id)
        self.assertEqual(result, organization)

        # Test non-existent organization
        result = get_organization_by_id("non-existent-id")
        self.assertIsNone(result)


@pytest.mark.integration
class TestCoreUtilsIntegration(TestCase):
    """Integration tests for core utility workflows."""

    @pytest.mark.django_db
    def test_model_update_integration_workflow(self):
        """Test model_update utility integration workflow."""
        organization = OrganizationFactory(title="Original Title")

        # Test successful update
        updated_org = model_update(
            instance=organization,
            data={"title": "Updated Title", "description": "New description"},
            update_fields=["title", "description"],
        )

        self.assertEqual(updated_org.title, "Updated Title")
        self.assertEqual(updated_org.description, "New description")

        # Verify database persistence
        updated_org.refresh_from_db()
        self.assertEqual(updated_org.title, "Updated Title")
        self.assertEqual(updated_org.description, "New description")

    def test_get_paginated_context_workflow(self):
        """Test get_paginated_context utility workflow."""
        # Create test queryset
        organizations = [OrganizationFactory() for _ in range(15)]
        queryset = type(organizations[0]).objects.all()

        # Test pagination
        context = get_paginated_context(
            queryset=queryset, object_name="organizations", page_size=10, page_no=1
        )

        # Verify pagination context
        self.assertIn("page_obj", context)
        self.assertIn("paginator", context)
        self.assertIn("organizations", context)
        self.assertIn("is_paginated", context)
        self.assertTrue(context["is_paginated"])
        self.assertEqual(len(context["organizations"]), 10)

    def test_permission_denied_view_workflow(self):
        """Test permission_denied_view utility workflow."""
        request = RequestFactory().get("/")

        # Add session and messages middleware
        middleware = SessionMiddleware(lambda req: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        setattr(request, "_messages", FallbackStorage(request))

        # Test regular request
        response = permission_denied_view(request, "Access denied")
        self.assertEqual(response.status_code, 302)  # Redirect

        # Test HTMX request
        request.META["HTTP_HX_REQUEST"] = "true"
        response = permission_denied_view(request, "Access denied")
        self.assertEqual(response.status_code, 302)  # HTMX redirect


@pytest.mark.integration
class TestBaseViewIntegration(TestCase):
    """Integration tests for base view workflows."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()

    def test_base_list_view_workflow(self):
        """Test BaseListView workflow."""

        class TestListView(BaseListView):
            model = Organization
            context_object_name = "organizations"
            template_name = "test_list.html"
            table_template_name = "test_table.html"

        view = TestListView()
        request = self.factory.get("/")
        request.user = self.user
        request.htmx = False  # Add htmx attribute

        view.setup(request)
        view.object_list = view.get_queryset()

        # Test regular request
        context = view.get_context_data()
        self.assertIn("organizations", context)
        self.assertIn("page_obj", context)

        # Test HTMX request
        request.htmx = True
        view.request = request

        with patch("apps.core.views.crud_base_views.render") as mock_render:
            mock_render.return_value = HttpResponse("Table HTML")
            view.render_to_response(context)
            mock_render.assert_called_once_with(request, "test_table.html", context)


@pytest.mark.integration
class TestPermissionIntegration(TestCase):
    """Integration tests for permission workflows."""

    @pytest.mark.django_db
    def test_workspace_permissions_integration(self):
        """Test workspace permissions integration."""
        user = CustomUserFactory()
        organization = OrganizationFactory()
        org_member = OrganizationMemberFactory(user=user, organization=organization)
        WorkspaceFactory(organization=organization, workspace_admin=org_member)

        # Test permission checking workflow
        permissions = [
            WorkspacePermissions.CHANGE_WORKSPACE,
            WorkspacePermissions.ADD_WORKSPACE_ENTRY,
            WorkspacePermissions.VIEW_WORKSPACE_ENTRY,
        ]

        for permission in permissions:
            # This would typically be tested with actual permission backend
            # For integration test, we verify the permission constants exist
            self.assertIsInstance(permission, str)
            self.assertTrue(len(permission) > 0)

    @pytest.mark.django_db
    def test_organization_permissions_integration(self):
        """Test organization permissions integration."""
        user = CustomUserFactory()
        organization = OrganizationFactory()
        OrganizationMemberFactory(user=user, organization=organization)

        # Test permission checking workflow
        permissions = [
            OrganizationPermissions.MANAGE_ORGANIZATION,
            OrganizationPermissions.ADD_WORKSPACE,
            OrganizationPermissions.INVITE_ORG_MEMBER,
        ]

        for permission in permissions:
            # This would typically be tested with actual permission backend
            # For integration test, we verify the permission constants exist
            self.assertIsInstance(permission, str)
            self.assertTrue(len(permission) > 0)


@pytest.mark.integration
class TestCoreWorkflowEndToEnd(TestCase):
    """End-to-end integration tests for core workflows."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUserFactory()
        self.organization = OrganizationFactory()
        self.org_member = OrganizationMemberFactory(
            user=self.user, organization=self.organization
        )
        self.workspace = WorkspaceFactory(
            organization=self.organization, workspace_admin=self.org_member
        )

    @pytest.mark.django_db
    def test_complete_organization_workspace_workflow(self):
        """Test complete organization and workspace workflow integration."""

        # Test organization service
        retrieved_org = get_organization_by_id(self.organization.organization_id)
        self.assertEqual(retrieved_org, self.organization)

        # Test model update workflow
        updated_org = model_update(
            instance=self.organization,
            data={"title": "Updated Organization"},
            update_fields=["title"],
        )
        self.assertEqual(updated_org.title, "Updated Organization")

        # Test mixin workflow
        class TestWorkspaceView(WorkspaceRequiredMixin, TemplateView):
            def get_context_data(self, **kwargs):
                return super().get_context_data(**kwargs)

        view = TestWorkspaceView()
        request = self.factory.get("/")
        request.user = self.user

        view.setup(
            request,
            organization_id=self.organization.organization_id,
            workspace_id=self.workspace.workspace_id,
        )

        context = view.get_context_data()

        # Verify complete workflow
        self.assertEqual(context["organization"], self.organization)
        self.assertEqual(context["workspace"], self.workspace)
        self.assertTrue(context["is_workspace_admin"])
        self.assertIn("permissions", context)
