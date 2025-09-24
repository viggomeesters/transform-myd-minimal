#!/usr/bin/env python3
"""
Enhanced logging for transform-myd-minimal F01/F02 commands.

Provides Rich-based logging with TTY detection, JSONL file output,
and configurable output formats for index_source and index_target commands.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.table import Table


class EnhancedLogger:
    """Enhanced logger with Rich output, TTY detection, and JSONL file support."""

    def __init__(
        self, args, step: str, object_name: str, variant: str, root_path: Path
    ):
        """Initialize the enhanced logger.

        Args:
            args: CLI arguments containing logging flags
            step: The step name (index_source or index_target)
            object_name: Object name (e.g., m143)
            variant: Variant name (e.g., bnka)
            root_path: Root directory path
        """
        self.args = args
        self.step = step
        self.object_name = object_name
        self.variant = variant
        self.root_path = root_path
        self.start_time = time.time()

        # Determine output mode based on precedence: quiet > json > format > TTY detection
        self.quiet = getattr(args, "quiet", False)
        self.json_flag = getattr(args, "json", False)
        self.format_flag = getattr(args, "format", None)
        self.no_preview = getattr(args, "no_preview", False)

        # File logging settings
        self.log_file_path = getattr(args, "log_file", None)
        self.no_log_file = getattr(args, "no_log_file", False)

        # Console setup
        self.console = Console()

        # Determine stdout format
        if self.quiet:
            self.stdout_format = "none"
        elif self.json_flag:
            self.stdout_format = "jsonl"
        elif self.format_flag:
            self.stdout_format = self.format_flag
        else:
            # TTY detection
            self.stdout_format = "human" if sys.stdout.isatty() else "jsonl"

    def get_duration_ms(self) -> int:
        """Get elapsed time in milliseconds since logger creation."""
        return int((time.time() - self.start_time) * 1000)

    def normalize_path(self, path: Path) -> str:
        """Normalize path to use forward slashes on all OSes and make relative to root."""
        try:
            # Try to make path relative to root_path
            relative_path = path.relative_to(self.root_path)
            return str(relative_path).replace("\\", "/")
        except ValueError:
            # If path is not relative to root, use as-is
            return str(path).replace("\\", "/")

    def get_log_file_path(self) -> Optional[Path]:
        """Get the log file path based on naming convention."""
        if self.no_log_file:
            return None

        if self.log_file_path:
            return Path(self.log_file_path)

        # Default naming: data/99_logging/<step>_<object>_<variant>_<YYYYMMDD_HHmm>.jsonl
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{self.step}_{self.object_name}_{self.variant}_{timestamp}.jsonl"
        log_dir = self.root_path / "data" / "99_logging"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / filename

    def write_jsonl_to_file(self, event: Dict[str, Any]) -> None:
        """Write JSONL event to log file."""
        log_file = self.get_log_file_path()
        if not log_file:
            return

        jsonl_line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(jsonl_line + "\n")

    def output_to_stdout(
        self, event: Dict[str, Any], preview_data: Optional[List[Dict]] = None
    ) -> None:
        """Output event to stdout based on format settings."""
        if self.stdout_format == "none":
            return
        elif self.stdout_format == "jsonl":
            jsonl_line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
            print(jsonl_line)
        elif self.stdout_format == "human":
            self._output_human_format(event, preview_data)

    def _output_human_format(
        self, event: Dict[str, Any], preview_data: Optional[List[Dict]] = None
    ) -> None:
        """Output event in human-readable Rich format."""
        # Determine check mark color
        warnings_count = len(event.get("warnings", []))
        check_color = "yellow" if warnings_count > 0 else "green"
        check_mark = "✓" if warnings_count == 0 else "⚠"

        # Main summary line
        if self.step == "index_source":
            columns_count = event.get("total_columns", 0)
            self.console.print(
                f"[{check_color}]{check_mark}[/{check_color}] {self.step}  {self.object_name}/{self.variant}  columns={columns_count}"
            )
        elif self.step == "index_target":
            fields_count = event.get("total_fields", 0)
            self.console.print(
                f"[{check_color}]{check_mark}[/{check_color}] {self.step}  {self.object_name}/{self.variant}  fields={fields_count}"
            )
        elif self.step == "map":
            mapped_count = event.get("mapped", 0)
            unmapped_count = event.get("unmapped", 0) 
            to_audit_count = event.get("to_audit", 0)
            self.console.print(
                f"[{check_color}]{check_mark}[/{check_color}] {self.step}  {self.object_name}/{self.variant}  mapped={mapped_count}  unmapped={unmapped_count}  to_audit={to_audit_count}"
            )
        elif self.step == "transform":
            rows_in = event.get("rows_in", 0)
            rows_out = event.get("rows_out", 0)
            rows_rejected = event.get("rows_rejected", 0)
            self.console.print(
                f"[{check_color}]{check_mark}[/{check_color}] {self.step}  {self.object_name}/{self.variant}  in={rows_in}  out={rows_out}  rej={rows_rejected}"
            )

        # Input/Output paths
        input_file = event.get("input_file", "")
        output_file = event.get("output_file", "")
        if input_file:
            self.console.print(f"  in:  {self.normalize_path(Path(input_file))}")
        if output_file:
            self.console.print(f"  out: {self.normalize_path(Path(output_file))}")

        # Step-specific paths and information
        if self.step == "map":
            # Map-specific paths
            source_index = event.get("source_index", "")
            target_index = event.get("target_index", "")
            if source_index:
                self.console.print(f"  source: {self.normalize_path(Path(source_index))}")
            if target_index:
                self.console.print(f"  target: {self.normalize_path(Path(target_index))}")
            
            # Ruleset sources
            ruleset_sources = event.get("ruleset_sources", "")
            if ruleset_sources:
                self.console.print(f"  ruleset: {self.normalize_path(Path(ruleset_sources))}")
                
        elif self.step == "transform":
            # Transform-specific paths (no longer showing sap_csv as per requirement 4)
            input_raw = event.get("input_raw", "")
            mapping = event.get("mapping", "")
            snapshot_csv = event.get("snapshot_csv", "")
            rejects_csv = event.get("rejects_csv", "")
            template_used = event.get("template_used", "")
            
            if input_raw:
                self.console.print(f"  raw: {self.normalize_path(Path(input_raw))}")
            if mapping:
                self.console.print(f"  mapping: {self.normalize_path(Path(mapping))}")
            if snapshot_csv:
                self.console.print(f"  snap: {self.normalize_path(Path(snapshot_csv))}")
            if rejects_csv:
                self.console.print(f"  rej: {self.normalize_path(Path(rejects_csv))}")
            if template_used:
                self.console.print(f"  template: {self.normalize_path(Path(template_used)) if template_used != 'missing' else 'missing'}")

        # Structure (for index_target)
        if self.step == "index_target":
            structure = event.get("structure", "")
            if structure:
                self.console.print(f"  structure: {structure}")

            # Validation scaffold line
            validation_scaffold = event.get("validation_scaffold", "")
            rules_count = event.get("rules_count", 0)
            if validation_scaffold:
                # Determine status based on rules_count
                validation_status = "created" if rules_count > 0 else "skipped:exists"
                self.console.print(
                    f"  validation: rules={rules_count} → {validation_scaffold} ({validation_status})"
                )

        # Duration and warnings
        duration_ms = event.get("duration_ms", 0)
        self.console.print(f"  time: {duration_ms}ms")
        self.console.print(f"  warnings: {warnings_count}")

        # Preview table
        if not self.no_preview and preview_data:
            self._output_preview_table(preview_data)

    def _output_preview_table(self, preview_data: List[Dict]) -> None:
        """Output preview table for human format."""
        if not preview_data:
            return

        if self.step == "index_source":
            self._output_source_preview_table(preview_data)
        elif self.step == "index_target":
            self._output_target_preview_table(preview_data)
        elif self.step == "map":
            self._output_map_preview_table(preview_data)
        elif self.step == "transform":
            self._output_transform_preview_table(preview_data)

    def _output_source_preview_table(self, preview_data: List[Dict]) -> None:
        """Output preview table for index_source with first 8 headers."""
        table = Table(title="Headers (sample)")
        table.add_column("#", style="dim")
        table.add_column("field_name")
        table.add_column("dtype")
        table.add_column("nullable")
        table.add_column("example")

        # Show first 8 items
        for i, item in enumerate(preview_data[:8], 1):
            table.add_row(
                str(i),
                item.get("field_name", ""),
                item.get("dtype", ""),
                str(item.get("nullable", "")),
                str(item.get("example", "")),
            )

        self.console.print(table)

    def _output_target_preview_table(self, preview_data: List[Dict]) -> None:
        """Output preview table for index_target with first 8 fields."""
        table = Table(title="Fields (sample)")
        table.add_column("sap_field")
        table.add_column("field_description")
        table.add_column("mandatory")
        table.add_column("data_type")
        table.add_column("length")
        table.add_column("decimal")
        table.add_column("field_group")
        table.add_column("key")

        # Show first 8 items
        for item in preview_data[:8]:
            table.add_row(
                item.get("sap_field", ""),
                item.get("field_description", ""),
                str(item.get("mandatory", "")),
                item.get("data_type", ""),
                str(item.get("length", "")),
                str(item.get("decimal", "")),
                item.get("field_group", ""),
                str(item.get("key", "")),
            )

        self.console.print(table)

    def _output_map_preview_table(self, preview_data: List[Dict]) -> None:
        """Output preview table for map with first 8 mappings."""
        table = Table(title="Mappings (sample)")
        table.add_column("target_field")
        table.add_column("source_header")
        table.add_column("source_field_name")  # Always show field_name
        table.add_column("confidence")
        table.add_column("status")

        # Show first 8 items
        for item in preview_data[:8]:
            table.add_row(
                item.get("target_field", ""),
                item.get("source_header", ""),
                item.get("source_field_name", "field_name onbekend"),  # Always show field_name
                item.get("confidence", ""),
                item.get("status", ""),
            )

        self.console.print(table)

    def _output_transform_preview_table(self, preview_data: List[Dict]) -> None:
        """Output preview table for transform with first 8 columns of data."""
        table = Table(title="Transformed data (sample)")
        table.add_column("#", style="dim")
        
        # Get first 8 columns from preview data
        if preview_data:
            first_row = preview_data[0]
            column_names = list(first_row.keys())[:8]
            for col in column_names:
                table.add_column(col)

            # Show first 5 rows
            for i, item in enumerate(preview_data[:5], 1):
                row_data = [str(i)]
                for col in column_names:
                    value = str(item.get(col, ""))[:15]  # Truncate to 15 chars
                    row_data.append(value)
                table.add_row(*row_data)

        self.console.print(table)

    def log_event(
        self, event: Dict[str, Any], preview_data: Optional[List[Dict]] = None
    ) -> None:
        """Log an event to both file and stdout as configured."""
        # Add duration if not present
        if "duration_ms" not in event:
            event["duration_ms"] = self.get_duration_ms()

        # Normalize paths in event
        if "input_file" in event:
            event["input_file"] = self.normalize_path(Path(event["input_file"]))
        if "output_file" in event:
            event["output_file"] = self.normalize_path(Path(event["output_file"]))

        # Write to file
        self.write_jsonl_to_file(event)

        # Output to stdout
        self.output_to_stdout(event, preview_data)

    def log_error(self, error_event: Dict[str, Any]) -> None:
        """Log an error event."""
        error_event["duration_ms"] = self.get_duration_ms()

        # Normalize paths in error event
        if "path" in error_event:
            error_event["path"] = self.normalize_path(Path(error_event["path"]))

        self.write_jsonl_to_file(error_event)

        if self.stdout_format != "none":
            if self.stdout_format == "jsonl":
                jsonl_line = json.dumps(
                    error_event, ensure_ascii=False, separators=(",", ":")
                )
                print(jsonl_line)
            else:
                # Human format error - display structured error message
                error_msg = self._format_error_message(error_event)
                self.console.print(f"[red]✗[/red] Error: {error_msg}")

    def _format_error_message(self, error_event: Dict[str, Any]) -> str:
        """Format error message for human-readable output."""
        error_type = error_event.get("error", "unknown")

        if error_type == "missing_input":
            path = error_event.get("path", "unknown")
            return f"Input file not found: {path}"
        elif error_type == "missing_raw":
            expected_path = error_event.get("expected_path", "unknown")
            return f"Raw XLSX file not found: {expected_path}"
        elif error_type == "missing_mapping":
            expected_path = error_event.get("expected_path", "unknown")
            return f"Mapping file not found: {expected_path}"
        elif error_type == "missing_target_index":
            expected_path = error_event.get("expected_path", "unknown")
            return f"Target index file not found: {expected_path}"
        elif error_type == "no_headers":
            return "No valid headers found in the input file"
        elif error_type == "structure_not_found":
            variant = error_event.get("variant", "unknown")
            return f"Structure S_{variant.upper()} not found in target file"
        elif error_type == "exception":
            message = error_event.get("message", "Unknown exception")
            return f"Unexpected error: {message}"
        elif error_type == "would_overwrite":
            path = error_event.get("path")
            existing_files = error_event.get("existing_files", [])
            if existing_files:
                files_str = ", ".join(existing_files)
                return f"Output files exist and --force not specified: {files_str}"
            elif path:
                return f"Output file exists and --force not specified: {path}"
            else:
                return "Output files exist and --force not specified"
        elif error_type == "unsupported_format":
            path = error_event.get("path", "unknown")
            return f"Unsupported file format: {path}"
        else:
            return error_event.get("message", f"Unknown error type: {error_type}")
