import io
import os
from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from typing import IO, Iterator
from urllib.parse import urlunparse

import fsspec  # type: ignore[import-untyped]
from django.core.files.uploadedfile import UploadedFile

from main.util.storage_factory import get_storage_factory

DEFAULT_BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE
DEFAULT_MAX_TEMP_FILE_BUFFER_SIZE = 20 * 1024 * 1024  # 20 MiB


def _is_azure_blob_uri(uri: str) -> bool:
    """Check if the URI is an Azure Blob Storage URI."""
    return uri.startswith("abfs://") or uri.startswith("azure://")


def _is_s3_uri(uri: str) -> bool:
    """Check if the URI is an S3 URI."""
    return uri.startswith("s3://")


def _configure_fsspec_for_azure() -> None:
    """Configure fsspec for Azure Blob Storage if needed."""
    try:
        # Import adlfs to register the Azure Blob Storage filesystem with fsspec
        import adlfs  # type: ignore[import-untyped]

        # Set up Azure credentials from environment variables if not already configured
        if not os.environ.get("AZURE_STORAGE_ACCOUNT_NAME"):
            # Try to get from Azure Identity (managed identity, service principal, etc.)
            try:
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()
                # This will be used by adlfs automatically
            except ImportError:
                pass
    except ImportError:
        # adlfs not available, Azure Blob Storage won't work
        pass


@contextmanager
def open_source(source: str | UploadedFile) -> Iterator[IO[bytes]]:
    if isinstance(source, str):
        # Use storage factory with configured backend
        storage_factory = get_storage_factory()
        backend = storage_factory.get_configured_backend()

        # Configure backend-specific settings
        if backend.value == "azure_blob":
            _configure_fsspec_for_azure()

        # Open with configured backend
        with storage_factory.open_with_backend(source, mode="rb", backend=backend) as f:
            yield f
    else:
        source.seek(0)
        yield source
        # Don't close — Django manages lifecycle


@contextmanager
def open_sink(sink: str | IO[bytes]) -> Iterator[IO[bytes]]:
    if isinstance(sink, str):
        # Use storage factory with configured backend
        storage_factory = get_storage_factory()
        backend = storage_factory.get_configured_backend()

        # Configure backend-specific settings
        if backend.value == "azure_blob":
            _configure_fsspec_for_azure()

        # Open with configured backend
        with storage_factory.open_with_backend(sink, mode="wb", backend=backend) as f:
            yield f
    else:
        yield sink
        # Don't close — caller manages lifecycle


def open_temp_file() -> SpooledTemporaryFile[bytes]:
    return SpooledTemporaryFile(max_size=DEFAULT_MAX_TEMP_FILE_BUFFER_SIZE)


def get_uri(file: str | UploadedFile) -> str:
    if isinstance(file, str):
        return file

    return urlunparse(("upload", "", file.name, "", "", ""))


def get_storage_backend_info(uri: str) -> dict:
    """Get information about the configured storage backend."""
    storage_factory = get_storage_factory()
    return storage_factory.get_backend_info(uri)


def get_configured_storage_backend() -> str:
    """Get the configured storage backend."""
    storage_factory = get_storage_factory()
    return storage_factory.get_configured_backend().value


def get_configured_backends() -> list[str]:
    """Get list of available storage backends."""
    return ["s3", "azure_blob"]
