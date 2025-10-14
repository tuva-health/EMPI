"""Pagination utilities for API views."""

from typing import Any, Dict, List

from rest_framework import status
from rest_framework.response import Response


class PaginationMixin:
    """Mixin to add pagination functionality to views."""

    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 1000

    def get_skip_take(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, int]:
        """Extract skip and take values from request data."""
        (page, page_size) = self.get_pagination_params(data)
        skip = (page - 1) * page_size
        take = page_size + 1  # Fetch one extra to check for next page
        return {"skip": skip, "take": take}

    def get_pagination_params(self, data: Dict[str, Any]) -> tuple[int, int]:
        """Extract pagination parameters from request data."""
        page = data.get("page", 1)
        page_size = min(
            data.get("page_size", self.DEFAULT_PAGE_SIZE), self.MAX_PAGE_SIZE
        )
        return page, page_size

    def paginate_list(
        self, items: List[Any], page: int, page_size: int
    ) -> Dict[str, Any]:
        """Return pagination metadata for a list of items.

        This assumes that `items` is longer than `page_size` if there is a next page.
        """
        has_next = len(items) > page_size
        has_previous = page > 1

        return {
            "items": items[0:page_size],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
                "has_previous": has_previous,
                "next_page": page + 1 if has_next else None,
                "previous_page": page - 1 if has_previous else None,
            },
        }

    def create_paginated_response(
        self,
        items: List[Any],
        page: int,
        page_size: int,
        response_key: str = "items",
    ) -> Response:
        """Create a paginated response with standard format.

        This assumes that `items` is longer than `page_size` if there is a next page.
        """
        paginated_data = self.paginate_list(items, page, page_size)

        return Response(
            {
                response_key: paginated_data["items"],
                "pagination": paginated_data["pagination"],
            },
            status=status.HTTP_200_OK,
        )

    def create_simple_response(
        self, items: List[Any], response_key: str = "items"
    ) -> Response:
        """Create a simple response without pagination metadata."""
        return Response(
            {response_key: items},
            status=status.HTTP_200_OK,
        )
