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

from .logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)


class Config:
    """Configuration management class for transform-myd-minimal."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration with defaults and load from file if available."""
        # Set default values
        self.fuzzy_threshold = 0.6
        self.max_suggestions = 3
        self.disable_fuzzy = False
        self.input_dir = "data/02_fields"
        self.output_dir = "output"
        
        # Optional default object and variant (can be set in config)
        self.object = None
        self.variant = None
        
        # New mapping configuration defaults
        self.mapping_from_sources = False
        self.source_headers = {
            'path': 'data/02_fields/BNKA_headers.xlsx',
            'sheet': 'Sheet1',
            'header_row': 1,
            'ignore_data_below': True
        }
        self.target_xml = {
            'path': 'data/02_fields/Source data for Bank.xml',
            'worksheet_name': 'Field List',
            'header_match': {
                'sheet_name': 'Sheet Name',
                'group_name': 'Group Name',
                'description': 'Field Description',
                'importance': 'Importance',
                'type': 'Type',
                'length': 'Length',
                'decimal': 'Decimal',
                'sap_table': 'SAP Structure',
                'sap_field': 'SAP Field'
            },
            'normalization': {
                'strip_table_prefix': 'S_',
                'uppercase_table_field': True
            },
            'output_naming': {
                'transformer_id_template': '{sap_table}#{sap_field}',
                'internal_id_template': '{internal_table}.{sap_field}'
            }
        }
        self.matching = {
            'target_label_priority': ['description', 'sap_field', 'group_name']
        }
        
        # Load from config file if it exists
        if config_path is None:
            # Look in config directory first, fallback to old configs directory for backward compatibility
            config_path = Path.cwd() / "config" / "config.yaml"
            if not config_path.exists():
                config_path = Path.cwd() / "configs" / "config.yaml"
                if not config_path.exists():
                    config_path = Path.cwd() / "config.yaml"
        
        if config_path.exists():
            self._load_from_file(config_path)
    
    def _load_from_file(self, config_path: Path) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                # Update existing configuration values
                if 'object' in config_data:
                    self.object = str(config_data['object'])
                if 'variant' in config_data:
                    self.variant = str(config_data['variant'])
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
                
                # Load new mapping configuration if present
                mapping_config = config_data.get('mapping', {})
                if mapping_config:
                    self.mapping_from_sources = mapping_config.get('from_sources', self.mapping_from_sources)
                    
                    # Update source headers config
                    if 'source_headers' in mapping_config:
                        source_config = mapping_config['source_headers']
                        self.source_headers.update(source_config)
                    
                    # Update target XML config
                    if 'target_xml' in mapping_config:
                        target_config = mapping_config['target_xml']
                        # Deep merge for nested dictionaries
                        for key, value in target_config.items():
                            if key in self.target_xml and isinstance(self.target_xml[key], dict) and isinstance(value, dict):
                                self.target_xml[key].update(value)
                            else:
                                self.target_xml[key] = value
                
                # Load matching config
                if 'matching' in config_data:
                    self.matching.update(config_data['matching'])
                    
        except Exception as e:
            logger.warning(f"Could not load config.yaml: {e}")
            logger.info("Using default values")
    
    def merge_with_cli_args(self, args) -> None:
        """Merge CLI arguments with config values. CLI args take precedence."""
        # Handle object and variant - use config defaults if CLI not provided
        if hasattr(args, 'object') and args.object is not None:
            self.object = args.object
        elif hasattr(args, 'object') and self.object is None:
            # This should not happen due to required=True when no config default
            raise ValueError("Object must be provided either via CLI or config.yaml")
            
        if hasattr(args, 'variant') and args.variant is not None:
            self.variant = args.variant
        elif hasattr(args, 'variant') and self.variant is None:
            # This should not happen due to required=True when no config default
            raise ValueError("Variant must be provided either via CLI or config.yaml")
        
        # CLI arguments override config values if they are provided
        if hasattr(args, 'fuzzy_threshold') and args.fuzzy_threshold is not None:
            self.fuzzy_threshold = args.fuzzy_threshold
        if hasattr(args, 'max_suggestions') and args.max_suggestions is not None:
            self.max_suggestions = args.max_suggestions
        if hasattr(args, 'disable_fuzzy') and args.disable_fuzzy is not None:
            self.disable_fuzzy = args.disable_fuzzy
        
        # New mapping-related CLI arguments
        if hasattr(args, 'source_headers_xlsx') and args.source_headers_xlsx is not None:
            self.source_headers['path'] = args.source_headers_xlsx
        if hasattr(args, 'source_headers_sheet') and args.source_headers_sheet is not None:
            self.source_headers['sheet'] = args.source_headers_sheet
        if hasattr(args, 'source_headers_row') and args.source_headers_row is not None:
            self.source_headers['header_row'] = args.source_headers_row
        if hasattr(args, 'target_xml') and args.target_xml is not None:
            self.target_xml['path'] = args.target_xml
        if hasattr(args, 'target_xml_worksheet') and args.target_xml_worksheet is not None:
            self.target_xml['worksheet_name'] = args.target_xml_worksheet
    
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