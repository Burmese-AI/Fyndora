"""Unit tests for AuditConfig validation and configuration management.

Following the test plan: AuditLog App (apps.auditlog)
- Configuration validation tests
- Configuration boundary tests
- Configuration consistency tests
"""

from unittest.mock import patch

import pytest
from django.test import TestCase

from apps.auditlog.config import AuditConfig
from apps.auditlog.constants import AuditActionType


@pytest.mark.unit
class TestAuditConfigValidation(TestCase):
    """Test AuditConfig validation and settings."""

    def test_max_metadata_size_validation(self):
        """Test MAX_METADATA_SIZE configuration validation."""
        # Test current value is valid
        self.assertIsInstance(AuditConfig.MAX_METADATA_SIZE, int)
        self.assertGreater(AuditConfig.MAX_METADATA_SIZE, 0)

        # Test reasonable bounds
        self.assertGreaterEqual(AuditConfig.MAX_METADATA_SIZE, 1000)  # At least 1KB
        self.assertLessEqual(AuditConfig.MAX_METADATA_SIZE, 1000000)  # At most 1MB

        # Test it's the expected value
        self.assertEqual(AuditConfig.MAX_METADATA_SIZE, 10000)

    def test_bulk_operation_threshold_validation(self):
        """Test BULK_OPERATION_THRESHOLD configuration validation."""
        # Test current value is valid
        self.assertIsInstance(AuditConfig.BULK_OPERATION_THRESHOLD, int)
        self.assertGreater(AuditConfig.BULK_OPERATION_THRESHOLD, 0)

        # Test reasonable bounds
        self.assertGreaterEqual(AuditConfig.BULK_OPERATION_THRESHOLD, 5)
        self.assertLessEqual(AuditConfig.BULK_OPERATION_THRESHOLD, 10000)

        # Test it's the expected value
        self.assertEqual(AuditConfig.BULK_OPERATION_THRESHOLD, 50)

    def test_bulk_sample_size_validation(self):
        """Test BULK_SAMPLE_SIZE configuration validation."""
        # Test current value is valid
        self.assertIsInstance(AuditConfig.BULK_SAMPLE_SIZE, int)
        self.assertGreater(AuditConfig.BULK_SAMPLE_SIZE, 0)

        # Test it's less than threshold
        self.assertLess(
            AuditConfig.BULK_SAMPLE_SIZE, AuditConfig.BULK_OPERATION_THRESHOLD
        )

        # Test it's the expected value
        self.assertEqual(AuditConfig.BULK_SAMPLE_SIZE, 10)

    def test_default_retention_days_validation(self):
        """Test DEFAULT_RETENTION_DAYS configuration validation."""
        # Test current value is valid
        self.assertIsInstance(AuditConfig.DEFAULT_RETENTION_DAYS, int)
        self.assertGreater(AuditConfig.DEFAULT_RETENTION_DAYS, 0)

        # Test reasonable bounds (at least 30 days, at most 10 years)
        self.assertGreaterEqual(AuditConfig.DEFAULT_RETENTION_DAYS, 30)
        self.assertLessEqual(AuditConfig.DEFAULT_RETENTION_DAYS, 3650)

        # Test it's the expected value
        self.assertEqual(AuditConfig.DEFAULT_RETENTION_DAYS, 90)

    def test_retention_days_constants_validation(self):
        """Test retention days constants validation."""
        # Test DEFAULT_RETENTION_DAYS
        self.assertIsInstance(AuditConfig.DEFAULT_RETENTION_DAYS, int)
        self.assertGreater(AuditConfig.DEFAULT_RETENTION_DAYS, 0)

        # Test AUTHENTICATION_RETENTION_DAYS if it exists
        if hasattr(AuditConfig, "AUTHENTICATION_RETENTION_DAYS"):
            self.assertIsInstance(AuditConfig.AUTHENTICATION_RETENTION_DAYS, int)
            self.assertGreater(AuditConfig.AUTHENTICATION_RETENTION_DAYS, 0)

        # Test CRITICAL_RETENTION_DAYS if it exists
        if hasattr(AuditConfig, "CRITICAL_RETENTION_DAYS"):
            self.assertIsInstance(AuditConfig.CRITICAL_RETENTION_DAYS, int)
            self.assertGreater(AuditConfig.CRITICAL_RETENTION_DAYS, 0)

    def test_sensitive_fields_validation(self):
        """Test SENSITIVE_FIELDS configuration validation."""
        # Test it's a set
        self.assertIsInstance(AuditConfig.SENSITIVE_FIELDS, set)

        # Test all items are strings
        for field in AuditConfig.SENSITIVE_FIELDS:
            with self.subTest(field=field):
                self.assertIsInstance(field, str)
                self.assertGreater(len(field), 0)  # Non-empty strings

        # Test that sensitive fields set is reasonable
        expected_sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "hash",
            "salt",
            "credit_card",
            "ssn",
            "social_security",
            "bank_account",
        }
        self.assertEqual(AuditConfig.SENSITIVE_FIELDS, expected_sensitive_fields)

    def test_boolean_configurations(self):
        """Test boolean configuration values."""
        boolean_configs = [
            "ENABLE_AUTOMATIC_LOGGING",
            "LOG_FIELD_CHANGES",
            "ENABLE_BULK_OPERATIONS",
            "ENABLE_METADATA_SEARCH",
        ]

        for config_name in boolean_configs:
            with self.subTest(config=config_name):
                if hasattr(AuditConfig, config_name):
                    value = getattr(AuditConfig, config_name)
                    self.assertIsInstance(value, bool)


@pytest.mark.unit
class TestAuditConfigMethods(TestCase):
    """Test AuditConfig class methods."""

    def test_get_retention_days_for_action_valid_actions(self):
        """Test get_retention_days_for_action with valid action types."""
        # Test with known action types
        test_actions = [
            AuditActionType.ENTRY_CREATED,
            AuditActionType.LOGIN_SUCCESS,
            AuditActionType.ORGANIZATION_CREATED,
            AuditActionType.UNAUTHORIZED_ACCESS_ATTEMPT,
        ]

        for action in test_actions:
            with self.subTest(action=action):
                days = AuditConfig.get_retention_days_for_action(action)
                self.assertIsInstance(days, int)
                self.assertGreater(days, 0)

    def test_get_retention_days_for_action_invalid_actions(self):
        """Test get_retention_days_for_action with invalid action types."""
        invalid_actions = [None, "", "invalid_action", 123, [], {}]

        for action in invalid_actions:
            with self.subTest(action=action):
                days = AuditConfig.get_retention_days_for_action(action)
                self.assertEqual(days, AuditConfig.DEFAULT_RETENTION_DAYS)

    def test_get_retention_days_for_action_different_types(self):
        """Test that different action types return appropriate retention periods."""
        # Test authentication action
        auth_action = AuditActionType.LOGIN_SUCCESS
        auth_days = AuditConfig.get_retention_days_for_action(auth_action)
        self.assertIsInstance(auth_days, int)
        self.assertGreater(auth_days, 0)

        # Test regular action
        regular_action = AuditActionType.ENTRY_CREATED
        regular_days = AuditConfig.get_retention_days_for_action(regular_action)
        self.assertIsInstance(regular_days, int)
        self.assertGreater(regular_days, 0)

    def test_is_sensitive_field_known_sensitive(self):
        """Test is_sensitive_field with known sensitive field names."""
        sensitive_fields = [
            "password",
            "token",
            "secret",
            "user_key",
            "api_key",
            "access_token",
            "refresh_token",
            "private_key",
            "auth_token",
        ]

        for field in sensitive_fields:
            with self.subTest(field=field):
                self.assertTrue(AuditConfig.is_sensitive_field(field))

    def test_is_sensitive_field_case_insensitive(self):
        """Test is_sensitive_field is case insensitive."""
        test_cases = [
            ("password", "PASSWORD", "Password", "pAsSwOrD"),
            ("token", "TOKEN", "Token", "tOkEn"),
            ("secret", "SECRET", "Secret", "sEcReT"),
        ]

        for case_variants in test_cases:
            for variant in case_variants:
                with self.subTest(field=variant):
                    self.assertTrue(AuditConfig.is_sensitive_field(variant))

    def test_is_sensitive_field_non_sensitive(self):
        """Test is_sensitive_field with non-sensitive field names."""
        non_sensitive_fields = [
            "name",
            "email",
            "description",
            "title",
            "id",
            "created_at",
            "updated_at",
            "status",
            "type",
            "category",
        ]

        for field in non_sensitive_fields:
            with self.subTest(field=field):
                self.assertFalse(AuditConfig.is_sensitive_field(field))

    def test_is_sensitive_field_edge_cases(self):
        """Test is_sensitive_field with edge cases."""
        edge_cases = [None, "", 123, [], {}, True, False]

        for case in edge_cases:
            with self.subTest(case=case):
                # Should handle gracefully - either return False or raise appropriate exception
                try:
                    result = AuditConfig.is_sensitive_field(case)
                    self.assertFalse(result)
                except (AttributeError, TypeError):
                    # If implementation doesn't handle non-strings, that's acceptable
                    pass


@pytest.mark.unit
class TestAuditConfigBoundaryConditions(TestCase):
    """Test AuditConfig boundary conditions and edge cases."""

    def test_metadata_size_boundary_conditions(self):
        """Test metadata size configuration boundary conditions."""
        # Test that MAX_METADATA_SIZE is not too small to be useful
        min_useful_size = 100  # At least 100 bytes for basic metadata
        self.assertGreaterEqual(AuditConfig.MAX_METADATA_SIZE, min_useful_size)

        # Test that it's not unreasonably large (memory concerns)
        max_reasonable_size = 10 * 1024 * 1024  # 10MB
        self.assertLessEqual(AuditConfig.MAX_METADATA_SIZE, max_reasonable_size)

    def test_bulk_operation_boundary_conditions(self):
        """Test bulk operation configuration boundary conditions."""
        # BULK_SAMPLE_SIZE should be meaningful but not too large
        self.assertGreaterEqual(AuditConfig.BULK_SAMPLE_SIZE, 1)
        self.assertLessEqual(AuditConfig.BULK_SAMPLE_SIZE, 100)

        # BULK_OPERATION_THRESHOLD should be reasonable
        self.assertGreaterEqual(AuditConfig.BULK_OPERATION_THRESHOLD, 10)
        self.assertLessEqual(AuditConfig.BULK_OPERATION_THRESHOLD, 10000)

        # Sample size should be significantly smaller than threshold
        ratio = AuditConfig.BULK_OPERATION_THRESHOLD / AuditConfig.BULK_SAMPLE_SIZE
        self.assertGreaterEqual(ratio, 2)  # At least 2:1 ratio

    def test_retention_days_boundary_conditions(self):
        """Test retention days boundary conditions."""
        # Test default retention period
        self.assertGreaterEqual(
            AuditConfig.DEFAULT_RETENTION_DAYS, 7
        )  # At least 1 week
        self.assertLessEqual(
            AuditConfig.DEFAULT_RETENTION_DAYS, 7300
        )  # At most 20 years

        # Test other retention periods if they exist
        if hasattr(AuditConfig, "AUTHENTICATION_RETENTION_DAYS"):
            self.assertGreaterEqual(AuditConfig.AUTHENTICATION_RETENTION_DAYS, 7)
            self.assertLessEqual(AuditConfig.AUTHENTICATION_RETENTION_DAYS, 7300)

        if hasattr(AuditConfig, "CRITICAL_RETENTION_DAYS"):
            self.assertGreaterEqual(AuditConfig.CRITICAL_RETENTION_DAYS, 7)
            self.assertLessEqual(AuditConfig.CRITICAL_RETENTION_DAYS, 7300)


@pytest.mark.unit
class TestAuditConfigConsistency(TestCase):
    """Test AuditConfig internal consistency."""

    def test_retention_days_consistency(self):
        """Test that retention day values are consistent and logical."""
        # All retention values should be positive
        self.assertGreater(AuditConfig.DEFAULT_RETENTION_DAYS, 0)
        self.assertGreater(AuditConfig.AUTHENTICATION_RETENTION_DAYS, 0)
        self.assertGreater(AuditConfig.CRITICAL_RETENTION_DAYS, 0)

        # Critical retention should be >= default retention
        self.assertGreaterEqual(
            AuditConfig.CRITICAL_RETENTION_DAYS, AuditConfig.DEFAULT_RETENTION_DAYS
        )

    def test_sensitive_fields_consistency(self):
        """Test that sensitive fields configuration is consistent."""
        # Should contain common sensitive field patterns
        sensitive_lower = [field.lower() for field in AuditConfig.SENSITIVE_FIELDS]

        expected_patterns = ["password", "token", "secret", "key"]
        for pattern in expected_patterns:
            with self.subTest(pattern=pattern):
                # Should have at least one field containing this pattern
                has_pattern = any(pattern in field for field in sensitive_lower)
                self.assertTrue(has_pattern, f"No sensitive field contains '{pattern}'")

    def test_configuration_types_consistency(self):
        """Test that all configuration values have consistent types."""
        # Integer configurations
        int_configs = [
            "MAX_METADATA_SIZE",
            "BULK_OPERATION_THRESHOLD",
            "BULK_SAMPLE_SIZE",
            "DEFAULT_RETENTION_DAYS",
        ]

        for config_name in int_configs:
            with self.subTest(config=config_name):
                if hasattr(AuditConfig, config_name):
                    value = getattr(AuditConfig, config_name)
                    self.assertIsInstance(value, int)
                    self.assertGreater(value, 0)


@pytest.mark.unit
class TestAuditConfigWithMocking(TestCase):
    """Test AuditConfig behavior with mocked values."""

    @patch("apps.auditlog.config.AuditConfig.MAX_METADATA_SIZE", 100)
    def test_small_metadata_size_handling(self):
        """Test behavior with very small MAX_METADATA_SIZE."""
        from apps.auditlog.utils import truncate_metadata

        # Test that truncation still works with small limits
        large_metadata = {"key": "x" * 200}
        result = truncate_metadata(large_metadata)

        self.assertIsInstance(result, dict)

        # Result should be smaller than original
        import json

        result_size = len(json.dumps(result))
        original_size = len(json.dumps(large_metadata))
        self.assertLess(result_size, original_size)

    @patch("apps.auditlog.config.AuditConfig.BULK_OPERATION_THRESHOLD", 5)
    @patch("apps.auditlog.config.AuditConfig.BULK_SAMPLE_SIZE", 2)
    def test_small_bulk_thresholds(self):
        """Test behavior with very small bulk operation thresholds."""
        # Verify the mocked values are applied
        self.assertEqual(AuditConfig.BULK_OPERATION_THRESHOLD, 5)
        self.assertEqual(AuditConfig.BULK_SAMPLE_SIZE, 2)

        # Sample size should still be less than threshold
        self.assertLess(
            AuditConfig.BULK_SAMPLE_SIZE, AuditConfig.BULK_OPERATION_THRESHOLD
        )

    @patch("apps.auditlog.config.AuditConfig.DEFAULT_RETENTION_DAYS", 1)
    def test_minimal_retention_days(self):
        """Test behavior with minimal retention days."""
        # Test that get_retention_days_for_action still works
        days = AuditConfig.get_retention_days_for_action("unknown_action")
        self.assertEqual(days, 1)

        # Test with known action that falls back to default
        days = AuditConfig.get_retention_days_for_action("non_existent_action")
        self.assertEqual(days, 1)


@pytest.mark.unit
class TestAuditConfigIntegration(TestCase):
    """Test AuditConfig integration with other components."""

    def test_config_used_by_truncate_metadata(self):
        """Test that truncate_metadata uses AuditConfig.MAX_METADATA_SIZE."""
        import json

        from apps.auditlog.utils import truncate_metadata

        # Create metadata just under the limit
        safe_size = AuditConfig.MAX_METADATA_SIZE - 100
        safe_metadata = {"data": "x" * safe_size}

        result = truncate_metadata(safe_metadata)
        self.assertFalse(result.get("_truncated", False))

        # Create metadata over the limit
        large_size = AuditConfig.MAX_METADATA_SIZE + 1000
        large_metadata = {"data": "x" * large_size}

        result = truncate_metadata(large_metadata)
        self.assertTrue(len(json.dumps(result)) <= AuditConfig.MAX_METADATA_SIZE)

    def test_config_used_by_retention_cleanup(self):
        """Test that retention configuration is used by cleanup processes."""
        # Test that get_retention_days_for_action returns valid values
        test_actions = [
            AuditActionType.ENTRY_CREATED,
            AuditActionType.LOGIN_SUCCESS,
            AuditActionType.ORGANIZATION_CREATED,
        ]

        for action_type in test_actions:
            with self.subTest(action_type=action_type):
                actual_days = AuditConfig.get_retention_days_for_action(action_type)
                self.assertIsInstance(actual_days, int)
                self.assertGreater(actual_days, 0)

    def test_config_used_by_sensitive_field_detection(self):
        """Test that sensitive field configuration is used correctly."""
        # Test that configured sensitive fields are detected
        for field in AuditConfig.SENSITIVE_FIELDS:
            with self.subTest(field=field):
                self.assertTrue(AuditConfig.is_sensitive_field(field))

                # Test case variations
                self.assertTrue(AuditConfig.is_sensitive_field(field.upper()))
                self.assertTrue(AuditConfig.is_sensitive_field(field.lower()))
                self.assertTrue(AuditConfig.is_sensitive_field(field.capitalize()))
