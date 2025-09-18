#!/usr/bin/env python3
"""
CLI parsing and argument handling for transform-myd-minimal.

Contains all CLI parsing and argument handling including:
- argparse setup and configuration
- subcommands definition
- help and version handling
- Backward compatibility with legacy format
"""

import argparse
import sys

from .config_loader import load_config
from .logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)


__version__ = "3.0.0"


def setup_cli():
    """Set up the command line interface with argparse."""
    # Load configuration to get default values
    config = load_config()
    
    # Check if this is the old format (no subcommand)
    if len(sys.argv) > 1 and not sys.argv[1] in ['map', '-h', '--help', '--version']:
        # Old format detected, handle backward compatibility
        logger.info("Note: Using legacy format. Consider using 'map' subcommand: python3 transform_myd_minimal.py map --object {} --variant {}".format(
            sys.argv[sys.argv.index('-object') + 1] if '-object' in sys.argv else 'OBJECT',
            sys.argv[sys.argv.index('-variant') + 1] if '-variant' in sys.argv else 'VARIANT'
        ))
        
        # Parse with old format
        old_parser = argparse.ArgumentParser(description='Generate column mapping YAML from Excel field definitions (Advanced Version)')
        old_parser.add_argument('-object', '--object', required=True, help='Object name (e.g., m140)')
        old_parser.add_argument('-variant', '--variant', required=True, help='Variant name (e.g., bnka)')
        old_parser.add_argument('--fuzzy-threshold', type=float, default=config.fuzzy_threshold, help=f'Fuzzy matching threshold (0.0-1.0, default: {config.fuzzy_threshold})')
        old_parser.add_argument('--max-suggestions', type=int, default=config.max_suggestions, help=f'Maximum fuzzy match suggestions (default: {config.max_suggestions})')
        old_parser.add_argument('--disable-fuzzy', action='store_true', default=config.disable_fuzzy, help='Disable fuzzy matching')
        
        # New optional flags for source-based mapping (legacy format)
        old_parser.add_argument('--source-headers-xlsx', type=str, help='Path to source headers XLSX file')
        old_parser.add_argument('--source-headers-sheet', type=str, help='Sheet name in source XLSX')
        old_parser.add_argument('--source-headers-row', type=int, help='Header row number in source XLSX')
        old_parser.add_argument('--target-xml', type=str, help='Path to target XML file')
        old_parser.add_argument('--target-xml-worksheet', type=str, help='Worksheet name in target XML')
        
        args = old_parser.parse_args()
        config.merge_with_cli_args(args)
        return args, config, True  # True indicates legacy format
    
    # New format with subcommands
    parser = argparse.ArgumentParser(description='Transform MYD Minimal - Advanced Field Matching and YAML Generation')
    parser.add_argument('--version', action='version', version=f'transform-myd-minimal {__version__}')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Map subcommand (default behavior)
    map_parser = subparsers.add_parser('map', help='Generate column mapping and YAML files')
    map_parser.add_argument('--object', required=True, help='Object name (e.g., m140)')
    map_parser.add_argument('--variant', required=True, help='Variant name (e.g., bnka)')
    map_parser.add_argument('--fuzzy-threshold', type=float, default=config.fuzzy_threshold, help=f'Fuzzy matching threshold (0.0-1.0, default: {config.fuzzy_threshold})')
    map_parser.add_argument('--max-suggestions', type=int, default=config.max_suggestions, help=f'Maximum fuzzy match suggestions (default: {config.max_suggestions})')
    map_parser.add_argument('--disable-fuzzy', action='store_true', default=config.disable_fuzzy, help='Disable fuzzy matching')
    
    # New optional flags for source-based mapping
    map_parser.add_argument('--source-headers-xlsx', type=str, help='Path to source headers XLSX file (overrides config)')
    map_parser.add_argument('--source-headers-sheet', type=str, help='Sheet name in source XLSX (overrides config)')
    map_parser.add_argument('--source-headers-row', type=int, help='Header row number in source XLSX (overrides config)')
    map_parser.add_argument('--target-xml', type=str, help='Path to target XML file (overrides config)')
    map_parser.add_argument('--target-xml-worksheet', type=str, help='Worksheet name in target XML (overrides config)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is specified, show help
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Validate command
    if args.command != 'map':
        parser.print_help()
        sys.exit(1)
    
    config.merge_with_cli_args(args)
    return args, config, False  # False indicates new format