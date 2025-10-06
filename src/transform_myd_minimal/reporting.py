#!/usr/bin/env python3
"""
HTML reporting module for transform-myd-minimal.

Provides self-contained HTML report generation for all F01-F04 steps
with embedded JSON data, inline CSS/JS, and client-side UI features.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def ensure_json_serializable(obj: Any) -> Any:
    """
    Ensure an object is JSON serializable by converting non-serializable types.

    Args:
        obj: Object to make JSON serializable

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, (dict, list, tuple)):
        if isinstance(obj, dict):
            return {str(k): ensure_json_serializable(v) for k, v in obj.items()}
        else:
            return [ensure_json_serializable(item) for item in obj]
    elif isinstance(obj, Path):
        # Use as_posix() for cross-platform compatibility (always forward slashes)
        return obj.as_posix()
    elif isinstance(obj, (pd.Timestamp, pd.NaT.__class__)):
        return str(obj) if pd.notna(obj) else None
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, "__dict__"):
        return ensure_json_serializable(obj.__dict__)
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)


def _determine_field_type(
    field_name: str, validation_rules: Optional[Dict] = None
) -> str:
    """
    Determine field type based on validation.yaml rules or fallback heuristics.

    Args:
        field_name: Name of the field
        validation_rules: Optional validation rules dict

    Returns:
        Field type: string, int, decimal, date, or time
    """
    # Check validation.yaml rules first
    if validation_rules and field_name.lower() in validation_rules:
        vtype = validation_rules[field_name.lower()].get("type", "").lower()
        if vtype in {"string", "int", "decimal", "date", "time"}:
            return vtype

    # Fallback heuristics based on field name
    field_lower = field_name.lower()
    if any(x in field_lower for x in ["decimal", "number", "num", "decimals"]):
        return "decimal"
    elif any(x in field_lower for x in ["int", "integer"]):
        return "int"
    elif "date" in field_lower:
        return "date"
    elif "time" in field_lower:
        return "time"
    else:
        return "string"


def _parse_field_by_type(
    series: pd.Series, field_type: str
) -> tuple[pd.Series, pd.Series]:
    """
    Parse series values according to field type and return parsed values and validity mask.

    Args:
        series: Input pandas Series
        field_type: Type to parse as (string, int, decimal, date, time)

    Returns:
        Tuple of (parsed_series, is_valid_mask)
    """
    if field_type == "decimal":
        parsed = pd.to_numeric(series, errors="coerce")
        is_valid = pd.notna(parsed)
        return parsed, is_valid
    elif field_type == "int":
        parsed = pd.to_numeric(series, errors="coerce")
        # For int, also check if values are actually integers
        is_valid = pd.notna(parsed) & (parsed == parsed.astype(int, errors="ignore"))
        return parsed, is_valid
    elif field_type == "date":
        # Try to parse YYYYMMDD format
        parsed = pd.to_datetime(series, format="%Y%m%d", errors="coerce")
        is_valid = pd.notna(parsed)
        return parsed, is_valid
    elif field_type == "time":
        # Parse HHMMSS to seconds
        def parse_time_to_seconds(time_str):
            if pd.isna(time_str) or str(time_str).strip() == "":
                return np.nan
            try:
                time_str = str(time_str).strip()
                if len(time_str) == 6:  # HHMMSS
                    h, m, s = int(time_str[:2]), int(time_str[2:4]), int(time_str[4:6])
                    if 0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59:
                        return h * 3600 + m * 60 + s
                return np.nan
            except (ValueError, TypeError):
                return np.nan

        parsed = series.apply(parse_time_to_seconds)
        is_valid = pd.notna(parsed)
        return parsed, is_valid
    else:  # string
        # For strings, everything is valid except null/empty
        parsed = series.astype(str)
        is_valid = (series.notna()) & (series.astype(str).str.strip() != "")
        return parsed, is_valid


def _calculate_histogram(
    series: pd.Series, field_type: str, parsed_series: pd.Series
) -> Dict[str, Any]:
    """
    Calculate histogram data based on field type.

    Args:
        series: Original series
        field_type: Field type (string, int, decimal, date, time)
        parsed_series: Parsed series values

    Returns:
        Dictionary with histogram data
    """
    valid_data = parsed_series[pd.notna(parsed_series)]

    if len(valid_data) == 0:
        return {"bins": [], "counts": []}

    if field_type in ["int", "decimal"]:
        # Numeric histogram with 12 bins
        try:
            hist, bin_edges = np.histogram(valid_data, bins=12)
            bins = [
                f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}" for i in range(len(hist))
            ]
            return {"bins": bins, "counts": hist.tolist()}
        except Exception:
            return {"bins": [], "counts": []}
    elif field_type == "date":
        # Group by month YYYY-MM
        try:
            months = valid_data.dt.strftime("%Y-%m")
            month_counts = months.value_counts().head(24).sort_index()
            return {
                "bins": month_counts.index.tolist(),
                "counts": month_counts.values.tolist(),
                "type": "monthly",
            }
        except Exception:
            return {"bins": [], "counts": []}
    elif field_type == "time":
        # Histogram on seconds (0-86400)
        try:
            hist, bin_edges = np.histogram(valid_data, bins=12, range=(0, 86400))
            bins = [
                f"{int(bin_edges[i])//3600:02d}:{(int(bin_edges[i])%3600)//60:02d}-{int(bin_edges[i+1])//3600:02d}:{(int(bin_edges[i+1])%3600)//60:02d}"
                for i in range(len(hist))
            ]
            return {"bins": bins, "counts": hist.tolist()}
        except Exception:
            return {"bins": [], "counts": []}
    else:  # string
        # Histogram on string length
        try:
            lengths = series[pd.notna(series)].astype(str).str.len()
            if len(lengths) > 0:
                hist, bin_edges = np.histogram(lengths, bins=12)
                bins = [
                    f"{int(bin_edges[i])}-{int(bin_edges[i+1])}"
                    for i in range(len(hist))
                ]
                return {"bins": bins, "counts": hist.tolist()}
            return {"bins": [], "counts": []}
        except Exception:
            return {"bins": [], "counts": []}


def profile_series(
    name: str,
    series: pd.Series,
    field_type: str,
    validation_rules: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Profile a pandas Series and return comprehensive statistics.

    Args:
        name: Name of the field
        series: Pandas Series to profile
        field_type: Field type (string, int, decimal, date, time)
        validation_rules: Optional validation rules for the field

    Returns:
        Dictionary with profiling results
    """
    # Limit to 100,000 samples for performance
    if len(series) > 100_000:
        series = series.sample(100_000, random_state=0)

    # Basic counts
    total_count = len(series)
    missing_count = series.isna().sum() + (series.astype(str).str.strip() == "").sum()
    count = total_count - missing_count

    # Parse by type and determine validity
    parsed_series, is_valid = _parse_field_by_type(series, field_type)
    invalid_count = count - is_valid.sum()

    # Unique values
    unique_count = series[
        pd.notna(series) & (series.astype(str).str.strip() != "")
    ].nunique()
    unique_ratio = unique_count / count if count > 0 else 0

    # Top values (limited to 10)
    try:
        top_values_series = series[
            pd.notna(series) & (series.astype(str).str.strip() != "")
        ]
        top_values = top_values_series.value_counts().head(10)
        top_values_list = [
            {"value": str(val), "count": int(count)}
            for val, count in top_values.items()
        ]
    except Exception:
        top_values_list = []

    # Calculate histogram
    histogram = _calculate_histogram(series, field_type, parsed_series)

    # Quality score calculation
    missing_pct = missing_count / total_count if total_count > 0 else 0
    invalid_pct = invalid_count / total_count if total_count > 0 else 0
    dup_pct = 1 - unique_ratio
    quality_score = max(
        0, min(100, 100 - (missing_pct * 40 + invalid_pct * 40 + dup_pct * 20))
    )

    # Base profile
    profile = {
        "field": name,
        "type": field_type,
        "count": int(count),
        "missing": int(missing_count),
        "invalid": int(invalid_count),
        "unique": int(unique_count),
        "unique_ratio": round(unique_ratio, 4),
        "quality_score": round(quality_score, 2),
        "missing_pct": round(missing_pct * 100, 2),
        "invalid_pct": round(invalid_pct * 100, 2),
        "unique_pct": round(unique_ratio * 100, 2),
        "top_values": top_values_list,
        "histogram": histogram,
    }

    # Type-specific statistics
    valid_data = parsed_series[pd.notna(parsed_series) & is_valid]

    if field_type == "string":
        # String-specific stats
        string_data = series[
            pd.notna(series) & (series.astype(str).str.strip() != "")
        ].astype(str)
        if len(string_data) > 0:
            lengths = string_data.str.len()
            profile["length"] = {
                "min": int(lengths.min()),
                "p50": int(lengths.median()),
                "p95": int(lengths.quantile(0.95)),
                "max": int(lengths.max()),
                "mean": round(lengths.mean(), 2),
            }

            # Whitespace issues
            profile["whitespace_issues"] = {
                "leading_or_trailing": int(
                    (string_data.str.strip() != string_data).sum()
                )
            }

            # Case mix analysis
            non_empty = string_data[string_data.str.len() > 0]
            if len(non_empty) > 0:
                upper_ratio = (non_empty.str.isupper()).mean()
                lower_ratio = (non_empty.str.islower()).mean()
                mixed_ratio = 1 - upper_ratio - lower_ratio

                profile["case_mix"] = {
                    "upper_ratio": round(upper_ratio, 4),
                    "lower_ratio": round(lower_ratio, 4),
                    "mixed_ratio": round(mixed_ratio, 4),
                }

                # Character analysis
                digit_ratios = [
                    len(re.findall(r"\d", s)) / len(s) if len(s) > 0 else 0
                    for s in non_empty
                ]
                alpha_ratios = [
                    len(re.findall(r"[A-Za-z]", s)) / len(s) if len(s) > 0 else 0
                    for s in non_empty
                ]

                profile["digit_ratio"] = round(np.mean(digit_ratios), 4)
                profile["alpha_ratio"] = round(np.mean(alpha_ratios), 4)

    elif field_type in ["int", "decimal"]:
        # Numeric stats
        if len(valid_data) > 0:
            profile["numeric"] = {
                "min": float(valid_data.min()),
                "p25": float(valid_data.quantile(0.25)),
                "p50": float(valid_data.median()),
                "p75": float(valid_data.quantile(0.75)),
                "p95": float(valid_data.quantile(0.95)),
                "max": float(valid_data.max()),
                "mean": float(valid_data.mean()),
                "std": float(valid_data.std()),
            }

    elif field_type == "date":
        # Date stats
        if len(valid_data) > 0:
            profile["date"] = {
                "min": valid_data.min().strftime("%Y%m%d"),
                "max": valid_data.max().strftime("%Y%m%d"),
                "by_month": histogram.get("bins", []),
            }

    elif field_type == "time":
        # Time stats
        if len(valid_data) > 0:

            def seconds_to_hhmmss(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                return f"{h:02d}{m:02d}{s:02d}"

            profile["time"] = {
                "min": seconds_to_hhmmss(valid_data.min()),
                "max": seconds_to_hhmmss(valid_data.max()),
            }
            # Also include numeric stats for time as seconds
            profile["numeric"] = {
                "min": float(valid_data.min()),
                "p25": float(valid_data.quantile(0.25)),
                "p50": float(valid_data.median()),
                "p75": float(valid_data.quantile(0.75)),
                "p95": float(valid_data.quantile(0.95)),
                "max": float(valid_data.max()),
                "mean": float(valid_data.mean()),
                "std": float(valid_data.std()),
            }

    return profile


def profile_dataframe(
    df: pd.DataFrame,
    validation_rules: Optional[Dict] = None,
    field_types: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Profile all columns in a DataFrame.

    Args:
        df: DataFrame to profile
        validation_rules: Optional validation rules mapping field names to rules
        field_types: Optional mapping of field names to types

    Returns:
        Dictionary with field_profiles for all columns
    """
    profiles = {}

    for col in df.columns:
        # Determine field type
        if field_types and col in field_types:
            field_type = field_types[col]
        else:
            field_type = _determine_field_type(col, validation_rules)

        # Profile the column
        profiles[col] = profile_series(col, df[col], field_type, validation_rules)

    return profiles


def write_html_report(summary: Dict[str, Any], out_html: Path, title: str) -> None:
    """
    Write a self-contained HTML report with embedded JSON data.

    Args:
        summary: Data dictionary to embed and display
        out_html: Output HTML file path
        title: Title for the HTML report
    """
    # Ensure summary is JSON serializable
    clean_summary = ensure_json_serializable(summary)

    # Escape JSON for HTML embedding (prevent </script> breaking)
    json_data = json.dumps(clean_summary, ensure_ascii=False, indent=2)
    escaped_json = json_data.replace("</script>", '</scr" + "ipt>')

    # Determine step type and generate appropriate content
    _step = summary.get("step", "unknown")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 30px;
            padding-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 2.2em;
        }}
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 1.1em;
            margin: 5px 0;
        }}
        .kpi-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .kpi-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .kpi-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .chart-container {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .bar-chart {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .bar-item {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .bar-label {{
            min-width: 120px;
            font-size: 0.9em;
            color: #555;
        }}
        .bar-visual {{
            flex-grow: 1;
            height: 25px;
            background: #e9ecef;
            border-radius: 12px;
            position: relative;
            overflow: hidden;
        }}
        .bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 12px;
            transition: width 0.3s ease;
        }}
        .bar-value {{
            min-width: 60px;
            text-align: right;
            font-weight: bold;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
            cursor: pointer;
            user-select: none;
            position: relative;
        }}
        th:hover {{
            background: #e9ecef;
        }}
        th.sortable:after {{
            content: '↕';
            position: absolute;
            right: 8px;
            opacity: 0.5;
        }}
        th.sort-asc:after {{
            content: '↑';
            opacity: 1;
        }}
        th.sort-desc:after {{
            content: '↓';
            opacity: 1;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .search-box {{
            margin-bottom: 15px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            width: 300px;
            font-size: 14px;
        }}
        .controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .download-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
            display: inline-block;
        }}
        .download-btn:hover {{
            background: #218838;
        }}
        .list-container {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        .list-item {{
            padding: 5px 10px;
            margin: 3px 0;
            background: white;
            border-radius: 3px;
            border-left: 3px solid #667eea;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 0.9em;
        }}
        .csv-requirements {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin-top: 20px;
        }}
        .csv-requirements h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .csv-requirements ul {{
            margin-bottom: 0;
        }}
        .hidden {{
            display: none;
        }}
        .profiling-table {{
            margin-top: 20px;
        }}
        .profiling-row {{
            cursor: pointer;
            transition: background-color 0.2s;
        }}
        .profiling-row:hover {{
            background-color: #f0f8ff;
        }}
        .profiling-row.selected {{
            background-color: #e6f3ff;
            border-left: 3px solid #667eea;
        }}
        .profiling-detail {{
            display: none;
            margin-top: 15px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .profiling-detail.show {{
            display: block;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 15px;
        }}
        .detail-section h4 {{
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        .histogram-container {{
            margin: 15px 0;
        }}
        .histogram-bar {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .histogram-label {{
            min-width: 100px;
            font-size: 0.85em;
            color: #555;
        }}
        .histogram-visual {{
            flex-grow: 1;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            margin: 0 10px;
            position: relative;
            overflow: hidden;
        }}
        .histogram-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 10px;
            transition: width 0.3s ease;
        }}
        .histogram-value {{
            min-width: 40px;
            text-align: right;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin: 10px 0;
        }}
        .stats-item {{
            text-align: center;
            padding: 8px;
            background: white;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }}
        .stats-value {{
            font-weight: bold;
            font-size: 1.1em;
            color: #2c3e50;
        }}
        .stats-label {{
            font-size: 0.8em;
            color: #666;
            margin-top: 2px;
        }}
        .top-values-table {{
            width: 100%;
            margin-top: 10px;
        }}
        .top-values-table th, .top-values-table td {{
            padding: 6px 10px;
            font-size: 0.9em;
        }}
        .type-filter {{
            margin-bottom: 15px;
        }}
        .type-filter select {{
            padding: 5px 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle" id="subtitle"></div>
            <div class="subtitle" id="metadata"></div>
        </div>
        
        <div class="kpi-cards" id="kpi-cards"></div>
        
        <div class="section" id="chart-section">
            <h2>Distribution</h2>
            <div class="chart-container">
                <div class="bar-chart" id="bar-chart"></div>
            </div>
        </div>
        
        <div id="sections-container"></div>
        
        <div class="footer" id="footer">
            <p>Generated: <span id="timestamp"></span></p>
        </div>
    </div>

    <script type="application/json" id="data">{escaped_json}</script>

    <script>
        // Load and parse embedded data
        const data = JSON.parse(document.getElementById('data').textContent);
        
        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {{
            initializePage(data);
        }});
        
        function initializePage(data) {{
            renderHeader(data);
            renderKPIs(data);
            renderCharts(data);
            renderTables(data);
            renderLists(data);
            renderFooter(data);
            
            // Show data profiling for F04 steps
            if (data.step === 'raw_validation' || data.step === 'post_transform_validation') {{
                renderDataProfiling(data);
            }}
            
            // Show CSV requirements for F04 POST step
            if (data.step === 'post_transform_validation') {{
                renderCSVRequirements();
            }}
        }}
        
        function renderHeader(data) {{
            let subtitle = data.step;
            if (data.structure) {{
                subtitle += ' · ' + data.structure;
            }}
            if (data.object && data.variant) {{
                subtitle += ' · ' + data.object + '/' + data.variant;
            }}
            document.getElementById('subtitle').textContent = subtitle;
            
            let metadata = '';
            if (data.input_file) {{
                metadata += 'Input: ' + data.input_file;
            }}
            if (data.template_used) {{
                metadata += (metadata ? ' | ' : '') + 'Template: ' + data.template_used;
            }}
            document.getElementById('metadata').textContent = metadata;
        }}
        
        function renderKPIs(data) {{
            const container = document.getElementById('kpi-cards');
            const kpis = getKPIs(data);
            
            container.innerHTML = kpis.map(kpi =>
                `<div class="kpi-card">
                    <div class="kpi-value">${{kpi.value}}</div>
                    <div class="kpi-label">${{kpi.label}}</div>
                </div>`
            ).join('');
        }}
        
        function getKPIs(data) {{
            const step = data.step;
            
            if (step === 'index_source') {{
                return [
                    {{value: data.total_columns || 0, label: 'Total Columns'}},
                    {{value: data.duplicates?.length || 0, label: 'Duplicates'}},
                    {{value: data.empty_headers || 0, label: 'Empty Headers'}}
                ];
            }} else if (step === 'index_target') {{
                return [
                    {{value: data.total_fields || 0, label: 'Total Fields'}},
                    {{value: data.mandatory || 0, label: 'Mandatory'}},
                    {{value: data.keys || 0, label: 'Keys'}}
                ];
            }} else if (step === 'map') {{
                return [
                    {{value: data.mapped || 0, label: 'Mapped'}},
                    {{value: data.unmapped || 0, label: 'Unmapped'}},
                    {{value: data.to_audit || 0, label: 'To Audit'}},
                    {{value: data.unused_sources || 0, label: 'Unused Sources'}}
                ];
            }} else if (step === 'raw_validation') {{
                return [
                    {{value: data.rows_in || 0, label: 'Rows In'}},
                    {{value: Object.keys(data.missing_sources || {{}}).length, label: 'Missing Sources'}}
                ];
            }} else if (step === 'post_transform_validation') {{
                return [
                    {{value: data.rows_in || 0, label: 'Rows In'}},
                    {{value: data.rows_out || 0, label: 'Rows Out'}},
                    {{value: data.rows_rejected || 0, label: 'Rejected'}},
                    {{value: ((data.mapped_coverage || 0) * 100).toFixed(1) + '%', label: 'Coverage'}}
                ];
            }}
            return [];
        }}
        
        function renderCharts(data) {{
            const container = document.getElementById('bar-chart');
            const chartData = getChartData(data);
            
            if (chartData.length === 0) {{
                document.getElementById('chart-section').style.display = 'none';
                return;
            }}
            
            const maxValue = Math.max(...chartData.map(item => item.value));
            
            container.innerHTML = chartData.map(item => {{
                const percentage = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
                return `<div class="bar-item">
                    <div class="bar-label">${{item.label}}</div>
                    <div class="bar-visual">
                        <div class="bar-fill" style="width: ${{percentage}}%"></div>
                    </div>
                    <div class="bar-value">${{item.value}}</div>
                </div>`;
            }}).join('');
        }}
        
        function getChartData(data) {{
            const step = data.step;
            
            if (step === 'index_target' && data.groups) {{
                return Object.entries(data.groups)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10)
                    .map(([key, value]) => ({{label: key, value}}));
            }} else if (step === 'raw_validation' && data.null_rate_by_source) {{
                return Object.entries(data.null_rate_by_source)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10)
                    .map(([key, value]) => ({{label: key, value: (value * 100).toFixed(1) + '%'}}));
            }} else if (step === 'post_transform_validation' && data.errors_by_rule) {{
                return Object.entries(data.errors_by_rule)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10)
                    .map(([key, value]) => ({{label: key, value}}));
            }}
            return [];
        }}
        
        function renderTables(data) {{
            const container = document.getElementById('sections-container');
            const tables = getTables(data);
            
            tables.forEach(table => {{
                const sectionHtml = `
                    <div class="section">
                        <h2>${{table.title}}</h2>
                        <div class="controls">
                            <input type="text" class="search-box" placeholder="Search ${{table.title.toLowerCase()}}..."
                                   onkeyup="filterTable(this, '${{table.id}}')">
                            <button class="download-btn" onclick="downloadCSV('${{table.id}}', '${{table.title}}')">
                                Download CSV
                            </button>
                        </div>
                        <table id="${{table.id}}">
                            <thead>
                                <tr>
                                    ${{table.headers.map((h, i) =>
                                        `<th class="sortable" onclick="sortTable('${{table.id}}', ${{i}})">${{h}}</th>`
                                    ).join('')}}
                                </tr>
                            </thead>
                            <tbody>
                                ${{table.rows.map(row =>
                                    `<tr>${{row.map(cell => `<td>${{cell}}</td>`).join('')}}</tr>`
                                ).join('')}}
                            </tbody>
                        </table>
                    </div>
                `;
                container.innerHTML += sectionHtml;
            }});
        }}
        
        function getTables(data) {{
            const step = data.step;
            const tables = [];
            
            if (step === 'index_source' && data.headers) {{
                const headers = ['#', 'Field Name', 'Data Type', 'Nullable', 'Example'];
                const rows = data.headers.slice(0, 500).map(h => [
                    h.index || '',
                    h.field_name || '',
                    h.dtype || '',
                    h.nullable ? 'Yes' : 'No',
                    h.example || ''
                ]);
                tables.push({{id: 'headers-table', title: 'Headers', headers, rows}});
            }}
            
            if (step === 'index_target' && data.sample_fields) {{
                const headers = ['SAP Field', 'SAP Table', 'Mandatory', 'Key', 'Data Type', 'Length', 'Decimal'];
                const rows = data.sample_fields.map(f => [
                    f.sap_field || '',
                    f.sap_table || '',
                    f.mandatory ? 'Yes' : 'No',
                    f.key ? 'Yes' : 'No',
                    f.data_type || '',
                    f.length || '',
                    f.decimal || ''
                ]);
                tables.push({{id: 'fields-table', title: 'Target Fields', headers, rows}});
            }}
            
            if (step === 'map') {{
                if (data.mappings) {{
                    const headers = ['Target Field', 'Source Header', 'Required', 'Confidence', 'Status', 'Rationale'];
                    const rows = data.mappings.map(m => [
                        m.target_field || '',
                        m.source_header || '',
                        m.required ? 'Yes' : 'No',
                        m.confidence ? m.confidence.toFixed(2) : '',
                        m.status || '',
                        m.rationale || ''
                    ]);
                    tables.push({{id: 'mappings-table', title: 'Mappings', headers, rows}});
                }}
                
                if (data.to_audit_rows) {{
                    const headers = ['Target Table', 'Target Field', 'Source Header', 'Confidence', 'Reason'];
                    const rows = data.to_audit_rows.map(r => [
                        r.target_table || '',
                        r.target_field || '',
                        r.source_header || '',
                        r.confidence ? r.confidence.toFixed(2) : '',
                        r.reason || ''
                    ]);
                    tables.push({{id: 'audit-table', title: 'To Audit', headers, rows}});
                }}
            }}
            
            if (step === 'raw_validation' && data.null_rate_by_source) {{
                const headers = ['Column', 'Null Rate %'];
                const rows = Object.entries(data.null_rate_by_source).map(([col, rate]) => [
                    col,
                    ((rate || 0) * 100).toFixed(1) + '%'
                ]);
                tables.push({{id: 'null-rates-table', title: 'Null Rates by Source', headers, rows}});
            }}
            
            if (step === 'post_transform_validation') {{
                if (data.errors_by_rule) {{
                    const headers = ['Rule', 'Error Count'];
                    const rows = Object.entries(data.errors_by_rule).map(([rule, count]) => [rule, count]);
                    tables.push({{id: 'errors-rule-table', title: 'Errors by Rule', headers, rows}});
                }}
                
                if (data.errors_by_field) {{
                    const headers = ['Field', 'Error Count'];
                    const rows = Object.entries(data.errors_by_field).map(([field, count]) => [field, count]);
                    tables.push({{id: 'errors-field-table', title: 'Errors by Field', headers, rows}});
                }}
                
                if (data.sample_rows) {{
                    const sampleRows = data.sample_rows.slice(0, 200);
                    if (sampleRows.length > 0) {{
                        const headers = ['Row #', 'Errors', ...Object.keys(sampleRows[0]).filter(k => !k.startsWith('_') && k !== 'errors').slice(0, 3)];
                        const rows = sampleRows.map(row => [
                            row.__rownum || '',
                            (row.errors || []).join(', '),
                            ...Object.entries(row).filter(([k, v]) => !k.startsWith('_') && k !== 'errors').slice(0, 3).map(([k, v]) => v || '')
                        ]);
                        tables.push({{id: 'sample-rows-table', title: 'Sample Rows', headers, rows}});
                    }}
                }}
            }}
            
            return tables;
        }}
        
        function renderLists(data) {{
            const container = document.getElementById('sections-container');
            const lists = getLists(data);
            
            lists.forEach(list => {{
                const sectionHtml = `
                    <div class="section">
                        <h2>${{list.title}}</h2>
                        <div class="controls">
                            <button class="download-btn" onclick="downloadListCSV('${{list.id}}', '${{list.title}}', ${{JSON.stringify(list.items)}})">
                                Download CSV
                            </button>
                        </div>
                        <div class="list-container" id="${{list.id}}">
                            ${{list.items.map(item => `<div class="list-item">${{item}}</div>`).join('')}}
                        </div>
                    </div>
                `;
                container.innerHTML += sectionHtml;
            }});
        }}
        
        function getLists(data) {{
            const step = data.step;
            const lists = [];
            
            if (step === 'index_target' && data.anomalies) {{
                lists.push({{id: 'anomalies-list', title: 'Anomalies', items: data.anomalies}});
            }}
            
            if (step === 'map') {{
                if (data.unmapped_source_fields) {{
                    lists.push({{id: 'unmapped-source-list', title: 'Unmapped Source Fields', items: data.unmapped_source_fields}});
                }}
                
                if (data.unmapped_target_fields) {{
                    const items = data.unmapped_target_fields.map(f =>
                        typeof f === 'object' ? `${{f.target_table}}.${{f.target_field}}${{f.required ? ' (required)' : ''}}` : f
                    );
                    lists.push({{id: 'unmapped-target-list', title: 'Unmapped Target Fields', items}});
                }}
            }}
            
            if (step === 'raw_validation' && data.missing_sources) {{
                lists.push({{id: 'missing-sources-list', title: 'Missing Sources', items: data.missing_sources}});
            }}
            
            return lists;
        }}
        
        function renderFooter(data) {{
            document.getElementById('timestamp').textContent = new Date().toLocaleString();
        }}
        
        function renderDataProfiling(data) {{
            if (!data.field_profiles || Object.keys(data.field_profiles).length === 0) {{
                return;
            }}
            
            const container = document.getElementById('sections-container');
            const stepTitle = data.step === 'raw_validation' ? 'Data Summary (Raw)' : 'Data Summary (Post-Transform)';
            
            const profilingHtml = `
                <div class="section">
                    <h2>${{stepTitle}}</h2>
                    <div class="controls">
                        <div class="type-filter">
                            <label for="type-filter">Filter by type: </label>
                            <select id="type-filter" onchange="filterProfilingByType()">
                                <option value="">All types</option>
                                <option value="string">String</option>
                                <option value="int">Integer</option>
                                <option value="decimal">Decimal</option>
                                <option value="date">Date</option>
                                <option value="time">Time</option>
                            </select>
                        </div>
                        <div style="margin-top: 10px;">
                            <button class="download-btn" onclick="downloadProfilingCSV()">
                                Download Field Profiles CSV
                            </button>
                        </div>
                    </div>
                    <div class="profiling-table">
                        <table id="profiling-overview-table">
                            <thead>
                                <tr>
                                    <th onclick="sortProfilingTable(0)">Field</th>
                                    <th onclick="sortProfilingTable(1)">Type</th>
                                    <th onclick="sortProfilingTable(2)">Quality Score</th>
                                    <th onclick="sortProfilingTable(3)">Missing %</th>
                                    <th onclick="sortProfilingTable(4)">Invalid %</th>
                                    <th onclick="sortProfilingTable(5)">Unique %</th>
                                    <th onclick="sortProfilingTable(6)">Summary Stats</th>
                                </tr>
                            </thead>
                            <tbody id="profiling-tbody">
                            </tbody>
                        </table>
                    </div>
                    <div id="profiling-detail" class="profiling-detail"></div>
                </div>
            `;
            
            container.innerHTML += profilingHtml;
            
            // Populate the profiling table
            populateProfilingTable(data.field_profiles);
        }}
        
        function populateProfilingTable(fieldProfiles) {{
            const tbody = document.getElementById('profiling-tbody');
            const profiles = Object.values(fieldProfiles).sort((a, b) => a.field.localeCompare(b.field));
            
            tbody.innerHTML = profiles.map((profile, index) => {{
                const summaryStats = getSummaryStats(profile);
                return `<tr class="profiling-row" onclick="showProfilingDetail('${{profile.field}}', ${{index}})">
                    <td>${{profile.field}}</td>
                    <td>${{profile.type}}</td>
                    <td style="color: ${{getQualityColor(profile.quality_score)}}">${{profile.quality_score}}</td>
                    <td>${{profile.missing_pct}}%</td>
                    <td>${{profile.invalid_pct}}%</td>
                    <td>${{profile.unique_pct}}%</td>
                    <td>${{summaryStats}}</td>
                </tr>`;
            }}).join('');
        }}
        
        function getSummaryStats(profile) {{
            if (profile.type === 'string' && profile.length) {{
                return `len: ${{profile.length.min}}-${{profile.length.max}} (avg: ${{profile.length.mean}})`;
            }} else if ((profile.type === 'int' || profile.type === 'decimal') && profile.numeric) {{
                return `range: ${{profile.numeric.min.toFixed(2)}}-${{profile.numeric.max.toFixed(2)}}`;
            }} else if (profile.type === 'date' && profile.date) {{
                return `${{profile.date.min}} to ${{profile.date.max}}`;
            }} else if (profile.type === 'time' && profile.time) {{
                return `${{profile.time.min}} to ${{profile.time.max}}`;
            }}
            return `count: ${{profile.count}}`;
        }}
        
        function getQualityColor(score) {{
            if (score >= 80) return '#28a745';
            if (score >= 60) return '#ffc107';
            return '#dc3545';
        }}
        
        function showProfilingDetail(fieldName, rowIndex) {{
            // Remove previous selection
            document.querySelectorAll('.profiling-row').forEach(row => row.classList.remove('selected'));
            
            // Select current row
            const rows = document.querySelectorAll('.profiling-row');
            if (rows[rowIndex]) {{
                rows[rowIndex].classList.add('selected');
            }}
            
            // Get profile data
            const data = JSON.parse(document.getElementById('data').textContent);
            const profile = data.field_profiles[fieldName];
            
            if (!profile) return;
            
            // Generate detail content
            let detailHtml = `
                <h3>Field Details: ${{profile.field}} (${{profile.type}})</h3>
                <div class="detail-grid">
                    <div class="detail-section">
                        <h4>Statistics</h4>
                        <div class="stats-grid">
                            <div class="stats-item">
                                <div class="stats-value">${{profile.count}}</div>
                                <div class="stats-label">Count</div>
                            </div>
                            <div class="stats-item">
                                <div class="stats-value">${{profile.missing}}</div>
                                <div class="stats-label">Missing</div>
                            </div>
                            <div class="stats-item">
                                <div class="stats-value">${{profile.invalid}}</div>
                                <div class="stats-label">Invalid</div>
                            </div>
                            <div class="stats-item">
                                <div class="stats-value">${{profile.unique}}</div>
                                <div class="stats-label">Unique</div>
                            </div>
                        </div>
            `;
            
            // Add type-specific stats
            if (profile.type === 'string' && profile.length) {{
                detailHtml += `
                    <h4>Length Statistics</h4>
                    <div class="stats-grid">
                        <div class="stats-item">
                            <div class="stats-value">${{profile.length.min}}</div>
                            <div class="stats-label">Min Length</div>
                        </div>
                        <div class="stats-item">
                            <div class="stats-value">${{profile.length.p50}}</div>
                            <div class="stats-label">Median Length</div>
                        </div>
                        <div class="stats-item">
                            <div class="stats-value">${{profile.length.p95}}</div>
                            <div class="stats-label">95th %ile Length</div>
                        </div>
                        <div class="stats-item">
                            <div class="stats-value">${{profile.length.max}}</div>
                            <div class="stats-label">Max Length</div>
                        </div>
                    </div>
                `;
            }}
            
            if ((profile.type === 'int' || profile.type === 'decimal' || profile.type === 'time') && profile.numeric) {{
                detailHtml += `
                    <h4>Numeric Statistics</h4>
                    <div class="stats-grid">
                        <div class="stats-item">
                            <div class="stats-value">${{profile.numeric.min.toFixed(2)}}</div>
                            <div class="stats-label">Min</div>
                        </div>
                        <div class="stats-item">
                            <div class="stats-value">${{profile.numeric.p50.toFixed(2)}}</div>
                            <div class="stats-label">Median</div>
                        </div>
                        <div class="stats-item">
                            <div class="stats-value">${{profile.numeric.p95.toFixed(2)}}</div>
                            <div class="stats-label">95th %ile</div>
                        </div>
                        <div class="stats-item">
                            <div class="stats-value">${{profile.numeric.max.toFixed(2)}}</div>
                            <div class="stats-label">Max</div>
                        </div>
                    </div>
                `;
            }}
            
            detailHtml += `</div><div class="detail-section">`;
            
            // Add histogram
            if (profile.histogram && profile.histogram.bins && profile.histogram.bins.length > 0) {{
                const maxCount = Math.max(...profile.histogram.counts);
                detailHtml += `
                    <h4>Distribution</h4>
                    <div class="histogram-container">
                `;
                
                profile.histogram.bins.forEach((bin, i) => {{
                    const count = profile.histogram.counts[i] || 0;
                    const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
                    detailHtml += `
                        <div class="histogram-bar">
                            <div class="histogram-label">${{bin}}</div>
                            <div class="histogram-visual">
                                <div class="histogram-fill" style="width: ${{percentage}}%"></div>
                            </div>
                            <div class="histogram-value">${{count}}</div>
                        </div>
                    `;
                }});
                
                detailHtml += `</div>`;
            }}
            
            // Add top values
            if (profile.top_values && profile.top_values.length > 0) {{
                detailHtml += `
                    <h4>Top Values</h4>
                    <table class="top-values-table">
                        <thead>
                            <tr><th>Value</th><th>Count</th></tr>
                        </thead>
                        <tbody>
                `;
                
                profile.top_values.forEach(item => {{
                    detailHtml += `<tr><td>${{item.value}}</td><td>${{item.count}}</td></tr>`;
                }});
                
                detailHtml += `
                        </tbody>
                    </table>
                    <button class="download-btn" onclick="downloadTopValuesCSV('${{fieldName}}')">
                        Download Top Values CSV
                    </button>
                `;
            }}
            
            detailHtml += `</div></div>`;
            
            // Show detail panel
            const detailPanel = document.getElementById('profiling-detail');
            detailPanel.innerHTML = detailHtml;
            detailPanel.classList.add('show');
        }}
        
        function filterProfilingByType() {{
            const filter = document.getElementById('type-filter').value.toLowerCase();
            const rows = document.querySelectorAll('.profiling-row');
            
            rows.forEach(row => {{
                const type = row.cells[1].textContent.toLowerCase();
                row.style.display = (!filter || type === filter) ? '' : 'none';
            }});
        }}
        
        function sortProfilingTable(columnIndex) {{
            const table = document.getElementById('profiling-overview-table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            rows.sort((a, b) => {{
                const aVal = a.cells[columnIndex].textContent.trim();
                const bVal = b.cells[columnIndex].textContent.trim();
                
                // Try numeric comparison for numeric columns
                if (columnIndex >= 2 && columnIndex <= 5) {{
                    const aNum = parseFloat(aVal);
                    const bNum = parseFloat(bVal);
                    if (!isNaN(aNum) && !isNaN(bNum)) {{
                        return bNum - aNum; // Descending for numeric
                    }}
                }}
                
                // String comparison
                return aVal.localeCompare(bVal);
            }});
            
            tbody.innerHTML = '';
            rows.forEach(row => tbody.appendChild(row));
        }}
        
        function downloadProfilingCSV() {{
            const data = JSON.parse(document.getElementById('data').textContent);
            if (!data.field_profiles) return;
            
            let csv = 'Field,Type,Quality Score,Missing %,Invalid %,Unique %,Count,Missing,Invalid,Unique\\r\\n';
            
            Object.values(data.field_profiles).forEach(profile => {{
                csv += `"${{profile.field}}","${{profile.type}}",${{profile.quality_score}},${{profile.missing_pct}},${{profile.invalid_pct}},${{profile.unique_pct}},${{profile.count}},${{profile.missing}},${{profile.invalid}},${{profile.unique}}\\r\\n`;
            }});
            
            downloadFile(csv, 'field_profiles.csv', 'text/csv');
        }}
        
        function downloadTopValuesCSV(fieldName) {{
            const data = JSON.parse(document.getElementById('data').textContent);
            const profile = data.field_profiles[fieldName];
            if (!profile || !profile.top_values) return;
            
            let csv = 'Value,Count\\r\\n';
            profile.top_values.forEach(item => {{
                const value = String(item.value).replace(/"/g, '""');
                csv += `"${{value}}",${{item.count}}\\r\\n`;
            }});
            
            downloadFile(csv, `top_values_${{fieldName}}.csv`, 'text/csv');
        }}
        
        function renderCSVRequirements() {{
            const container = document.getElementById('sections-container');
            const csvHtml = `
                <div class="csv-requirements">
                    <h3>CSV Export Requirements</h3>
                    <ul>
                        <li><strong>Encoding:</strong> UTF-8 without BOM</li>
                        <li><strong>Delimiter:</strong> Comma (,)</li>
                        <li><strong>Quote character:</strong> Double quote (")</li>
                        <li><strong>Escape:</strong> Double quotes escaped as ""</li>
                        <li><strong>Line endings:</strong> CRLF (\\r\\n)</li>
                        <li><strong>Date format:</strong> DATS as YYYYMMDD</li>
                        <li><strong>Time format:</strong> TIMS as HHMMSS</li>
                        <li><strong>Decimal separator:</strong> Period (.)</li>
                    </ul>
                </div>
            `;
            container.innerHTML += csvHtml;
        }}
        
        // Table functionality
        function sortTable(tableId, columnIndex) {{
            const table = document.getElementById(tableId);
            const tbody = table.querySelector('tbody');
            const headers = table.querySelectorAll('th');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Clear other headers
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            
            const currentHeader = headers[columnIndex];
            const isAsc = !currentHeader.classList.contains('sort-asc');
            
            rows.sort((a, b) => {{
                const aVal = a.cells[columnIndex].textContent.trim();
                const bVal = b.cells[columnIndex].textContent.trim();
                
                // Try numeric comparison first
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return isAsc ? aNum - bNum : bNum - aNum;
                }}
                
                // String comparison
                return isAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }});
            
            // Clear tbody and re-add sorted rows
            tbody.innerHTML = '';
            rows.forEach(row => tbody.appendChild(row));
            
            // Update header state
            currentHeader.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
        }}
        
        function filterTable(input, tableId) {{
            const filter = input.value.toLowerCase();
            const table = document.getElementById(tableId);
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            }});
        }}
        
        function downloadCSV(tableId, filename) {{
            const table = document.getElementById(tableId);
            const rows = table.querySelectorAll('tr');
            
            let csv = '';
            rows.forEach(row => {{
                const cells = row.querySelectorAll('th, td');
                const rowData = Array.from(cells).map(cell => {{
                    let value = cell.textContent.trim();
                    // Escape quotes and wrap in quotes if contains comma, quote, or newline
                    if (value.includes(',') || value.includes('"') || value.includes('\\n')) {{
                        value = '"' + value.replace(/"/g, '""') + '"';
                    }}
                    return value;
                }});
                csv += rowData.join(',') + '\\r\\n';
            }});
            
            downloadFile(csv, filename + '.csv', 'text/csv');
        }}
        
        function downloadListCSV(listId, filename, items) {{
            let csv = 'Item\\r\\n';
            items.forEach(item => {{
                let value = item.toString().trim();
                if (value.includes(',') || value.includes('"') || value.includes('\\n')) {{
                    value = '"' + value.replace(/"/g, '""') + '"';
                }}
                csv += value + '\\r\\n';
            }});
            
            downloadFile(csv, filename + '.csv', 'text/csv');
        }}
        
        function downloadFile(content, filename, type) {{
            const blob = new Blob([content], {{ type: type + ';charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>"""

    # Ensure output directory exists
    out_html.parent.mkdir(parents=True, exist_ok=True)

    # Write HTML file
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)
