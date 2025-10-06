#!/usr/bin/env python3
"""
Parsers for source file formats in transform-myd-minimal.

Contains parsers for:
- XLSX source headers
- SpreadsheetML (Excel 2003 XML) target fields with namespace support
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def read_excel_headers(
    path: Path,
    sheet: str = "Sheet1",
    header_row: int = 1,
    ignore_data_below: bool = True,
) -> List[str]:
    """
    Read Excel file headers from specified sheet and row.

    Args:
        path: Path to XLSX file
        sheet: Sheet name to read
        header_row: Row number containing headers (1-based)
        ignore_data_below: Whether to ignore data below headers

    Returns:
        List of header names
    """
    try:
        # Read just the header row
        df = pd.read_excel(
            path,
            sheet_name=sheet,
            header=header_row - 1,
            nrows=0 if ignore_data_below else None,
        )
        return list(df.columns)
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {path}")
    except Exception as e:
        raise Exception(f"Error reading Excel headers from {path}: {e}")


def read_excel_target_fields(
    path: Path,
    variant: str,
    sheet: str = "Field List",
) -> List[Dict[str, Any]]:
    """
    Read target field definitions from Excel file for F02 fallback.

    Expected columns in Excel file:
    - Sheet Name (or equivalent)
    - Group Name (or Field Group)
    - Field Description
    - Importance (Mandatory/Optional)
    - Type (Data Type)
    - Length
    - Decimal
    - SAP Structure (Table name)
    - SAP Field

    Args:
        path: Path to XLSX file
        variant: Variant name for table mapping
        sheet: Sheet name to read (default: "Field List")

    Returns:
        List of target field dictionaries with same structure as SpreadsheetML parser
    """
    try:
        # Read the Excel file
        df = pd.read_excel(path, sheet_name=sheet)

        # Column mapping for flexible header names
        column_mapping = {
            "sheet_name": ["Sheet Name", "sheet_name", "SheetName"],
            "field_group": ["Group Name", "field_group", "Group", "FieldGroup"],
            "field_description": [
                "Field Description",
                "field_description",
                "Description",
            ],
            "importance": ["Importance", "importance", "Mandatory"],
            "data_type": ["Type", "data_type", "DataType", "Data Type"],
            "length": ["Length", "length"],
            "decimal": ["Decimal", "decimal", "Decimals"],
            "sap_table": ["SAP Structure", "sap_table", "sap_structure", "Table"],
            "sap_field": ["SAP Field", "sap_field", "Field"],
        }

        # Find actual column names in the DataFrame
        actual_columns = {}
        for field_name, possible_names in column_mapping.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    actual_columns[field_name] = possible_name
                    break

            # If not found, try case-insensitive match
            if field_name not in actual_columns:
                for col in df.columns:
                    if any(col.lower() == name.lower() for name in possible_names):
                        actual_columns[field_name] = col
                        break

        # Verify we have the essential columns
        required_fields = ["field_description", "sap_field"]
        for field in required_fields:
            if field not in actual_columns:
                raise ValueError(
                    f"Required column not found for '{field}'. Available columns: {list(df.columns)}"
                )

        # Convert DataFrame to target field format
        target_fields = []
        for index, row in df.iterrows():
            # Extract importance/mandatory status
            importance = row.get(actual_columns.get("importance", ""), "").strip()
            mandatory = importance.lower() in ["mandatory", "true", "1", "yes"]

            # Determine if field is a key (typically mandatory + in key group)
            field_group = (
                row.get(actual_columns.get("field_group", ""), "").strip().lower()
            )
            key = mandatory and field_group == "key"

            # Handle decimal values
            decimal_val = row.get(actual_columns.get("decimal", ""), "")
            if pd.isna(decimal_val) or decimal_val == "" or decimal_val == "None":
                decimal_val = None

            # Handle length values
            length_val = row.get(actual_columns.get("length", ""), "")
            if pd.isna(length_val) or length_val == "":
                length_val = ""
            else:
                try:
                    length_val = str(int(float(length_val)))
                except (ValueError, TypeError):
                    length_val = str(length_val)

            # Create field dictionary matching XML parser output format
            field_dict = {
                "sap_field": str(row[actual_columns["sap_field"]]).strip(),
                "field_description": str(
                    row[actual_columns["field_description"]]
                ).strip(),
                "sap_table": str(
                    row.get(actual_columns.get("sap_table", ""), variant)
                ).strip(),
                "mandatory": mandatory,
                "field_group": field_group if field_group else "default",
                "key": key,
                "sheet_name": str(
                    row.get(actual_columns.get("sheet_name", ""), "Field List")
                ).strip(),
                "data_type": str(
                    row.get(actual_columns.get("data_type", ""), "Text")
                ).strip(),
                "length": length_val,
                "decimal": decimal_val,
                "field_count": index + 1,
            }

            target_fields.append(field_dict)

        return target_fields

    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {path}")
    except Exception as e:
        raise Exception(f"Error reading Excel target fields from {path}: {e}")


class SpreadsheetMLParser:
    """Parser for SpreadsheetML (Excel 2003 XML) format with namespace support."""

    def __init__(self, path: Path):
        """Initialize parser with XML file path."""
        self.path = path
        self.ns = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
        self.tree = None
        self.root = None
        self._load_xml()

    def _load_xml(self) -> None:
        """Load and parse the XML file."""
        try:
            self.tree = ET.parse(self.path)
            self.root = self.tree.getroot()
        except FileNotFoundError:
            raise FileNotFoundError(f"XML file not found: {self.path}")
        except Exception as e:
            raise Exception(f"Error parsing XML file {self.path}: {e}")

    def find_worksheet(self, worksheet_name: str) -> Optional[ET.Element]:
        """Find worksheet by name."""
        worksheets = self.root.findall(".//ss:Worksheet", self.ns)
        for ws in worksheets:
            name = ws.get(f'{{{self.ns["ss"]}}}Name', "")
            if name == worksheet_name:
                return ws
        return None

    def find_header_row(
        self, worksheet: ET.Element, expected_headers: List[str]
    ) -> Optional[int]:
        """
        Find header row by looking for expected header names (case-insensitive).

        Args:
            worksheet: Worksheet element
            expected_headers: List of expected header names to match

        Returns:
            Row number (0-based) if found, None otherwise
        """
        rows = worksheet.findall(".//ss:Row", self.ns)

        # Convert expected headers to lowercase for comparison
        expected_lower = [h.lower() for h in expected_headers]

        for row_idx, row in enumerate(rows):
            cells = self._parse_row_cells(row)
            if len(cells) >= len(expected_headers):
                # Check if this row contains our expected headers
                row_headers = [str(cell).lower() if cell else "" for cell in cells]

                # Count exact matches first
                exact_matches = sum(
                    1
                    for expected in expected_lower
                    if any(expected == actual for actual in row_headers)
                )

                # Count partial matches
                partial_matches = sum(
                    1
                    for expected in expected_lower
                    if any(
                        expected in actual or actual in expected
                        for actual in row_headers
                        if actual
                    )
                )

                # If we have most exact matches or good partial matches, this is our header row
                if (
                    exact_matches >= len(expected_headers) * 0.8
                    or partial_matches >= len(expected_headers) * 0.7
                ):
                    return row_idx

        return None

    def _parse_row_cells(self, row: ET.Element) -> List[Optional[str]]:
        """
        Parse cells from a row, handling ss:Index (sparse cells) and merges.

        Args:
            row: Row element

        Returns:
            List of cell values (None for empty cells)
        """
        cells = []
        current_col = 0

        for cell in row.findall("ss:Cell", self.ns):
            # Check if cell has an Index attribute (sparse cells)
            index = cell.get(f'{{{self.ns["ss"]}}}Index')
            if index:
                target_col = int(index) - 1  # Convert to 0-based
                # Fill gaps with None
                while current_col < target_col:
                    cells.append(None)
                    current_col += 1

            # Get cell data
            data_elem = cell.find("ss:Data", self.ns)
            cell_value = data_elem.text if data_elem is not None else None
            cells.append(cell_value)
            current_col += 1

        return cells

    def parse_target_fields(
        self,
        worksheet_name: str = "Field List",
        header_config: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parse target fields from the specified worksheet.

        Args:
            worksheet_name: Name of worksheet to parse
            header_config: Mapping of logical names to expected header text

        Returns:
            List of target field dictionaries
        """
        if header_config is None:
            header_config = {
                "sheet_name": "Sheet Name",
                "group_name": "Group Name",
                "description": "Field Description",
                "importance": "Importance",
                "type": "Type",
                "length": "Length",
                "decimal": "Decimal",
                "sap_table": "SAP Structure",
                "sap_field": "SAP Field",
            }

        # Find the worksheet
        worksheet = self.find_worksheet(worksheet_name)
        if worksheet is None:
            raise ValueError(f"Worksheet '{worksheet_name}' not found")

        # Find header row
        expected_headers = list(header_config.values())
        header_row_idx = self.find_header_row(worksheet, expected_headers)
        if header_row_idx is None:
            raise ValueError(
                f"Header row not found with expected headers: {expected_headers}"
            )

        # Get all rows
        rows = worksheet.findall(".//ss:Row", self.ns)
        header_row = rows[header_row_idx]
        header_cells = self._parse_row_cells(header_row)

        # Create column index mapping
        col_mapping = {}
        for logical_name, expected_text in header_config.items():
            for idx, cell_value in enumerate(header_cells):
                if cell_value and expected_text.lower() in cell_value.lower():
                    col_mapping[logical_name] = idx
                    break

        # Parse data rows
        target_fields = []
        for row in rows[header_row_idx + 1 :]:
            cells = self._parse_row_cells(row)

            # Skip empty rows
            if not any(cell for cell in cells if cell and str(cell).strip()):
                continue

            # Extract field data
            field_data = {}
            for logical_name, col_idx in col_mapping.items():
                if col_idx < len(cells):
                    field_data[logical_name] = cells[col_idx]
                else:
                    field_data[logical_name] = None

            # Skip rows without required data
            if not field_data.get("sap_field") or not field_data.get("sap_table"):
                continue

            # Apply normalization
            sap_table = field_data.get("sap_table", "")
            sap_field = field_data.get("sap_field", "")

            # Remove prefix (e.g., "S_") from table name for internal use
            internal_table = sap_table
            if sap_table.startswith("S_"):
                internal_table = sap_table[2:]

            # Create internal and transformer IDs
            field_data["internal_table"] = internal_table
            field_data["internal_id"] = f"{internal_table}.{sap_field}"
            field_data["transformer_id"] = f"{sap_table}#{sap_field}"

            target_fields.append(field_data)

        return target_fields


def parse_source_and_targets(
    source_xlsx_path: Path,
    target_xml_path: Path,
    source_config: Optional[Dict[str, Any]] = None,
    target_config: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Parse both source headers and target fields from the respective files.

    Args:
        source_xlsx_path: Path to source XLSX file
        target_xml_path: Path to target XML file
        source_config: Configuration for source parsing
        target_config: Configuration for target parsing

    Returns:
        Tuple of (source_headers, target_fields)
    """
    # Default configurations
    if source_config is None:
        source_config = {"sheet": "Sheet1", "header_row": 1, "ignore_data_below": True}

    if target_config is None:
        target_config = {
            "worksheet_name": "Field List",
            "header_match": {
                "sheet_name": "Sheet Name",
                "group_name": "Group Name",
                "description": "Field Description",
                "importance": "Importance",
                "type": "Type",
                "length": "Length",
                "decimal": "Decimal",
                "sap_table": "SAP Structure",
                "sap_field": "SAP Field",
            },
        }

    # Parse source headers
    source_headers = read_excel_headers(
        source_xlsx_path,
        source_config["sheet"],
        source_config["header_row"],
        source_config["ignore_data_below"],
    )

    # Parse target fields
    xml_parser = SpreadsheetMLParser(target_xml_path)
    target_fields = xml_parser.parse_target_fields(
        target_config["worksheet_name"], target_config["header_match"]
    )

    return source_headers, target_fields
