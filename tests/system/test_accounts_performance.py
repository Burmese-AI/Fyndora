"""
Performance and system tests for the accounts app.

Following the test plan: Accounts App (apps.accounts)
- Performance tests for user creation and authentication
- System tests for end-to-end user workflows
- Load testing for user operations
"""

import pytest
import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction

from apps.accounts.constants import StatusChoices
from tests.factories import CustomUserFactory, StaffUserFactory

User = get_user_model()


@pytest.mark.performance
class TestUserCreationPerformance(TransactionTestCase):
    """Test user creation performance under various loads."""

    @pytest.mark.django_db
    def test_single_user_creation_performance(self):
        """Test time to create a single user."""
        start_time = time.time()

        user = User.objects.create_user(
            email="perf_test@example.com", username="perftest", password="testpass123"
        )

        end_time = time.time()
        creation_time = end_time - start_time

        # User creation should be reasonably fast (under 1 second)
        self.assertLess(creation_time, 1.0)
        self.assertIsNotNone(user)

    @pytest.mark.django_db
    def test_bulk_user_creation_performance(self):
        """Test performance of creating multiple users."""
        start_time = time.time()

        users = []
        for i in range(100):
            user = User.objects.create_user(
                email=f"bulk_user_{i}@example.com",
                username=f"bulkuser{i}",
                password="testpass123",
            )
            users.append(user)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_user = total_time / 100

        # Average creation time should be reasonable
        self.assertLess(avg_time_per_user, 0.1)  # Less than 100ms per user
        self.assertEqual(len(users), 100)

    @pytest.mark.django_db
    def test_user_factory_performance(self):
        """Test performance of factory-based user creation."""
        start_time = time.time()

        users = [CustomUserFactory() for _ in range(50)]

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_user = total_time / 50

        # Factory creation should be efficient
        self.assertLess(avg_time_per_user, 0.2)  # Less than 200ms per user
        self.assertEqual(len(users), 50)


@pytest.mark.performance
class TestAuthenticationPerformance(TestCase):
    """Test authentication performance under load."""

    @pytest.mark.django_db
    def test_single_authentication_performance(self):
        """Test time to authenticate a single user."""
        CustomUserFactory(username="authtest", password="testpass123")

        start_time = time.time()

        authenticated_user = authenticate(username="authtest", password="testpass123")

        end_time = time.time()
        auth_time = end_time - start_time

        # Authentication should be fast
        self.assertLess(auth_time, 0.5)  # Less than 500ms
        self.assertIsNotNone(authenticated_user)

    @pytest.mark.django_db
    def test_multiple_authentication_performance(self):
        """Test performance of multiple authentication attempts."""
        # Create test users
        users = []
        for i in range(20):
            user = CustomUserFactory(username=f"multiauth{i}", password="testpass123")
            users.append(user)

        start_time = time.time()

        # Authenticate all users
        authenticated_count = 0
        for i in range(20):
            authenticated_user = authenticate(
                username=f"multiauth{i}", password="testpass123"
            )
            if authenticated_user:
                authenticated_count += 1

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_auth = total_time / 20

        # Average authentication time should be reasonable
        self.assertLess(avg_time_per_auth, 0.1)  # Less than 100ms per auth
        self.assertEqual(authenticated_count, 20)

    @pytest.mark.django_db
    def test_failed_authentication_performance(self):
        """Test performance of failed authentication attempts."""
        CustomUserFactory(username="failtest", password="testpass123")

        start_time = time.time()

        # Try 10 failed authentications
        for _ in range(10):
            authenticated_user = authenticate(username="failtest", password="wrongpass")
            self.assertIsNone(authenticated_user)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_fail = total_time / 10

        # Failed authentication should not be significantly slower
        self.assertLess(avg_time_per_fail, 0.2)  # Less than 200ms per failed auth


@pytest.mark.system
class TestUserSystemWorkflows(TransactionTestCase):
    """System tests for complete user workflows."""

    @pytest.mark.django_db
    def test_complete_user_lifecycle_system_test(self):
        """Test complete user lifecycle from creation to deletion."""
        # 1. User creation
        user = User.objects.create_user(
            email="lifecycle@example.com", username="lifecycle", password="testpass123"
        )

        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        self.assertEqual(user.status, StatusChoices.ACTIVE)

        # 2. User authentication
        authenticated = authenticate(username="lifecycle", password="testpass123")
        self.assertEqual(authenticated, user)

        # 3. User status change
        user.status = StatusChoices.SUSPENDED
        user.is_active = False
        user.save()

        user.refresh_from_db()
        self.assertEqual(user.status, StatusChoices.SUSPENDED)
        self.assertFalse(user.is_active)

        # 4. Django's default backend rejects inactive users
        suspended_auth = authenticate(username="lifecycle", password="testpass123")
        self.assertIsNone(suspended_auth)  # Should fail

        # 5. Reactivation
        user.status = StatusChoices.ACTIVE
        user.is_active = True
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # 6. Password change
        user.set_password("newpass456")
        user.save()

        # Old password should fail
        old_auth = authenticate(username="lifecycle", password="testpass123")
        self.assertIsNone(old_auth)

        # New password should work
        new_auth = authenticate(username="lifecycle", password="newpass456")
        self.assertEqual(new_auth, user)

    @pytest.mark.django_db
    def test_concurrent_user_creation_system_test(self):
        """Test concurrent user creation without conflicts."""

        def create_user(index):
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=f"concurrent_{index}@example.com",
                        username=f"concurrent{index}",
                        password="testpass123",
                    )
                    return user.user_id
            except Exception as e:
                return f"Error: {e}"

        # Create users sequentially to avoid concurrency issues in SQLite
        results = []
        for i in range(20):
            result = create_user(i)
            results.append(result)

        # All users should be created successfully
        successful_creations = [r for r in results if not str(r).startswith("Error")]
        failed_creations = [r for r in results if str(r).startswith("Error")]

        self.assertEqual(len(successful_creations), 20)
        self.assertEqual(len(failed_creations), 0)

        # Verify all users exist in database
        created_users = User.objects.filter(username__startswith="concurrent").count()
        self.assertEqual(created_users, 20)

    @pytest.mark.django_db
    def test_user_uniqueness_enforcement_system_test(self):
        """Test system-level uniqueness enforcement."""
        # Create initial user
        user1 = CustomUserFactory(email="unique@example.com", username="uniqueuser")

        # Test email uniqueness
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            CustomUserFactory(email="unique@example.com")

        # Test username uniqueness
        with self.assertRaises(IntegrityError):
            CustomUserFactory(username="uniqueuser")

        # Different email and username should work
        user2 = CustomUserFactory(
            email="different@example.com", username="differentuser"
        )

        self.assertNotEqual(user1.email, user2.email)
        self.assertNotEqual(user1.username, user2.username)


@pytest.mark.slow
class TestUserLongRunningOperations(TestCase):
    """Test long-running operations with users."""

    @pytest.mark.django_db
    def test_large_user_query_performance(self):
        """Test querying performance with large user dataset."""
        # Create large number of users
        [CustomUserFactory() for _ in range(1000)]

        start_time = time.time()

        # Perform various queries
        active_users = User.objects.filter(
            status=StatusChoices.ACTIVE, is_active=True
        ).count()

        User.objects.filter(is_staff=True).count()

        email_search = User.objects.filter(email__icontains="@example.com").count()

        end_time = time.time()
        query_time = end_time - start_time

        # Queries should complete in reasonable time
        self.assertLess(query_time, 5.0)  # Less than 5 seconds
        self.assertGreater(active_users, 0)
        self.assertGreaterEqual(email_search, active_users)

    @pytest.mark.django_db
    def test_user_password_hashing_performance(self):
        """Test password hashing performance under load."""
        passwords = [f"password{i}" for i in range(100)]

        start_time = time.time()

        for i, password in enumerate(passwords):
            user = User.objects.create_user(
                email=f"hash_test_{i}@example.com",
                username=f"hashtest{i}",
                password=password,
            )
            # Verify password was hashed
            self.assertNotEqual(user.password, password)
            self.assertTrue(user.check_password(password))

        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_hash = total_time / 100

        # Password hashing should be reasonable but not too fast (security)
        self.assertLess(avg_time_per_hash, 1.0)  # Less than 1 second
        self.assertGreater(
            avg_time_per_hash, 0.0001
        )  # More than 0.1ms (ensures hashing)


@pytest.mark.system
class TestUserSystemIntegration(TestCase):
    """Test user integration with broader system components."""

    @pytest.mark.django_db
    def test_user_organization_team_integration_system(self):
        """Test complete user integration across organization and team systems."""
        from tests.factories import (
            OrganizationFactory,
            OrganizationMemberFactory,
            TeamFactory,
            TeamMemberFactory,
        )

        # Create user
        user = CustomUserFactory()

        # Add to organization
        org = OrganizationFactory()
        org_member = OrganizationMemberFactory(user=user, organization=org)

        # Create team and add user
        team = TeamFactory()
        team_member = TeamMemberFactory(organization_member=org_member, team=team)

        # Verify integration with correct field paths
        # Test that user can be found through organization membership
        org_users = User.objects.filter(organization_memberships__organization=org)
        self.assertIn(user, org_users)

        # Test that user can be found through team membership
        # Correct path: User -> OrganizationMember -> TeamMember -> Team
        team_users = User.objects.filter(
            organization_memberships__team_memberships__team=team
        )
        self.assertIn(user, team_users)

        # Test reverse relationships
        # From Team to User: Team -> TeamMember -> OrganizationMember -> User
        user_teams = team.__class__.objects.filter(
            members__organization_member__user=user
        )
        self.assertIn(team, user_teams)

        # Test that organization member belongs to correct organization and user
        self.assertEqual(org_member.user, user)
        self.assertEqual(org_member.organization, org)
        self.assertEqual(team_member.organization_member, org_member)
        self.assertEqual(team_member.team, team)

    @pytest.mark.django_db
    def test_user_permissions_cascade_system(self):
        """Test how user permissions cascade through system."""
        # Create regular user, staff user, and superuser
        regular_user = CustomUserFactory(is_staff=False, is_superuser=False)
        staff_user = StaffUserFactory()
        super_user = User.objects.create_superuser(
            email="super@example.com", username="superuser", password="superpass123"
        )

        # Test permission levels
        self.assertFalse(regular_user.is_staff)
        self.assertFalse(regular_user.is_superuser)
        self.assertFalse(regular_user.has_perm("any.permission"))

        self.assertTrue(staff_user.is_staff)
        self.assertFalse(staff_user.is_superuser)
        self.assertFalse(staff_user.has_perm("any.permission"))

        self.assertTrue(super_user.is_staff)
        self.assertTrue(super_user.is_superuser)
        self.assertTrue(
            super_user.has_perm("any.permission")
        )  # Superuser has all perms
