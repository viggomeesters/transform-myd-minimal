#!/usr/bin/env python3
"""
CSV HTML reporting module for transform-myd-minimal.

Provides interactive HTML report generation for CSV files (rejects) with:
- NaN values displayed as blank
- Sortable table headers
- Per-column filters
- Global search functionality
- Dynamic KPI blocks with Top-5 unique values
- Light/dark theme switcher
- CSV export functionality for filtered data
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import numpy as np


def generate_csv_html_report(csv_file: Path, output_file: Path, title: str) -> None:
    """
    Generate an interactive HTML report from a CSV file.
    
    Args:
        csv_file: Path to the input CSV file
        output_file: Path for the output HTML file
        title: Title for the HTML report
    """
    # Read CSV file
    df = pd.read_csv(csv_file, dtype=str)
    
    # Replace NaN/None values with empty strings for display
    df = df.fillna("")
    
    # Prepare data for JSON embedding
    columns = df.columns.tolist()
    rows = df.values.tolist()
    
    # Calculate basic statistics
    total_rows = len(df)
    total_columns = len(columns)
    
    # Generate column statistics for KPIs
    column_stats = {}
    for col in columns:
        values = df[col].dropna()
        if len(values) > 0:
            value_counts = values.value_counts().head(5)
            column_stats[col] = {
                'total': len(df[col]),
                'non_empty': len(values),
                'top_values': [{'value': str(val), 'count': int(count)} 
                              for val, count in value_counts.items()]
            }
        else:
            column_stats[col] = {
                'total': len(df[col]),
                'non_empty': 0,
                'top_values': []
            }
    
    # Create JSON data object
    data = {
        'title': title,
        'csv_file': str(csv_file.name),
        'total_rows': total_rows,
        'total_columns': total_columns,
        'columns': columns,
        'rows': rows,
        'column_stats': column_stats
    }
    
    # Generate HTML content
    html_content = _generate_html_template(data)
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def _generate_html_template(data: Dict[str, Any]) -> str:
    """Generate the complete HTML template with embedded data and JavaScript."""
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['title']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --bg-color: #f5f5f5;
            --container-bg: white;
            --text-color: #333;
            --header-bg: #f8f9fa;
            --border-color: #e0e0e0;
            --primary-color: #667eea;
            --primary-dark: #764ba2;
            --success-color: #28a745;
            --success-hover: #218838;
            --shadow: rgba(0,0,0,0.1);
        }}
        
        [data-theme="dark"] {{
            --bg-color: #1a1a1a;
            --container-bg: #2d2d2d;
            --text-color: #e0e0e0;
            --header-bg: #3a3a3a;
            --border-color: #555;
            --primary-color: #8b7cf6;
            --primary-dark: #a78bfa;
            --success-color: #10b981;
            --success-hover: #059669;
            --shadow: rgba(0,0,0,0.3);
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            padding: 20px;
            background-color: var(--bg-color);
            color: var(--text-color);
            transition: background-color 0.3s, color 0.3s;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: var(--container-bg);
            border-radius: 8px;
            box-shadow: 0 2px 10px var(--shadow);
            padding: 30px;
        }}
        
        .header {{
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 30px;
            padding-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            color: var(--text-color);
            font-size: 2.2em;
        }}
        
        .header .subtitle {{
            color: var(--text-color);
            opacity: 0.7;
            font-size: 1.1em;
            margin: 5px 0;
        }}
        
        .theme-switcher {{
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s;
        }}
        
        .theme-switcher:hover {{
            background: var(--primary-dark);
        }}
        
        .kpi-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .kpi-card {{
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
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
        
        .controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .search-controls {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .search-box {{
            padding: 10px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            width: 300px;
            font-size: 14px;
            background: var(--container-bg);
            color: var(--text-color);
        }}
        
        .filter-select {{
            padding: 8px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background: var(--container-bg);
            color: var(--text-color);
            min-width: 120px;
        }}
        
        .download-btn {{
            background: var(--success-color);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
            display: inline-block;
            transition: background-color 0.3s;
        }}
        
        .download-btn:hover {{
            background: var(--success-hover);
        }}
        
        .table-container {{
            overflow-x: auto;
            background: var(--container-bg);
            border-radius: 8px;
            box-shadow: 0 1px 3px var(--shadow);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0;
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background: var(--header-bg);
            font-weight: 600;
            color: var(--text-color);
            cursor: pointer;
            user-select: none;
            position: relative;
            white-space: nowrap;
        }}
        
        th:hover {{
            opacity: 0.8;
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
            background: var(--header-bg);
            opacity: 0.8;
        }}
        
        .column-kpis {{
            margin-bottom: 30px;
        }}
        
        .column-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .column-kpi-card {{
            background: var(--container-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px var(--shadow);
        }}
        
        .column-kpi-title {{
            font-weight: bold;
            margin-bottom: 15px;
            color: var(--primary-color);
            font-size: 1.1em;
        }}
        
        .top-values {{
            list-style: none;
        }}
        
        .top-values li {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .top-values li:last-child {{
            border-bottom: none;
        }}
        
        .value-text {{
            flex: 1;
            margin-right: 10px;
            word-break: break-word;
        }}
        
        .value-count {{
            font-weight: bold;
            color: var(--primary-color);
        }}
        
        .empty-value {{
            font-style: italic;
            color: var(--text-color);
            opacity: 0.6;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            color: var(--text-color);
            opacity: 0.7;
            font-size: 0.9em;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>{data['title']}</h1>
                <div class="subtitle">Source: {data['csv_file']}</div>
            </div>
            <button class="theme-switcher" onclick="toggleTheme()">🌙 Dark Mode</button>
        </div>
        
        <div class="kpi-cards">
            <div class="kpi-card">
                <div class="kpi-value">{data['total_rows']}</div>
                <div class="kpi-label">Total Rows</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{data['total_columns']}</div>
                <div class="kpi-label">Total Columns</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" id="visible-rows">{data['total_rows']}</div>
                <div class="kpi-label">Visible Rows</div>
            </div>
        </div>
        
        <div class="column-kpis">
            <h2>Column Statistics (Top 5 Values)</h2>
            <div class="column-kpi-grid" id="column-kpi-grid">
                <!-- Column KPIs will be populated by JavaScript -->
            </div>
        </div>
        
        <div class="controls">
            <div class="search-controls">
                <input type="text" class="search-box" id="global-search" placeholder="Global search...">
                <select class="filter-select" id="column-filter">
                    <option value="">Filter by column...</option>
                </select>
                <input type="text" class="search-box" id="column-search" placeholder="Column value..." style="width: 200px;">
            </div>
            <button class="download-btn" onclick="downloadFilteredCSV()">Download Filtered CSV</button>
        </div>
        
        <div class="table-container">
            <table id="data-table">
                <thead>
                    <tr>
                        <!-- Headers will be populated by JavaScript -->
                    </tr>
                </thead>
                <tbody>
                    <!-- Rows will be populated by JavaScript -->
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            Generated by transform-myd-minimal CSV Report Tool
        </div>
    </div>

    <script id="data" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
    
    <script>
        // Global variables
        let originalData = [];
        let filteredData = [];
        let currentSort = {{ column: -1, direction: 'asc' }};
        
        // Load and initialize
        document.addEventListener('DOMContentLoaded', function() {{
            const data = JSON.parse(document.getElementById('data').textContent);
            originalData = data.rows;
            filteredData = [...originalData];
            
            initializeTable(data);
            initializeFilters(data);
            initializeColumnKPIs(data);
            
            // Add event listeners
            document.getElementById('global-search').addEventListener('input', applyFilters);
            document.getElementById('column-filter').addEventListener('change', function() {{
                document.getElementById('column-search').value = '';
                applyFilters();
            }});
            document.getElementById('column-search').addEventListener('input', applyFilters);
        }});
        
        function initializeTable(data) {{
            const table = document.getElementById('data-table');
            const thead = table.querySelector('thead tr');
            const tbody = table.querySelector('tbody');
            
            // Create headers
            thead.innerHTML = '';
            data.columns.forEach((col, index) => {{
                const th = document.createElement('th');
                th.className = 'sortable';
                th.textContent = col;
                th.onclick = () => sortTable(index);
                thead.appendChild(th);
            }});
            
            // Populate table body
            renderTableRows(data.rows);
        }}
        
        function renderTableRows(rows) {{
            const tbody = document.querySelector('#data-table tbody');
            tbody.innerHTML = '';
            
            rows.forEach(row => {{
                const tr = document.createElement('tr');
                row.forEach(cell => {{
                    const td = document.createElement('td');
                    td.textContent = cell === null || cell === undefined || cell === 'nan' || cell === 'NaN' ? '' : cell;
                    tr.appendChild(td);
                }});
                tbody.appendChild(tr);
            }});
        }}
        
        function initializeFilters(data) {{
            const columnFilter = document.getElementById('column-filter');
            
            data.columns.forEach(col => {{
                const option = document.createElement('option');
                option.value = col;
                option.textContent = col;
                columnFilter.appendChild(option);
            }});
        }}
        
        function initializeColumnKPIs(data) {{
            const grid = document.getElementById('column-kpi-grid');
            grid.innerHTML = '';
            
            data.columns.forEach(col => {{
                const stats = data.column_stats[col];
                const card = document.createElement('div');
                card.className = 'column-kpi-card';
                card.id = `kpi-${{col.replace(/[^a-zA-Z0-9]/g, '_')}}`;
                
                const title = document.createElement('div');
                title.className = 'column-kpi-title';
                title.textContent = col;
                
                const list = document.createElement('ul');
                list.className = 'top-values';
                
                stats.top_values.forEach(item => {{
                    const li = document.createElement('li');
                    
                    const valueSpan = document.createElement('span');
                    valueSpan.className = 'value-text';
                    if (item.value === '' || item.value === null || item.value === undefined) {{
                        valueSpan.textContent = '(empty)';
                        valueSpan.classList.add('empty-value');
                    }} else {{
                        valueSpan.textContent = item.value;
                    }}
                    
                    const countSpan = document.createElement('span');
                    countSpan.className = 'value-count';
                    countSpan.textContent = item.count;
                    
                    li.appendChild(valueSpan);
                    li.appendChild(countSpan);
                    list.appendChild(li);
                }});
                
                if (stats.top_values.length === 0) {{
                    const li = document.createElement('li');
                    li.innerHTML = '<span class="empty-value">No data</span>';
                    list.appendChild(li);
                }}
                
                card.appendChild(title);
                card.appendChild(list);
                grid.appendChild(card);
            }});
        }}
        
        function applyFilters() {{
            const data = JSON.parse(document.getElementById('data').textContent);
            const globalSearch = document.getElementById('global-search').value.toLowerCase();
            const columnFilter = document.getElementById('column-filter').value;
            const columnSearch = document.getElementById('column-search').value.toLowerCase();
            
            let filtered = [...originalData];
            
            // Apply global search
            if (globalSearch) {{
                filtered = filtered.filter(row => 
                    row.some(cell => 
                        String(cell || '').toLowerCase().includes(globalSearch)
                    )
                );
            }}
            
            // Apply column-specific filter
            if (columnFilter && columnSearch) {{
                const columnIndex = data.columns.indexOf(columnFilter);
                if (columnIndex !== -1) {{
                    filtered = filtered.filter(row => 
                        String(row[columnIndex] || '').toLowerCase().includes(columnSearch)
                    );
                }}
            }}
            
            filteredData = filtered;
            renderTableRows(filtered);
            updateVisibleRowsCount(filtered.length);
            updateColumnKPIs(data, filtered);
        }}
        
        function updateVisibleRowsCount(count) {{
            document.getElementById('visible-rows').textContent = count;
        }}
        
        function updateColumnKPIs(data, filtered) {{
            // Recalculate column statistics for filtered data
            data.columns.forEach((col, colIndex) => {{
                const values = filtered.map(row => row[colIndex]).filter(val => val !== '' && val !== null && val !== undefined);
                const valueCounts = {{}};
                
                values.forEach(val => {{
                    valueCounts[val] = (valueCounts[val] || 0) + 1;
                }});
                
                const topValues = Object.entries(valueCounts)
                    .sort(([,a], [,b]) => b - a)
                    .slice(0, 5)
                    .map(([value, count]) => ({{ value, count }}));
                
                // Update KPI card
                const cardId = `kpi-${{col.replace(/[^a-zA-Z0-9]/g, '_')}}`;
                const card = document.getElementById(cardId);
                const list = card.querySelector('.top-values');
                
                list.innerHTML = '';
                topValues.forEach(item => {{
                    const li = document.createElement('li');
                    
                    const valueSpan = document.createElement('span');
                    valueSpan.className = 'value-text';
                    if (item.value === '' || item.value === null || item.value === undefined) {{
                        valueSpan.textContent = '(empty)';
                        valueSpan.classList.add('empty-value');
                    }} else {{
                        valueSpan.textContent = item.value;
                    }}
                    
                    const countSpan = document.createElement('span');
                    countSpan.className = 'value-count';
                    countSpan.textContent = item.count;
                    
                    li.appendChild(valueSpan);
                    li.appendChild(countSpan);
                    list.appendChild(li);
                }});
                
                if (topValues.length === 0) {{
                    const li = document.createElement('li');
                    li.innerHTML = '<span class="empty-value">No data</span>';
                    list.appendChild(li);
                }}
            }});
        }}
        
        function sortTable(columnIndex) {{
            const data = JSON.parse(document.getElementById('data').textContent);
            const headers = document.querySelectorAll('#data-table th');
            
            // Clear previous sort indicators
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            
            // Determine sort direction
            let direction = 'asc';
            if (currentSort.column === columnIndex && currentSort.direction === 'asc') {{
                direction = 'desc';
            }}
            
            // Sort the filtered data
            filteredData.sort((a, b) => {{
                let aVal = String(a[columnIndex] || '');
                let bVal = String(b[columnIndex] || '');
                
                // Try numeric comparison first
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return direction === 'asc' ? aNum - bNum : bNum - aNum;
                }}
                
                // String comparison
                return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }});
            
            // Update sort state and header
            currentSort = {{ column: columnIndex, direction }};
            headers[columnIndex].classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');
            
            // Re-render table
            renderTableRows(filteredData);
        }}
        
        function downloadFilteredCSV() {{
            const data = JSON.parse(document.getElementById('data').textContent);
            
            // Create CSV content
            let csvContent = data.columns.join(',') + '\\n';
            
            filteredData.forEach(row => {{
                const csvRow = row.map(cell => {{
                    let value = String(cell || '');
                    // Escape quotes and wrap in quotes if contains comma, quote, or newline
                    if (value.includes(',') || value.includes('"') || value.includes('\\n')) {{
                        value = '"' + value.replace(/"/g, '""') + '"';
                    }}
                    return value;
                }}).join(',');
                csvContent += csvRow + '\\n';
            }});
            
            // Download file
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', 'filtered_data.csv');
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}
        
        function toggleTheme() {{
            const body = document.body;
            const button = document.querySelector('.theme-switcher');
            
            if (body.getAttribute('data-theme') === 'dark') {{
                body.removeAttribute('data-theme');
                button.textContent = '🌙 Dark Mode';
            }} else {{
                body.setAttribute('data-theme', 'dark');
                button.textContent = '☀️ Light Mode';
            }}
        }}
    </script>
</body>
</html>"""
    
    return html_template