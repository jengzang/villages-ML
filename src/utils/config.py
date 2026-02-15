"""Configuration management for character frequency analysis pipeline."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json
from pathlib import Path
from datetime import datetime


@dataclass
class CleaningConfig:
    """Configuration for text cleaning and normalization."""
    bracket_mode: str = "remove_content"  # "remove_content" or "keep_all"
    keep_rare_chars: bool = True  # Keep rare CJK Extension chars
    min_name_length: int = 1  # Minimum valid name length after cleaning

    def validate(self):
        """Validate configuration parameters."""
        if self.bracket_mode not in ["remove_content", "keep_all"]:
            raise ValueError(f"Invalid bracket_mode: {self.bracket_mode}")
        if self.min_name_length < 1:
            raise ValueError("min_name_length must be >= 1")


@dataclass
class FrequencyConfig:
    """Configuration for frequency computation."""
    region_levels: List[str] = field(default_factory=lambda: ["city", "county", "township"])
    min_count_threshold: int = 10  # Minimum count for reporting
    chunk_size: int = 10000  # Chunk size for streaming processing

    def validate(self):
        """Validate configuration parameters."""
        valid_levels = ["city", "county", "township"]
        for level in self.region_levels:
            if level not in valid_levels:
                raise ValueError(f"Invalid region level: {level}")


@dataclass
class TendencyConfig:
    """Configuration for regional tendency analysis."""
    smoothing_alpha: float = 1.0  # Laplace smoothing parameter
    min_global_support: int = 20  # Minimum global village count
    min_regional_support: int = 5  # Minimum regional village count
    compute_z_score: bool = True  # Whether to compute z-scores

    def validate(self):
        """Validate configuration parameters."""
        if self.smoothing_alpha < 0:
            raise ValueError("smoothing_alpha must be >= 0")
        if self.min_global_support < 1:
            raise ValueError("min_global_support must be >= 1")
        if self.min_regional_support < 1:
            raise ValueError("min_regional_support must be >= 1")


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""
    run_id: str
    db_path: str
    output_dir: str
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    frequency: FrequencyConfig = field(default_factory=FrequencyConfig)
    tendency: TendencyConfig = field(default_factory=TendencyConfig)

    @classmethod
    def create_default(cls, db_path: str, output_dir: str, run_id: Optional[str] = None):
        """Create default configuration with auto-generated run_id."""
        if run_id is None:
            run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return cls(
            run_id=run_id,
            db_path=db_path,
            output_dir=output_dir
        )

    def validate(self):
        """Validate all configuration parameters."""
        self.cleaning.validate()
        self.frequency.validate()
        self.tendency.validate()

        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def to_dict(self):
        """Convert configuration to dictionary."""
        return asdict(self)

    def save(self, path: str):
        """Save configuration to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str):
        """Load configuration from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls(
            run_id=data['run_id'],
            db_path=data['db_path'],
            output_dir=data['output_dir'],
            cleaning=CleaningConfig(**data.get('cleaning', {})),
            frequency=FrequencyConfig(**data.get('frequency', {})),
            tendency=TendencyConfig(**data.get('tendency', {}))
        )
