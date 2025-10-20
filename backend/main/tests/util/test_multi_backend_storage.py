"""
Tests for multi-backend storage system.
"""
import os
from unittest.mock import patch

from django.test import TestCase

from main.util.io import (
    get_configured_backends,
    get_storage_backend_info,
)
from main.util.storage_factory import StorageFactory, StorageBackend


class MultiBackendStorageTestCase(TestCase):
    """Test multi-backend storage functionality."""

    def test_configured_storage_backend(self):
        """Test configured storage backend retrieval."""
        # This will test the configured backend from the storage factory
        from main.util.io import get_configured_storage_backend

        # The configured backend should be consistent regardless of URI
        backend = get_configured_storage_backend()
        self.assertIn(backend, ["s3", "azure_blob"])

    def test_storage_factory_configured_backend(self):
        """Test StorageFactory configured backend retrieval."""
        factory = StorageFactory()

        # Test configured backend retrieval
        backend = factory.get_configured_backend()
        self.assertIn(backend, [StorageBackend.S3, StorageBackend.AZURE_BLOB])

    def test_storage_factory_backend_selection(self):
        """Test StorageFactory backend selection logic."""
        factory = StorageFactory()

        # Test configured backend (ignores URI format)
        backend = factory.get_backend_for_uri("s3://bucket/path/file.csv")
        configured_backend = factory.get_configured_backend()
        self.assertEqual(backend, configured_backend)

        backend = factory.get_backend_for_uri("abfs://container@account.dfs.core.windows.net/path/file.csv")
        self.assertEqual(backend, configured_backend)

    @patch('main.util.storage_factory.get_config')
    def test_storage_factory_with_config(self, mock_get_config):
        """Test StorageFactory with configuration."""
        from main.config import StorageConfig, S3StorageConfig, AzureBlobStorageConfig, StorageBackendType

        # Mock config with S3 backend
        mock_config = type('MockConfig', (), {
            'storage': StorageConfig(
                backend=StorageBackendType.s3,
                s3=S3StorageConfig(
                    bucket_name="test-bucket",
                    region="us-west-2",
                    access_key_id="test-key",
                    secret_access_key="test-secret"
                ),
                azure_blob=None
            )
        })()
        mock_get_config.return_value = mock_config

        factory = StorageFactory()

        # Test configured backend
        backend = factory.get_configured_backend()
        self.assertEqual(backend, StorageBackend.S3)

        # Test S3 configuration
        s3_config = factory.configure_s3_backend()
        self.assertIn("key", s3_config)
        self.assertIn("secret", s3_config)
        self.assertIn("region", s3_config)

    def test_environment_variable_override(self):
        """Test that environment variables override config file settings."""
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'env-key',
            'AWS_SECRET_ACCESS_KEY': 'env-secret',
            'AWS_DEFAULT_REGION': 'us-west-1',
            'AZURE_STORAGE_ACCOUNT_NAME': 'env-account',
            'AZURE_STORAGE_ACCOUNT_KEY': 'env-key'
        }):
            factory = StorageFactory()

            # Test S3 environment variables
            s3_config = factory.configure_s3_backend()
            self.assertEqual(s3_config.get("key"), "env-key")
            self.assertEqual(s3_config.get("secret"), "env-secret")
            self.assertEqual(s3_config.get("region"), "us-west-1")

            # Test Azure environment variables
            azure_config = factory.configure_azure_backend()
            self.assertEqual(azure_config.get("account_name"), "env-account")
            self.assertEqual(azure_config.get("account_key"), "env-key")

    def test_backend_info(self):
        """Test backend information retrieval."""
        info = get_storage_backend_info("s3://bucket/path/file.csv")

        self.assertIn("backend", info)
        self.assertIn("uri", info)
        self.assertIn("config", info)
        self.assertIn("configured_backend", info)

        self.assertIn(info["backend"], ["s3", "azure_blob"])
        self.assertEqual(info["uri"], "s3://bucket/path/file.csv")
        self.assertTrue(info["configured_backend"])

    def test_configured_backends(self):
        """Test configured backends retrieval."""
        backends = get_configured_backends()

        # Should include at least the default backends
        self.assertIn("s3", backends)
        self.assertIn("azure_blob", backends)

    def test_fsspec_configuration(self):
        """Test fsspec configuration for different backends."""
        factory = StorageFactory()

        # Test S3 configuration
        s3_config = factory.get_fsspec_config(StorageBackend.S3)
        self.assertIsInstance(s3_config, dict)

        # Test Azure configuration
        azure_config = factory.get_fsspec_config(StorageBackend.AZURE_BLOB)
        self.assertIsInstance(azure_config, dict)

        # Test local configuration
        local_config = factory.get_fsspec_config(StorageBackend.LOCAL)
        self.assertIsInstance(local_config, dict)

    def test_storage_factory_singleton(self):
        """Test that StorageFactory is a singleton."""
        from main.util.storage_factory import get_storage_factory

        factory1 = get_storage_factory()
        factory2 = get_storage_factory()

        self.assertIs(factory1, factory2)

    def test_configured_backend_consistency(self):
        """Test that configured backend is consistent regardless of URI."""
        factory = StorageFactory()
        configured_backend = factory.get_configured_backend()

        # Test with different URI types - all should use the same configured backend
        test_cases = [
            "s3://bucket/file.csv",
            "abfs://container@account.dfs.core.windows.net/file.csv",
            "azure://container@account.blob.core.windows.net/file.csv",
            "/local/path/file.csv",
            "file:///local/path/file.csv",
        ]

        for uri in test_cases:
            with self.subTest(uri=uri):
                backend = factory.get_backend_for_uri(uri)
                self.assertEqual(backend, configured_backend)

    def test_configuration_priority(self):
        """Test configuration priority (env vars > config file > defaults)."""
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'env-key',
            'AWS_SECRET_ACCESS_KEY': 'env-secret'
        }):
            factory = StorageFactory()
            s3_config = factory.configure_s3_backend()

            # Environment variables should take priority
            self.assertEqual(s3_config.get("key"), "env-key")
            self.assertEqual(s3_config.get("secret"), "env-secret")

    def test_explicit_backend_configuration(self):
        """Test that only the configured backend is used."""
        factory = StorageFactory()
        configured_backend = factory.get_configured_backend()

        # Test that the configured backend is used regardless of URI format
        s3_uri = "s3://bucket/file.csv"
        azure_uri = "abfs://container@account.dfs.core.windows.net/file.csv"

        s3_backend = factory.get_backend_for_uri(s3_uri)
        azure_backend = factory.get_backend_for_uri(azure_uri)

        # Both should use the same configured backend
        self.assertEqual(s3_backend, configured_backend)
        self.assertEqual(azure_backend, configured_backend)
        self.assertEqual(s3_backend, azure_backend)
