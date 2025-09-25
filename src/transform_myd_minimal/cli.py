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


__version__ = "4.0.0"


def setup_cli():
    """Set up the command line interface with argparse."""
    # Load configuration to get default values
    config = load_config()

    # Check if this is the old format (no subcommand)
    if len(sys.argv) > 1 and sys.argv[1] not in [
        "map",
        "index_source",
        "index_target",
        "transform",
        "-h",
        "--help",
        "--version",
    ]:
        # Old format detected, handle backward compatibility
        logger.info(
            "Note: Using legacy format. Consider using 'map' subcommand: python3 transform_myd_minimal.py map --object {} --variant {}".format(
                (
                    sys.argv[sys.argv.index("-object") + 1]
                    if "-object" in sys.argv
                    else "OBJECT"
                ),
                (
                    sys.argv[sys.argv.index("-variant") + 1]
                    if "-variant" in sys.argv
                    else "VARIANT"
                ),
            )
        )

        # Parse with old format
        old_parser = argparse.ArgumentParser(
            description="Generate column mapping YAML from Excel field definitions (Advanced Version)"
        )
        old_parser.add_argument(
            "-object", "--object", required=True, help="Object name (e.g., m140)"
        )
        old_parser.add_argument(
            "-variant", "--variant", required=True, help="Variant name (e.g., bnka)"
        )
        old_parser.add_argument(
            "--fuzzy-threshold",
            type=float,
            default=config.fuzzy_threshold,
            help=f"Fuzzy matching threshold (0.0-1.0, default: {config.fuzzy_threshold})",
        )
        old_parser.add_argument(
            "--max-suggestions",
            type=int,
            default=config.max_suggestions,
            help=f"Maximum fuzzy match suggestions (default: {config.max_suggestions})",
        )
        old_parser.add_argument(
            "--disable-fuzzy",
            action="store_true",
            default=config.disable_fuzzy,
            help="Disable fuzzy matching",
        )

        # New optional flags for source-based mapping (legacy format)
        old_parser.add_argument(
            "--source-headers-xlsx", type=str, help="Path to source headers XLSX file"
        )
        old_parser.add_argument(
            "--source-headers-sheet", type=str, help="Sheet name in source XLSX"
        )
        old_parser.add_argument(
            "--source-headers-row", type=int, help="Header row number in source XLSX"
        )
        old_parser.add_argument(
            "--target-xml", type=str, help="Path to target XML file"
        )
        old_parser.add_argument(
            "--target-xml-worksheet", type=str, help="Worksheet name in target XML"
        )

        args = old_parser.parse_args()
        config.merge_with_cli_args(args)
        return args, config, True  # True indicates legacy format

    # New format with subcommands
    parser = argparse.ArgumentParser(
        description="Transform MYD Minimal - Advanced Field Matching and YAML Generation"
    )
    parser.add_argument(
        "--version", action="version", version=f"transform-myd-minimal {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Map subcommand (default behavior)
    map_parser = subparsers.add_parser(
        "map", help="Generate column mapping and YAML files"
    )

    # Object and variant are required unless provided in config
    object_required = config.object is None
    variant_required = config.variant is None

    object_help = "Object name (e.g., m140)"
    variant_help = "Variant name (e.g., bnka)"

    if not object_required:
        object_help += f" (default from config: {config.object})"
    if not variant_required:
        variant_help += f" (default from config: {config.variant})"

    map_parser.add_argument(
        "-o", "--object", required=object_required, help=object_help
    )
    map_parser.add_argument(
        "-v", "--variant", required=variant_required, help=variant_help
    )
    map_parser.add_argument("--root", default=".", help="Root directory (default: .)")
    map_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing outputs"
    )
    map_parser.add_argument(
        "--json", action="store_true", help="Force JSONL output to stdout"
    )
    map_parser.add_argument(
        "--format", choices=["human", "jsonl"], help="Output format (overrides TTY detection)"
    )
    map_parser.add_argument(
        "--log-file", type=str, help="Override log file path"
    )
    map_parser.add_argument(
        "--no-log-file", action="store_true", help="Do not write log file"
    )
    map_parser.add_argument(
        "--no-preview", action="store_true", help="Suppress preview table in human mode"
    )
    map_parser.add_argument(
        "--quiet",
        action="store_true",
        help="No stdout output; still writes file unless --no-log-file",
    )
    
    # HTML reporting options for map command
    map_parser.add_argument(
        "--no-html", action="store_true", help="Skip HTML report generation"
    )
    map_parser.add_argument(
        "--html-dir", type=str, help="Custom directory for HTML and JSON reports"
    )

    # Fuzzy matching options for map command
    map_parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=config.fuzzy_threshold,
        help=f"Fuzzy matching threshold (0.0-1.0, default: {config.fuzzy_threshold})",
    )
    map_parser.add_argument(
        "--max-suggestions",
        type=int,
        default=config.max_suggestions,
        help=f"Maximum fuzzy match suggestions (default: {config.max_suggestions})",
    )
    map_parser.add_argument(
        "--disable-fuzzy",
        action="store_true",
        default=config.disable_fuzzy,
        help="Disable fuzzy matching completely",
    )

    # Source-based mapping options for map command
    map_parser.add_argument(
        "--source-headers-xlsx", type=str, help="Path to source headers XLSX file"
    )
    map_parser.add_argument(
        "--source-headers-sheet", type=str, help="Sheet name in source XLSX"
    )
    map_parser.add_argument(
        "--source-headers-row", type=int, help="Header row number in source XLSX"
    )
    map_parser.add_argument("--target-xml", type=str, help="Path to target XML file")
    map_parser.add_argument(
        "--target-xml-worksheet", type=str, help="Worksheet name in target XML"
    )

    # Index source subcommand
    index_source_parser = subparsers.add_parser(
        "index_source", help="Parse and index source fields from XLSX file"
    )
    index_source_parser.add_argument(
        "--object", required=True, help="Object name (e.g., m140)"
    )
    index_source_parser.add_argument(
        "--variant", required=True, help="Variant name (e.g., bnka)"
    )
    index_source_parser.add_argument(
        "--root", default=".", help="Root directory (default: .)"
    )
    index_source_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing outputs"
    )
    # Logging flags
    index_source_parser.add_argument(
        "--json", action="store_true", help="Force JSONL output to stdout"
    )
    index_source_parser.add_argument(
        "--format",
        choices=["human", "jsonl"],
        help="Output format (overrides TTY detection)",
    )
    index_source_parser.add_argument(
        "--log-file", type=str, help="Override log file path"
    )
    index_source_parser.add_argument(
        "--no-log-file", action="store_true", help="Do not write log file"
    )
    index_source_parser.add_argument(
        "--no-preview", action="store_true", help="Suppress preview table in human mode"
    )
    index_source_parser.add_argument(
        "--quiet",
        action="store_true",
        help="No stdout output; still writes file unless --no-log-file",
    )
    
    # HTML reporting options for index_source command
    index_source_parser.add_argument(
        "--no-html", action="store_true", help="Skip HTML report generation"
    )
    index_source_parser.add_argument(
        "--html-dir", type=str, help="Custom directory for HTML and JSON reports"
    )

    # Index target subcommand
    index_target_parser = subparsers.add_parser(
        "index_target", help="Parse and index target fields from XML file"
    )
    index_target_parser.add_argument(
        "--object", required=True, help="Object name (e.g., m140)"
    )
    index_target_parser.add_argument(
        "--variant", required=True, help="Variant name (e.g., bnka)"
    )
    index_target_parser.add_argument(
        "--root", default=".", help="Root directory (default: .)"
    )
    index_target_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing outputs"
    )
    index_target_parser.add_argument(
        "--prefer-xlsx", action="store_true", help="Prefer .xlsx file over .xml when both exist (F02 fallback feature)"
    )
    # Logging flags
    index_target_parser.add_argument(
        "--json", action="store_true", help="Force JSONL output to stdout"
    )
    index_target_parser.add_argument(
        "--format",
        choices=["human", "jsonl"],
        help="Output format (overrides TTY detection)",
    )
    index_target_parser.add_argument(
        "--log-file", type=str, help="Override log file path"
    )
    index_target_parser.add_argument(
        "--no-log-file", action="store_true", help="Do not write log file"
    )
    index_target_parser.add_argument(
        "--no-preview", action="store_true", help="Suppress preview table in human mode"
    )
    index_target_parser.add_argument(
        "--quiet",
        action="store_true",
        help="No stdout output; still writes file unless --no-log-file",
    )
    
    # HTML reporting options for index_target command
    index_target_parser.add_argument(
        "--no-html", action="store_true", help="Skip HTML report generation"
    )
    index_target_parser.add_argument(
        "--html-dir", type=str, help="Custom directory for HTML and JSON reports"
    )

    # Transform subcommand
    transform_parser = subparsers.add_parser(
        "transform", help="Transform raw data through ETL pipeline to SAP CSV"
    )
    transform_parser.add_argument(
        "-o", "--object", required=True, help="Object name (e.g., m140)"
    )
    transform_parser.add_argument(
        "-v", "--variant", required=True, help="Variant name (e.g., bnka)"
    )
    transform_parser.add_argument(
        "--root", default=".", help="Root directory (default: .)"
    )
    transform_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing outputs"
    )
    transform_parser.add_argument(
        "--json", action="store_true", help="Force JSONL output to stdout"
    )
    transform_parser.add_argument(
        "--format", choices=["human", "jsonl"], help="Output format (overrides TTY detection)"
    )
    transform_parser.add_argument(
        "--log-file", type=str, help="Override log file path"
    )
    transform_parser.add_argument(
        "--no-log-file", action="store_true", help="Do not write log file"
    )
    transform_parser.add_argument(
        "--no-preview", action="store_true", help="Suppress preview table in human mode"
    )
    transform_parser.add_argument(
        "--quiet",
        action="store_true",
        help="No stdout output; still writes file unless --no-log-file",
    )
    
    # HTML reporting options for transform command
    transform_parser.add_argument(
        "--no-html", action="store_true", help="Skip HTML report generation"
    )
    transform_parser.add_argument(
        "--html-dir", type=str, help="Custom directory for HTML and JSON reports"
    )

    # Parse arguments
    args = parser.parse_args()

    # If no command is specified, show help
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Validate command
    if args.command not in ["map", "index_source", "index_target", "transform"]:
        parser.print_help()
        sys.exit(1)

    config.merge_with_cli_args(args)

    # For index_source, index_target and transform commands, we need object and variant
    if args.command in ["index_source", "index_target", "transform"]:
        # These commands always require object and variant from CLI args
        return args, config, False

    # Validate that we have object and variant after merging (for map command)
    if not config.object:
        logger.error(
            "Object must be provided either via --object argument or config.yaml"
        )
        sys.exit(1)
    if not config.variant:
        logger.error(
            "Variant must be provided either via --variant argument or config.yaml"
        )
        sys.exit(1)

    return args, config, False  # False indicates new format


def app():
    """Console script entry point."""
    from .main import main

    main()
