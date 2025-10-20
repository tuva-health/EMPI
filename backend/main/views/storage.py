"""
Storage management views for multi-backend support.
"""
from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from main.util.io import (
    get_configured_backends,
    get_configured_storage_backend,
    get_storage_backend_info,
)
from main.views.serializer import Serializer


class StorageBackendInfoSerializer(Serializer):
    backend = serializers.CharField()
    uri = serializers.CharField()
    config = serializers.DictField()
    configured_backend = serializers.BooleanField()


class ConfiguredBackendsResponse(Serializer):
    backends = serializers.ListField(child=serializers.CharField())
    configured_backend = serializers.CharField()


class GetBackendInfoRequest(Serializer):
    uri = serializers.CharField()


class GetBackendInfoResponse(Serializer):
    backend = serializers.CharField()
    uri = serializers.CharField()


@extend_schema(
    summary="Get configured storage backends",
    responses={200: ConfiguredBackendsResponse},
)
@api_view(["GET"])
def get_configured_storage_backends(request: Request) -> Response:
    """Get list of available storage backends and the currently configured one."""
    backends = get_configured_backends()
    configured_backend = get_configured_storage_backend()

    return Response(
        {
            "backends": backends,
            "configured_backend": configured_backend,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="Get storage backend information",
    request=GetBackendInfoRequest,
    responses={200: StorageBackendInfoSerializer},
)
@api_view(["POST"])
def get_storage_backend_info(request: Request) -> Response:
    """Get detailed information about the configured storage backend."""
    serializer = GetBackendInfoRequest(data=request.data)
    serializer.is_valid(raise_exception=True)

    uri = serializer.validated_data["uri"]
    info = get_storage_backend_info(uri)

    return Response(info, status=status.HTTP_200_OK)


@extend_schema(
    summary="Test storage backend connectivity",
    request=GetBackendInfoRequest,
    responses={
        200: {"type": "object", "properties": {"status": {"type": "string"}}},
        400: {"type": "object", "properties": {"error": {"type": "string"}}},
    },
)
@api_view(["POST"])
def test_storage_backend(request: Request) -> Response:
    """Test connectivity to the configured storage backend."""
    serializer = GetBackendInfoRequest(data=request.data)
    serializer.is_valid(raise_exception=True)

    uri = serializer.validated_data["uri"]

    try:
        # Try to open the URI to test connectivity
        from main.util.io import open_source

        with open_source(uri) as f:
            # Just test that we can open it
            pass

        return Response(
            {"status": "success", "message": f"Successfully connected to {uri} using configured backend"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to connect to {uri}: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
