"""
Storage factory for multi-backend support (S3, Azure Blob Storage, etc.).
"""
import os
from enum import Enum
from typing import Optional, Union
from urllib.parse import urlparse

import fsspec  # type: ignore[import-untyped]
from django.core.files.uploadedfile import UploadedFile

from main.config import StorageBackendType, get_config


class StorageBackend(Enum):
    """Supported storage backends."""
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    LOCAL = "local"


class StorageFactory:
    """Factory for creating and managing storage backends."""

    def __init__(self):
        self.config = get_config()
        self.storage_config = self.config.storage

    def get_configured_backend(self) -> StorageBackend:
        """Get the configured storage backend."""
        if not self.storage_config:
            raise ValueError("Storage configuration is required")

        if self.storage_config.backend.value == "s3":
            return StorageBackend.S3
        elif self.storage_config.backend.value == "azure_blob":
            return StorageBackend.AZURE_BLOB
        else:
            raise ValueError(f"Unsupported storage backend: {self.storage_config.backend}")

    def get_backend_for_uri(self, uri: str) -> StorageBackend:
        """Get the configured backend (ignores URI format)."""
        return self.get_configured_backend()

    def configure_s3_backend(self) -> dict:
        """Configure S3 backend with credentials and settings."""
        config = {}

        # Use environment variables first (existing behavior)
        if os.environ.get("AWS_ACCESS_KEY_ID"):
            config["key"] = os.environ.get("AWS_ACCESS_KEY_ID")
        if os.environ.get("AWS_SECRET_ACCESS_KEY"):
            config["secret"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
        if os.environ.get("AWS_DEFAULT_REGION"):
            config["region"] = os.environ.get("AWS_DEFAULT_REGION")
        if os.environ.get("AWS_ENDPOINT_URL"):
            config["endpoint_url"] = os.environ.get("AWS_ENDPOINT_URL")

        # Override with config file settings if available
        if self.storage_config and self.storage_config.s3:
            s3_config = self.storage_config.s3
            if s3_config.access_key_id:
                config["key"] = s3_config.access_key_id
            if s3_config.secret_access_key:
                config["secret"] = s3_config.secret_access_key
            if s3_config.region:
                config["region"] = s3_config.region
            if s3_config.endpoint_url:
                config["endpoint_url"] = s3_config.endpoint_url

        return config

    def configure_azure_backend(self) -> dict:
        """Configure Azure Blob Storage backend with credentials and settings."""
        config = {}

        # Use environment variables first
        if os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"):
            config["account_name"] = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
        if os.environ.get("AZURE_STORAGE_ACCOUNT_KEY"):
            config["account_key"] = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
        if os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
            config["connection_string"] = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

        # Override with config file settings if available
        if self.storage_config and self.storage_config.azure_blob:
            azure_config = self.storage_config.azure_blob
            if azure_config.account_name:
                config["account_name"] = azure_config.account_name
            if azure_config.account_key:
                config["account_key"] = azure_config.account_key
            if azure_config.connection_string:
                config["connection_string"] = azure_config.connection_string
            if azure_config.endpoint_url:
                config["endpoint_url"] = azure_config.endpoint_url

        return config

    def get_fsspec_config(self, backend: StorageBackend) -> dict:
        """Get fsspec configuration for the specified backend."""
        if backend == StorageBackend.S3:
            return self.configure_s3_backend()
        elif backend == StorageBackend.AZURE_BLOB:
            return self.configure_azure_backend()
        else:
            return {}

    def open_with_backend(self, uri: str, mode: str = "rb", backend: Optional[StorageBackend] = None):
        """Open a file with the configured backend."""
        if backend is None:
            backend = self.get_configured_backend()

        # Get backend-specific configuration
        backend_config = self.get_fsspec_config(backend)

        # Configure fsspec with backend-specific settings
        if backend_config:
            # Use fsspec.open with backend-specific configuration
            return fsspec.open(uri, mode=mode, **backend_config)
        else:
            # Use default fsspec behavior
            return fsspec.open(uri, mode=mode)

    def get_backend_info(self, uri: str) -> dict:
        """Get information about the configured backend."""
        backend = self.get_configured_backend()
        config = self.get_fsspec_config(backend)

        return {
            "backend": backend.value,
            "uri": uri,
            "config": config,
            "configured_backend": True
        }


# Global storage factory instance
_storage_factory: Optional[StorageFactory] = None


def get_storage_factory() -> StorageFactory:
    """Get the global storage factory instance."""
    global _storage_factory
    if _storage_factory is None:
        _storage_factory = StorageFactory()
    return _storage_factory


def get_configured_storage_backend() -> StorageBackend:
    """Get the configured storage backend."""
    return get_storage_factory().get_configured_backend()


def get_storage_backend(uri: str) -> StorageBackend:
    """Get the configured storage backend (ignores URI format)."""
    return get_storage_factory().get_backend_for_uri(uri)


def get_backend_info(uri: str) -> dict:
    """Get information about the configured backend."""
    return get_storage_factory().get_backend_info(uri)
