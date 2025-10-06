#!/usr/bin/env python3
"""
Mapping Editor Web UI for transform-myd-minimal.

A Streamlit-based web interface for:
- Uploading and editing mapping files
- Validating mappings with error display
- Downloading/exporting mapping files
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


try:
    import streamlit as st
except ImportError:
    print("ERROR: Streamlit is not installed.", file=sys.stderr)
    print("Install it with: pip install streamlit", file=sys.stderr)
    sys.exit(1)


def validate_mapping(mapping_df: pd.DataFrame) -> Dict[str, List[str]]:
    """Validate a mapping DataFrame.

    Args:
        mapping_df: DataFrame with mapping data

    Returns:
        Dictionary with 'errors' and 'warnings' lists
    """
    errors = []
    warnings = []

    # Check for required columns
    required_columns = ["Source Field", "Target Field", "Transformation"]
    missing_columns = [col for col in required_columns if col not in mapping_df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return {"errors": errors, "warnings": warnings}

    # Check for empty source fields
    empty_source = mapping_df["Source Field"].isna() | (mapping_df["Source Field"] == "")
    if empty_source.any():
        row_indices = mapping_df[empty_source].index.tolist()
        errors.append(f"Empty source field at rows: {', '.join(map(str, row_indices))}")

    # Check for empty target fields
    empty_target = mapping_df["Target Field"].isna() | (mapping_df["Target Field"] == "")
    if empty_target.any():
        row_indices = mapping_df[empty_target].index.tolist()
        errors.append(f"Empty target field at rows: {', '.join(map(str, row_indices))}")

    # Check for duplicate source fields
    source_counts = mapping_df["Source Field"].value_counts()
    duplicates = source_counts[source_counts > 1]
    if len(duplicates) > 0:
        warnings.append(f"Duplicate source fields: {', '.join(duplicates.index.tolist())}")

    # Check for duplicate target fields
    target_counts = mapping_df["Target Field"].value_counts()
    duplicates = target_counts[target_counts > 1]
    if len(duplicates) > 0:
        warnings.append(f"Duplicate target fields: {', '.join(duplicates.index.tolist())}")

    # Check for empty transformations
    empty_transform = mapping_df["Transformation"].isna() | (mapping_df["Transformation"] == "")
    if empty_transform.any():
        row_indices = mapping_df[empty_transform].index.tolist()
        warnings.append(f"Empty transformation at rows: {', '.join(map(str, row_indices))}")

    # Check for valid transformation types
    valid_transformations = ["copy", "constant", "derive", "lookup", "concatenate", "split", "transform"]
    invalid_transforms = mapping_df[
        ~mapping_df["Transformation"].isin(valid_transformations + ["", None])
    ]
    if len(invalid_transforms) > 0:
        row_indices = invalid_transforms.index.tolist()
        warnings.append(
            f"Invalid transformation types at rows: {', '.join(map(str, row_indices))}. "
            f"Valid types: {', '.join(valid_transformations)}"
        )

    return {"errors": errors, "warnings": warnings}


def export_to_yaml(mapping_df: pd.DataFrame) -> str:
    """Export mapping DataFrame to YAML format.

    Args:
        mapping_df: DataFrame with mapping data

    Returns:
        YAML string
    """
    mappings = []
    for _, row in mapping_df.iterrows():
        # Skip empty rows
        if pd.isna(row.get("Source Field")) or row.get("Source Field") == "":
            continue

        mapping = {
            "source_field": row.get("Source Field", ""),
            "target_field": row.get("Target Field", ""),
            "transformation": row.get("Transformation", "copy"),
        }

        if "Note" in row and pd.notna(row["Note"]) and row["Note"] != "":
            mapping["note"] = row["Note"]

        mappings.append(mapping)

    data = {
        "metadata": {
            "generated_by": "Mapping Editor Web UI",
            "version": "1.0",
        },
        "mappings": mappings,
    }

    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Mapping Editor",
        page_icon="🔄",
        layout="wide",
    )

    st.title("🔄 Mapping Editor")
    st.markdown("Upload, edit, and validate field mappings for data migration")

    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    transformation_types = ["copy", "constant", "derive", "lookup", "concatenate", "split", "transform"]
    
    # File upload section
    st.header("1. Upload Mapping File")
    
    uploaded_file = st.file_uploader(
        "Upload an existing mapping file (Excel or YAML)",
        type=["xlsx", "xls", "yaml", "yml"],
        help="Upload an Excel template or YAML mapping file to edit",
    )

    # Initialize session state for mapping data
    if "mapping_df" not in st.session_state:
        # Create empty DataFrame with default structure
        st.session_state.mapping_df = pd.DataFrame(
            columns=["Source Field", "Target Field", "Transformation", "Note"]
        )
        # Add a few empty rows
        for _ in range(5):
            st.session_state.mapping_df = pd.concat(
                [
                    st.session_state.mapping_df,
                    pd.DataFrame(
                        [["", "", "", ""]],
                        columns=["Source Field", "Target Field", "Transformation", "Note"],
                    ),
                ],
                ignore_index=True,
            )

    # Load uploaded file
    if uploaded_file is not None:
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        try:
            if file_extension in [".xlsx", ".xls"]:
                # Load Excel file
                df = pd.read_excel(uploaded_file)
                
                # Check if it has the expected columns
                expected_cols = ["Source Field", "Target Field", "Transformation", "Note"]
                if all(col in df.columns for col in expected_cols[:3]):  # At least first 3 required
                    st.session_state.mapping_df = df
                    st.success(f"✅ Loaded {len(df)} mappings from Excel file")
                else:
                    st.error(f"❌ Excel file must have columns: {', '.join(expected_cols[:3])}")
                    
            elif file_extension in [".yaml", ".yml"]:
                # Load YAML file
                data = yaml.safe_load(uploaded_file)
                
                mappings = data.get("mappings", [])
                rows = []
                for mapping in mappings:
                    rows.append(
                        {
                            "Source Field": mapping.get("source_field", ""),
                            "Target Field": mapping.get("target_field", ""),
                            "Transformation": mapping.get("transformation", ""),
                            "Note": mapping.get("note", ""),
                        }
                    )
                
                if rows:
                    st.session_state.mapping_df = pd.DataFrame(rows)
                    st.success(f"✅ Loaded {len(rows)} mappings from YAML file")
                else:
                    st.error("❌ No mappings found in YAML file")
                    
        except Exception as e:
            st.error(f"❌ Error loading file: {str(e)}")

    # Editing section
    st.header("2. Edit Mappings")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("Edit mappings in the table below. Use the controls to add or remove rows.")
    
    with col2:
        if st.button("➕ Add Row"):
            new_row = pd.DataFrame(
                [["", "", "", ""]],
                columns=["Source Field", "Target Field", "Transformation", "Note"],
            )
            st.session_state.mapping_df = pd.concat(
                [st.session_state.mapping_df, new_row],
                ignore_index=True,
            )
            st.rerun()
        
        if st.button("🗑️ Remove Empty Rows"):
            # Remove rows where both source and target are empty
            mask = (
                (st.session_state.mapping_df["Source Field"].notna())
                & (st.session_state.mapping_df["Source Field"] != "")
            ) | (
                (st.session_state.mapping_df["Target Field"].notna())
                & (st.session_state.mapping_df["Target Field"] != "")
            )
            st.session_state.mapping_df = st.session_state.mapping_df[mask].reset_index(drop=True)
            st.rerun()

    # Display editable dataframe
    edited_df = st.data_editor(
        st.session_state.mapping_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Source Field": st.column_config.TextColumn(
                "Source Field",
                help="Name of the source field",
                required=True,
            ),
            "Target Field": st.column_config.TextColumn(
                "Target Field",
                help="Name of the target field",
                required=True,
            ),
            "Transformation": st.column_config.SelectboxColumn(
                "Transformation",
                help="Type of transformation to apply",
                options=transformation_types,
                required=False,
            ),
            "Note": st.column_config.TextColumn(
                "Note",
                help="Optional notes about this mapping",
                required=False,
            ),
        },
        hide_index=False,
    )

    # Update session state with edited data
    st.session_state.mapping_df = edited_df

    # Validation section
    st.header("3. Validate Mappings")
    
    if st.button("🔍 Validate", type="primary"):
        validation_result = validate_mapping(st.session_state.mapping_df)
        
        if validation_result["errors"]:
            st.error("❌ Validation Errors Found:")
            for error in validation_result["errors"]:
                st.error(f"• {error}")
        else:
            st.success("✅ No validation errors found!")
        
        if validation_result["warnings"]:
            st.warning("⚠️ Validation Warnings:")
            for warning in validation_result["warnings"]:
                st.warning(f"• {warning}")

    # Statistics
    st.sidebar.header("Statistics")
    non_empty_rows = st.session_state.mapping_df[
        (st.session_state.mapping_df["Source Field"].notna())
        & (st.session_state.mapping_df["Source Field"] != "")
    ]
    st.sidebar.metric("Total Mappings", len(non_empty_rows))
    st.sidebar.metric("Total Rows", len(st.session_state.mapping_df))
    
    # Transformation statistics
    if len(non_empty_rows) > 0:
        transform_counts = non_empty_rows["Transformation"].value_counts()
        st.sidebar.markdown("**Transformations:**")
        for transform, count in transform_counts.items():
            if pd.notna(transform) and transform != "":
                st.sidebar.text(f"• {transform}: {count}")

    # Export section
    st.header("4. Export Mappings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Download as Excel"):
            # Create Excel file
            output = st.session_state.mapping_df.to_excel(index=False)
            
            # For Streamlit, we need to use download_button with bytes
            excel_bytes = st.session_state.mapping_df.to_excel(index=False).encode() if isinstance(
                st.session_state.mapping_df.to_excel(index=False), str
            ) else st.session_state.mapping_df.to_excel(index=False)
            
            # Use BytesIO to create Excel file
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                st.session_state.mapping_df.to_excel(writer, index=False, sheet_name='Mapping')
            
            st.download_button(
                label="⬇️ Download Excel File",
                data=buffer.getvalue(),
                file_name="mapping_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    
    with col2:
        if st.button("📥 Download as YAML"):
            yaml_content = export_to_yaml(st.session_state.mapping_df)
            
            st.download_button(
                label="⬇️ Download YAML File",
                data=yaml_content,
                file_name="mapping_export.yaml",
                mime="text/yaml",
            )

    # Footer
    st.markdown("---")
    st.markdown(
        "**Mapping Editor v1.0** | Part of transform-myd-minimal | "
        "See [documentation](../README.md) for more information"
    )


if __name__ == "__main__":
    main()
