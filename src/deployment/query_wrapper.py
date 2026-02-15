"""
Safe query executor with policy enforcement.

Wraps existing query functions with:
- Policy validation
- Limit application
- Pagination support
- Error handling
"""

import sqlite3
from typing import Callable, Dict, Any, Tuple, Optional
from .query_policy import QueryPolicy, PolicyViolationError
from .config import DeploymentConfig


class SafeQueryExecutor:
    """
    Safe query executor with policy enforcement.

    Wraps query functions to ensure they comply with
    deployment policies.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        policy: Optional[QueryPolicy] = None,
        config: Optional[DeploymentConfig] = None
    ):
        """
        Initialize safe query executor.

        Args:
            conn: Database connection
            policy: Query policy (uses default if None)
            config: Deployment config (uses default if None)
        """
        self.conn = conn
        self.config = config or DeploymentConfig()
        self.policy = policy or QueryPolicy(
            max_rows=self.config.max_rows_default,
            max_rows_absolute=self.config.max_rows_absolute,
            enable_full_scan=self.config.enable_full_scan,
            enable_runtime_clustering=self.config.enable_runtime_clustering
        )

    def execute(
        self,
        query_func: Callable,
        **kwargs
    ) -> Any:
        """
        Execute query function with policy enforcement.

        Args:
            query_func: Query function to execute
            **kwargs: Query parameters

        Returns:
            Query results

        Raises:
            PolicyViolationError: If query violates policy
        """
        # Validate query
        is_valid, error_msg = self.policy.validate_query(kwargs)
        if not is_valid:
            raise PolicyViolationError(error_msg)

        # Apply limits
        kwargs = self.policy.apply_limits(kwargs)

        # Execute query
        return query_func(self.conn, **kwargs)

    def execute_with_pagination(
        self,
        query_func: Callable,
        page: int = 1,
        page_size: Optional[int] = None,
        **kwargs
    ) -> Tuple[Any, int, bool]:
        """
        Execute query with pagination support.

        Args:
            query_func: Query function to execute
            page: Page number (1-indexed)
            page_size: Rows per page (uses default if None)
            **kwargs: Query parameters

        Returns:
            (results, total_count, has_next_page)

        Raises:
            PolicyViolationError: If query violates policy
        """
        # Use default page size if not specified
        if page_size is None:
            page_size = self.config.default_page_size

        # Get pagination parameters
        pagination = self.policy.get_pagination_params(
            page=page,
            page_size=page_size,
            max_page_size=self.config.max_page_size
        )

        # Merge with query parameters
        kwargs.update(pagination)

        # Validate query
        is_valid, error_msg = self.policy.validate_query(kwargs)
        if not is_valid:
            raise PolicyViolationError(error_msg)

        # Execute query
        results = query_func(self.conn, **kwargs)

        # Get total count (execute query without limit)
        count_kwargs = {k: v for k, v in kwargs.items() if k not in ['limit', 'offset']}
        total_results = query_func(self.conn, **count_kwargs)
        total_count = len(total_results) if hasattr(total_results, '__len__') else 0

        # Check if there's a next page
        has_next = (page * page_size) < total_count

        return results, total_count, has_next
