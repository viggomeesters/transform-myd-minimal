#!/usr/bin/env python3
"""
Configuration loading and management for transform-myd-minimal.

Handles loading configuration from config.yaml and merging with CLI arguments.
CLI arguments take precedence over config.yaml values.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

import yaml


class Config:
    """Configuration management class for transform-myd-minimal."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration with defaults and load from file if available."""
        # Set default values
        self.fuzzy_threshold = 0.6
        self.max_suggestions = 3
        self.disable_fuzzy = False
        self.input_dir = "data/02_fields"
        self.output_dir = "config"
        
        # Load from config file if it exists
        if config_path is None:
            config_path = Path.cwd() / "config.yaml"
        
        if config_path.exists():
            self._load_from_file(config_path)
    
    def _load_from_file(self, config_path: Path) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                # Update values if they exist in the config file
                if 'fuzzy_threshold' in config_data:
                    self.fuzzy_threshold = float(config_data['fuzzy_threshold'])
                if 'max_suggestions' in config_data:
                    self.max_suggestions = int(config_data['max_suggestions'])
                if 'disable_fuzzy' in config_data:
                    self.disable_fuzzy = bool(config_data['disable_fuzzy'])
                if 'input_dir' in config_data:
                    self.input_dir = str(config_data['input_dir'])
                if 'output_dir' in config_data:
                    self.output_dir = str(config_data['output_dir'])
                    
        except Exception as e:
            print(f"Warning: Could not load config.yaml: {e}")
            print("Using default values")
    
    def merge_with_cli_args(self, args) -> None:
        """Merge CLI arguments with config values. CLI args take precedence."""
        # CLI arguments override config values if they are provided
        if hasattr(args, 'fuzzy_threshold') and args.fuzzy_threshold is not None:
            self.fuzzy_threshold = args.fuzzy_threshold
        if hasattr(args, 'max_suggestions') and args.max_suggestions is not None:
            self.max_suggestions = args.max_suggestions
        if hasattr(args, 'disable_fuzzy') and args.disable_fuzzy is not None:
            self.disable_fuzzy = args.disable_fuzzy
    
    def get_input_path(self, object_name: str, variant: str) -> Path:
        """Get the full input path for Excel file."""
        base_dir = Path.cwd()
        excel_filename = f"fields_{object_name}_{variant}.xlsx"
        return base_dir / self.input_dir / excel_filename
    
    def get_output_dir(self, object_name: str, variant: str) -> Path:
        """Get the full output directory path."""
        base_dir = Path.cwd()
        return base_dir / self.output_dir / object_name / variant


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or use defaults."""
    return Config(config_path)