"""
Query policy framework for enforcing safe query execution.

This module provides:
- Query validation (block expensive operations)
- Row limit enforcement
- Query parameter sanitization
"""

from typing import Dict, Any, Tuple, Optional


class PolicyViolationError(Exception):
    """Raised when a query violates the policy."""
    pass


class QueryPolicy:
    """
    Query policy enforcer for safe online serving.

    Enforces:
    - Maximum row limits
    - Full table scan prevention
    - Expensive operation blocking
    """

    def __init__(
        self,
        max_rows: int = 1000,
        max_rows_absolute: int = 10000,
        enable_full_scan: bool = False,
        enable_runtime_clustering: bool = False
    ):
        """
        Initialize query policy.

        Args:
            max_rows: Default maximum rows to return
            max_rows_absolute: Absolute maximum rows (cannot be exceeded)
            enable_full_scan: Allow queries without filters
            enable_runtime_clustering: Allow runtime clustering operations
        """
        self.max_rows = max_rows
        self.max_rows_absolute = max_rows_absolute
        self.enable_full_scan = enable_full_scan
        self.enable_runtime_clustering = enable_runtime_clustering

    def validate_query(self, query_params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate if a query is allowed under the policy.

        Args:
            query_params: Query parameters (filters, limit, etc.)

        Returns:
            (is_valid, error_message)
        """
        # Check for full table scan
        if not self.enable_full_scan:
            has_filter = self._has_filter(query_params)
            if not has_filter:
                return False, "Full table scan not allowed. Please provide filters (city, county, town, or cluster_id)."

        # Check row limit - don't reject, just warn if it will be capped
        # The apply_limits method will handle capping
        requested_limit = query_params.get('limit')
        if requested_limit is not None:
            # Only reject if limit is unreasonably large (e.g., > 10x absolute max)
            if requested_limit > self.max_rows_absolute * 10:
                return False, f"Requested limit {requested_limit} is unreasonably large (max: {self.max_rows_absolute})."

        # Check for runtime clustering
        if query_params.get('enable_clustering') and not self.enable_runtime_clustering:
            return False, "Runtime clustering not allowed. Use precomputed cluster_id instead."

        return True, ""

    def _has_filter(self, query_params: Dict[str, Any]) -> bool:
        """Check if query has at least one filter (excluding run_id)."""
        filter_keys = ['city', 'county', 'town', 'cluster_id', 'semantic_category', 'suffix', 'algorithm']
        return any(query_params.get(key) is not None for key in filter_keys)

    def apply_limits(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply policy limits to query parameters.

        Args:
            query_params: Original query parameters

        Returns:
            Modified query parameters with limits applied
        """
        params = query_params.copy()

        # Apply default limit if not specified
        if 'limit' not in params or params['limit'] is None:
            params['limit'] = self.max_rows

        # Cap limit at absolute maximum
        if params['limit'] > self.max_rows_absolute:
            params['limit'] = self.max_rows_absolute

        return params

    def get_pagination_params(
        self,
        page: int = 1,
        page_size: int = 100,
        max_page_size: int = 500
    ) -> Dict[str, int]:
        """
        Calculate pagination parameters.

        Args:
            page: Page number (1-indexed)
            page_size: Rows per page
            max_page_size: Maximum allowed page size

        Returns:
            Dict with 'limit' and 'offset'
        """
        # Validate page number
        if page < 1:
            page = 1

        # Cap page size
        if page_size > max_page_size:
            page_size = max_page_size

        # Calculate offset
        offset = (page - 1) * page_size

        return {
            'limit': page_size,
            'offset': offset
        }
