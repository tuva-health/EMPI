"""
Tests for storage integration (S3, LocalStack, Azure Blob Storage).
"""
import os
import tempfile
from unittest.mock import patch

from django.test import TestCase

from main.util.io import open_sink, open_source


class StorageIntegrationTestCase(TestCase):
    """Test storage integration with multiple providers."""

    def test_s3_uri_detection(self):
        """Test S3 URI detection."""
        from main.util.io import _is_s3_uri, _is_azure_blob_uri

        # S3 URIs
        self.assertTrue(_is_s3_uri("s3://bucket/path/file.csv"))
        self.assertTrue(_is_s3_uri("s3://my-bucket/data/records.csv"))

        # Non-S3 URIs
        self.assertFalse(_is_s3_uri("abfs://container@account.dfs.core.windows.net/path"))
        self.assertFalse(_is_s3_uri("azure://container@account.blob.core.windows.net/path"))
        self.assertFalse(_is_s3_uri("file:///local/path"))

    def test_azure_blob_uri_detection(self):
        """Test Azure Blob Storage URI detection."""
        from main.util.io import _is_azure_blob_uri

        # Azure Blob URIs
        self.assertTrue(_is_azure_blob_uri("abfs://container@account.dfs.core.windows.net/path"))
        self.assertTrue(_is_azure_blob_uri("azure://container@account.blob.core.windows.net/path"))

        # Non-Azure URIs
        self.assertFalse(_is_azure_blob_uri("s3://bucket/path/file.csv"))
        self.assertFalse(_is_azure_blob_uri("file:///local/path"))

    def test_uri_validation_s3(self):
        """Test S3 URI validation."""
        from main.views.person_records import StorageURIValidatorMixin

        validator = StorageURIValidatorMixin()

        # Valid S3 URIs
        self.assertEqual(
            validator.validate_s3_uri("s3://bucket/path/file.csv"),
            "s3://bucket/path/file.csv"
        )
        self.assertEqual(
            validator.validate_s3_uri("s3://my-bucket-123/data/records.csv"),
            "s3://my-bucket-123/data/records.csv"
        )

        # Invalid S3 URIs
        with self.assertRaises(Exception):
            validator.validate_s3_uri("invalid-uri")

        with self.assertRaises(Exception):
            validator.validate_s3_uri("s3://bucket")  # No path

    def test_uri_validation_azure_blob(self):
        """Test Azure Blob Storage URI validation."""
        from main.views.person_records import StorageURIValidatorMixin

        validator = StorageURIValidatorMixin()

        # Valid Azure Blob URIs
        self.assertEqual(
            validator.validate_azure_blob_uri("abfs://container@account.dfs.core.windows.net/path/file.csv"),
            "abfs://container@account.dfs.core.windows.net/path/file.csv"
        )
        self.assertEqual(
            validator.validate_azure_blob_uri("azure://container@account.blob.core.windows.net/path/file.csv"),
            "azure://container@account.blob.core.windows.net/path/file.csv"
        )

        # Invalid Azure Blob URIs
        with self.assertRaises(Exception):
            validator.validate_azure_blob_uri("abfs://invalid-uri")

        with self.assertRaises(Exception):
            validator.validate_azure_blob_uri("azure://container@account.blob.core.windows.net")  # No path

    def test_storage_uri_validation(self):
        """Test generic storage URI validation."""
        from main.views.person_records import StorageURIValidatorMixin

        validator = StorageURIValidatorMixin()

        # Valid storage URIs
        self.assertEqual(
            validator.validate_storage_uri("s3://bucket/path/file.csv"),
            "s3://bucket/path/file.csv"
        )
        self.assertEqual(
            validator.validate_storage_uri("abfs://container@account.dfs.core.windows.net/path/file.csv"),
            "abfs://container@account.dfs.core.windows.net/path/file.csv"
        )
        self.assertEqual(
            validator.validate_storage_uri("azure://container@account.blob.core.windows.net/path/file.csv"),
            "azure://container@account.blob.core.windows.net/path/file.csv"
        )

        # Invalid storage URIs
        with self.assertRaises(Exception):
            validator.validate_storage_uri("invalid-uri")

        with self.assertRaises(Exception):
            validator.validate_storage_uri("file:///local/path")

    @patch('main.util.io.fsspec.open')
    def test_azure_blob_configuration(self, mock_fsspec_open):
        """Test Azure Blob Storage configuration."""
        # Mock the fsspec.open to simulate Azure Blob Storage
        mock_file = tempfile.NamedTemporaryFile()
        mock_fsspec_open.return_value.__enter__.return_value = mock_file

        # Test Azure Blob URI
        azure_uri = "abfs://container@account.dfs.core.windows.net/path/file.csv"

        with open_source(azure_uri) as f:
            self.assertIsNotNone(f)

        # Verify fsspec.open was called with the Azure URI
        mock_fsspec_open.assert_called_with(azure_uri, mode="rb")

    @patch('main.util.io.fsspec.open')
    def test_s3_uri_handling(self, mock_fsspec_open):
        """Test S3 URI handling remains unchanged."""
        # Mock the fsspec.open to simulate S3
        mock_file = tempfile.NamedTemporaryFile()
        mock_fsspec_open.return_value.__enter__.return_value = mock_file

        # Test S3 URI
        s3_uri = "s3://bucket/path/file.csv"

        with open_source(s3_uri) as f:
            self.assertIsNotNone(f)

        # Verify fsspec.open was called with the S3 URI
        mock_fsspec_open.assert_called_with(s3_uri, mode="rb")

    def test_environment_variable_handling(self):
        """Test Azure environment variable handling."""
        # Test with Azure environment variables
        with patch.dict(os.environ, {
            'AZURE_STORAGE_ACCOUNT_NAME': 'test-account',
            'AZURE_STORAGE_ACCOUNT_KEY': 'test-key'
        }):
            from main.util.io import _configure_fsspec_for_azure
            # Should not raise an exception
            _configure_fsspec_for_azure()

    def test_azure_identity_fallback(self):
        """Test Azure Identity fallback when no explicit credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('main.util.io.DefaultAzureCredential') as mock_credential:
                from main.util.io import _configure_fsspec_for_azure
                _configure_fsspec_for_azure()
                # Should attempt to use DefaultAzureCredential
                mock_credential.assert_called_once()

    def test_import_error_handling(self):
        """Test graceful handling when Azure libraries are not available."""
        with patch('main.util.io.adlfs', side_effect=ImportError):
            from main.util.io import _configure_fsspec_for_azure
            # Should not raise an exception
            _configure_fsspec_for_azure()

    def test_serializer_validation(self):
        """Test serializer validation for multiple storage options."""
        from main.views.person_records import ImportPersonRecordsRequest

        # Test valid S3 URI
        data = {
            's3_uri': 's3://bucket/path/file.csv',
            'config_id': 'Config_1'
        }
        serializer = ImportPersonRecordsRequest(data=data)
        self.assertTrue(serializer.is_valid())

        # Test valid Azure Blob URI
        data = {
            'azure_blob_uri': 'abfs://container@account.dfs.core.windows.net/path/file.csv',
            'config_id': 'Config_1'
        }
        serializer = ImportPersonRecordsRequest(data=data)
        self.assertTrue(serializer.is_valid())

        # Test valid generic storage URI
        data = {
            'storage_uri': 's3://bucket/path/file.csv',
            'config_id': 'Config_1'
        }
        serializer = ImportPersonRecordsRequest(data=data)
        self.assertTrue(serializer.is_valid())

        # Test multiple storage options (should fail)
        data = {
            's3_uri': 's3://bucket/path/file.csv',
            'azure_blob_uri': 'abfs://container@account.dfs.core.windows.net/path/file.csv',
            'config_id': 'Config_1'
        }
        serializer = ImportPersonRecordsRequest(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Provide only one storage option', str(serializer.errors))

        # Test no storage options (should fail)
        data = {
            'config_id': 'Config_1'
        }
        serializer = ImportPersonRecordsRequest(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Must provide one of', str(serializer.errors))
