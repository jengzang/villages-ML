"""
Deployment configuration management.

Provides configuration for different deployment environments:
- Production: Strict limits, no expensive operations
- Development: Relaxed limits, allow experimentation
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class DeploymentConfig:
    """
    Deployment configuration manager.

    Loads configuration from JSON files and provides
    typed access to configuration values.
    """

    # Default configuration
    DEFAULTS = {
        'query_limits': {
            'max_rows_default': 1000,
            'max_rows_absolute': 10000,
            'default_page_size': 100,
            'max_page_size': 500
        },
        'feature_flags': {
            'enable_full_scan': False,
            'enable_runtime_clustering': False
        },
        'performance': {
            'max_query_time_ms': 5000,
            'max_memory_mb': 500
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to JSON config file (optional)
        """
        self.config = self.DEFAULTS.copy()

        if config_path:
            self.load_from_file(config_path)

    def load_from_file(self, config_path: str):
        """Load configuration from JSON file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r', encoding='utf-8') as f:
            user_config = json.load(f)

        # Deep merge with defaults
        self._deep_merge(self.config, user_config)

    def _deep_merge(self, base: Dict, update: Dict):
        """Deep merge update dict into base dict."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    # Query limits
    @property
    def max_rows_default(self) -> int:
        return self.config['query_limits']['max_rows_default']

    @property
    def max_rows_absolute(self) -> int:
        return self.config['query_limits']['max_rows_absolute']

    @property
    def default_page_size(self) -> int:
        return self.config['query_limits']['default_page_size']

    @property
    def max_page_size(self) -> int:
        return self.config['query_limits']['max_page_size']

    # Feature flags
    @property
    def enable_full_scan(self) -> bool:
        return self.config['feature_flags']['enable_full_scan']

    @property
    def enable_runtime_clustering(self) -> bool:
        return self.config['feature_flags']['enable_runtime_clustering']

    # Performance thresholds
    @property
    def max_query_time_ms(self) -> int:
        return self.config['performance']['max_query_time_ms']

    @property
    def max_memory_mb(self) -> int:
        return self.config['performance']['max_memory_mb']

    @classmethod
    def production(cls) -> 'DeploymentConfig':
        """Load production configuration."""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'deployment.production.json'
        if config_path.exists():
            return cls(str(config_path))
        return cls()

    @classmethod
    def development(cls) -> 'DeploymentConfig':
        """Load development configuration."""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'deployment.development.json'
        if config_path.exists():
            return cls(str(config_path))
        return cls()
