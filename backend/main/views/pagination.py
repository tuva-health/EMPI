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
        """
        Compute skip and take counts for pagination based on request data.
        
        Parameters:
            data (Dict[str, Any]): Mapping of request parameters; expected keys include "page" and "page_size".
        
        Returns:
            Dict[str, int]: Dictionary with:
                - "skip": number of items to skip (calculated as (page - 1) * page_size)
                - "take": number of items to request (page_size + 1, one extra to detect a next page)
        """
        (page, page_size) = self.get_pagination_params(data)
        skip = (page - 1) * page_size
        take = page_size + 1  # Fetch one extra to check for next page
        return {"skip": skip, "take": take}

    def get_pagination_params(self, data: Dict[str, Any]) -> tuple[int, int]:
        """
        Normalize pagination parameters from a request-like mapping.
        
        Parameters:
            data (Dict[str, Any]): Mapping that may contain "page" and "page_size" keys.
        
        Returns:
            tuple[int, int]: A (page, page_size) pair where `page` defaults to 1 if missing and `page_size` is clamped to at most MAX_PAGE_SIZE (defaults to DEFAULT_PAGE_SIZE if not provided).
        """
        page = data.get("page", 1)
        page_size = min(
            data.get("page_size", self.DEFAULT_PAGE_SIZE), self.MAX_PAGE_SIZE
        )
        return page, page_size

    def paginate_list(
        self, items: List[Any], page: int, page_size: int
    ) -> Dict[str, Any]:
        """
        Produce paginated items and pagination metadata for the given page.
        
        Parameters:
            items (List[Any]): Sequence of items for the requested page; may contain up to one extra item (page_size + 1) to indicate whether a next page exists.
            page (int): 1-based page number.
            page_size (int): Maximum number of items to return for the page.
        
        Returns:
            Dict[str, Any]: A dictionary with:
                - "items": the slice of items for the page (at most `page_size` elements),
                - "pagination": metadata containing `page`, `page_size`, `has_next`, `has_previous`, `next_page`, and `previous_page`.
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
        """
        Create a paginated HTTP response in the module's standard format.
        
        Parameters:
            items (List[Any]): Sequence of results for the current request. If one extra item beyond `page_size` is present, it will be used to indicate that a next page exists.
            page (int): Current page number.
            page_size (int): Maximum number of items per page (used to slice `items` and determine `has_next`).
            response_key (str): Key name under which the paginated items will be returned (default: "items").
        
        Returns:
            Response: HTTP 200 response with a body containing:
                - `{response_key}`: the sliced list of items for the current page.
                - `pagination`: metadata with keys `page`, `page_size`, `has_next`, `has_previous`, `next_page`, and `previous_page`.
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