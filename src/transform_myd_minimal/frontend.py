#!/usr/bin/env python3
"""
Web frontend for Transform MYD Minimal - Alteryx-inspired UI

Provides a simple web interface to access all CLI commands:
- input/output (file management)
- index_source
- index_target
- map
- transform
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string, request, send_file

app = Flask(__name__)
app.secret_key = "transform-myd-minimal-dev-key-change-in-production"

# HTML template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transform MYD Minimal - Workflow Designer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .workflow-canvas {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f7fafc;
        }
        
        .workflow-step {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        
        .workflow-step:hover {
            box-shadow: 0 8px 16px rgba(0,0,0,0.15);
            transform: translateY(-2px);
            border-color: #667eea;
        }
        
        .step-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e2e8f0;
        }
        
        .step-icon {
            width: 48px;
            height: 48px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            margin-right: 15px;
        }
        
        .step-icon.input { background: #edf2f7; }
        .step-icon.index { background: #e6fffa; }
        .step-icon.map { background: #fef5e7; }
        .step-icon.transform { background: #fce7f3; }
        .step-icon.output { background: #ebf8ff; }
        
        .step-title {
            flex: 1;
        }
        
        .step-title h3 {
            font-size: 1.3em;
            color: #2d3748;
            margin-bottom: 4px;
        }
        
        .step-title p {
            font-size: 0.9em;
            color: #718096;
        }
        
        .step-form {
            margin-top: 15px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #4a5568;
            font-weight: 500;
            font-size: 0.9em;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 10px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 0.95em;
            transition: border-color 0.2s;
        }
        
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 6px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #e2e8f0;
            color: #4a5568;
        }
        
        .btn-secondary:hover {
            background: #cbd5e0;
        }
        
        .status-area {
            margin-top: 15px;
            padding: 12px;
            border-radius: 6px;
            font-size: 0.9em;
            display: none;
        }
        
        .status-area.success {
            background: #c6f6d5;
            color: #22543d;
            border: 1px solid #9ae6b4;
        }
        
        .status-area.error {
            background: #fed7d7;
            color: #742a2a;
            border: 1px solid #fc8181;
        }
        
        .status-area.info {
            background: #bee3f8;
            color: #2c5282;
            border: 1px solid #90cdf4;
        }
        
        .status-area.loading {
            background: #fefcbf;
            color: #744210;
            border: 1px solid #f6e05e;
        }
        
        .file-list {
            margin-top: 10px;
            max-height: 200px;
            overflow-y: auto;
            background: #f7fafc;
            border-radius: 6px;
            padding: 10px;
        }
        
        .file-item {
            padding: 8px;
            margin-bottom: 5px;
            background: white;
            border-radius: 4px;
            font-size: 0.85em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .file-item:hover {
            background: #edf2f7;
        }
        
        .file-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        
        .file-link:hover {
            text-decoration: underline;
        }
        
        .footer {
            background: #2d3748;
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .footer p {
            margin: 5px 0;
            opacity: 0.8;
        }
        
        pre {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 0.85em;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔄 Transform MYD Minimal</h1>
            <p>Visual Workflow Designer - Inspired by Alteryx</p>
        </div>
        
        <div class="workflow-canvas">
            <!-- Input Step -->
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon input">📁</div>
                    <div class="step-title">
                        <h3>Input</h3>
                        <p>Manage source files</p>
                    </div>
                </div>
                <div class="step-form">
                    <button class="btn btn-secondary" onclick="listFiles('01_source')">📂 View Source Files</button>
                    <button class="btn btn-secondary" onclick="listFiles('02_target')">📂 View Target Files</button>
                    <button class="btn btn-secondary" onclick="listFiles('07_raw')">📂 View Raw Data</button>
                    <div id="input-status" class="status-area"></div>
                    <div id="file-list" class="file-list" style="display:none;"></div>
                </div>
            </div>
            
            <!-- Index Source Step -->
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon index">📋</div>
                    <div class="step-title">
                        <h3>Index Source</h3>
                        <p>Parse source fields</p>
                    </div>
                </div>
                <div class="step-form">
                    <div class="form-group">
                        <label for="is-object">Object Name</label>
                        <input type="text" id="is-object" placeholder="e.g., m140">
                    </div>
                    <div class="form-group">
                        <label for="is-variant">Variant Name</label>
                        <input type="text" id="is-variant" placeholder="e.g., bnka">
                    </div>
                    <button class="btn btn-primary" onclick="runCommand('index_source')">▶️ Run Index Source</button>
                    <div id="index-source-status" class="status-area"></div>
                </div>
            </div>
            
            <!-- Index Target Step -->
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon index">📊</div>
                    <div class="step-title">
                        <h3>Index Target</h3>
                        <p>Parse target fields</p>
                    </div>
                </div>
                <div class="step-form">
                    <div class="form-group">
                        <label for="it-object">Object Name</label>
                        <input type="text" id="it-object" placeholder="e.g., m140">
                    </div>
                    <div class="form-group">
                        <label for="it-variant">Variant Name</label>
                        <input type="text" id="it-variant" placeholder="e.g., bnka">
                    </div>
                    <button class="btn btn-primary" onclick="runCommand('index_target')">▶️ Run Index Target</button>
                    <div id="index-target-status" class="status-area"></div>
                </div>
            </div>
            
            <!-- Map Step -->
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon map">🗺️</div>
                    <div class="step-title">
                        <h3>Map</h3>
                        <p>Generate field mappings</p>
                    </div>
                </div>
                <div class="step-form">
                    <div class="form-group">
                        <label for="map-object">Object Name</label>
                        <input type="text" id="map-object" placeholder="e.g., m140">
                    </div>
                    <div class="form-group">
                        <label for="map-variant">Variant Name</label>
                        <input type="text" id="map-variant" placeholder="e.g., bnka">
                    </div>
                    <button class="btn btn-primary" onclick="runCommand('map')">▶️ Run Mapping</button>
                    <div id="map-status" class="status-area"></div>
                </div>
            </div>
            
            <!-- Transform Step -->
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon transform">⚙️</div>
                    <div class="step-title">
                        <h3>Transform</h3>
                        <p>Execute data transformation</p>
                    </div>
                </div>
                <div class="step-form">
                    <div class="form-group">
                        <label for="tr-object">Object Name</label>
                        <input type="text" id="tr-object" placeholder="e.g., m140">
                    </div>
                    <div class="form-group">
                        <label for="tr-variant">Variant Name</label>
                        <input type="text" id="tr-variant" placeholder="e.g., bnka">
                    </div>
                    <button class="btn btn-primary" onclick="runCommand('transform')">▶️ Run Transform</button>
                    <div id="transform-status" class="status-area"></div>
                </div>
            </div>
            
            <!-- Output Step -->
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon output">📤</div>
                    <div class="step-title">
                        <h3>Output</h3>
                        <p>View results and reports</p>
                    </div>
                </div>
                <div class="step-form">
                    <button class="btn btn-secondary" onclick="listFiles('10_transformed')">📂 View Transformed Data</button>
                    <button class="btn btn-secondary" onclick="listFiles('08_raw_validation')">📊 View Validation Reports</button>
                    <button class="btn btn-secondary" onclick="listFiles('99_logging')">📝 View Logs</button>
                    <div id="output-status" class="status-area"></div>
                    <div id="output-file-list" class="file-list" style="display:none;"></div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Transform MYD Minimal v4.1.0</strong></p>
            <p>Step-by-Step Object+Variant Pipeline with Visual Workflow</p>
        </div>
    </div>
    
    <script>
        function showStatus(stepId, message, type) {
            const statusEl = document.getElementById(stepId + '-status');
            statusEl.className = 'status-area ' + type;
            statusEl.style.display = 'block';
            statusEl.textContent = message;
        }
        
        function appendOutput(stepId, message) {
            const statusEl = document.getElementById(stepId + '-status');
            if (statusEl.style.display === 'none') {
                showStatus(stepId, '', 'info');
            }
            statusEl.innerHTML += '<pre>' + message + '</pre>';
        }
        
        async function runCommand(command) {
            let object, variant;
            
            switch(command) {
                case 'index_source':
                    object = document.getElementById('is-object').value;
                    variant = document.getElementById('is-variant').value;
                    break;
                case 'index_target':
                    object = document.getElementById('it-object').value;
                    variant = document.getElementById('it-variant').value;
                    break;
                case 'map':
                    object = document.getElementById('map-object').value;
                    variant = document.getElementById('map-variant').value;
                    break;
                case 'transform':
                    object = document.getElementById('tr-object').value;
                    variant = document.getElementById('tr-variant').value;
                    break;
            }
            
            if (!object || !variant) {
                showStatus(command, '⚠️ Please provide both object and variant names', 'error');
                return;
            }
            
            showStatus(command, '⏳ Running command...', 'loading');
            
            try {
                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        command: command,
                        object: object,
                        variant: variant
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showStatus(command, '✅ Success!', 'success');
                    appendOutput(command, result.output);
                } else {
                    showStatus(command, '❌ Error occurred', 'error');
                    appendOutput(command, result.error || result.output);
                }
            } catch (error) {
                showStatus(command, '❌ Request failed: ' + error.message, 'error');
            }
        }
        
        async function listFiles(directory) {
            const targetId = directory.startsWith('0') || directory === '99_logging' ? 'input' : 'output';
            const listId = targetId === 'input' ? 'file-list' : 'output-file-list';
            
            showStatus(targetId, '⏳ Loading files...', 'loading');
            
            try {
                const response = await fetch('/list-files?directory=' + directory);
                const result = await response.json();
                
                if (result.success) {
                    const listEl = document.getElementById(listId);
                    listEl.style.display = 'block';
                    listEl.innerHTML = '';
                    
                    if (result.files.length === 0) {
                        listEl.innerHTML = '<div class="file-item">No files found</div>';
                    } else {
                        result.files.forEach(file => {
                            const fileEl = document.createElement('div');
                            fileEl.className = 'file-item';
                            fileEl.innerHTML = `
                                <a href="/download?path=${encodeURIComponent(file.path)}" class="file-link" target="_blank">
                                    ${file.name}
                                </a>
                                <span>${file.size}</span>
                            `;
                            listEl.appendChild(fileEl);
                        });
                    }
                    
                    showStatus(targetId, `📁 Found ${result.files.length} files in ${directory}`, 'success');
                } else {
                    showStatus(targetId, '❌ Error loading files: ' + result.error, 'error');
                }
            } catch (error) {
                showStatus(targetId, '❌ Request failed: ' + error.message, 'error');
            }
        }
    </script>
</body>
</html>
"""


def run_cli_command(
    command: str, object_name: str, variant_name: str
) -> dict[str, Any]:
    """
    Run a transform-myd-minimal CLI command.

    Args:
        command: Command to run (index_source, index_target, map, transform)
        object_name: Object name (e.g., m140)
        variant_name: Variant name (e.g., bnka)

    Returns:
        Dictionary with success status and output/error message
    """
    try:
        # Build command using sys.executable to ensure same Python interpreter
        cmd = [
            sys.executable,
            "-m",
            "transform_myd_minimal",
            command,
            "--object",
            object_name,
            "--variant",
            variant_name,
            "--force",  # Allow overwriting
        ]

        # Run command
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
        )

        output = result.stdout + result.stderr

        return {
            "success": result.returncode == 0,
            "output": output,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out after 5 minutes"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_directory_files(directory: str, root: Path = Path(".")) -> list:
    """
    List files in a specific data directory.

    Args:
        directory: Directory name (e.g., '01_source', '10_transformed')
        root: Root path of the project

    Returns:
        List of file information dictionaries
    """
    dir_path = root / "data" / directory

    if not dir_path.exists():
        return []

    files = []
    for file_path in dir_path.iterdir():
        if file_path.is_file():
            size = file_path.stat().st_size
            # Format size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            files.append(
                {
                    "name": file_path.name,
                    "path": str(file_path.relative_to(root)),
                    "size": size_str,
                }
            )

    return sorted(files, key=lambda x: x["name"], reverse=True)


@app.route("/")
def index():
    """Render the main frontend page."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/run", methods=["POST"])
def run():
    """Execute a CLI command."""
    data = request.json
    command = data.get("command")
    object_name = data.get("object")
    variant_name = data.get("variant")

    if not command or not object_name or not variant_name:
        return jsonify({"success": False, "error": "Missing required parameters"}), 400

    result = run_cli_command(command, object_name, variant_name)
    return jsonify(result)


@app.route("/list-files")
def list_files():
    """List files in a directory."""
    directory = request.args.get("directory")

    if not directory:
        return jsonify({"success": False, "error": "Missing directory parameter"}), 400

    try:
        files = list_directory_files(directory)
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/download")
def download():
    """Download a file."""
    file_path = request.args.get("path")

    if not file_path:
        return jsonify({"success": False, "error": "Missing path parameter"}), 400

    try:
        # Security: Validate path to prevent directory traversal attacks
        requested_path = Path(file_path).resolve()
        base_path = Path(".").resolve()

        # Ensure the requested file is within the project directory
        if not str(requested_path).startswith(str(base_path)):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Access denied: Path outside project directory",
                    }
                ),
                403,
            )

        # Ensure file exists and is a file (not a directory)
        if not requested_path.is_file():
            return jsonify({"success": False, "error": "File not found"}), 404

        return send_file(requested_path, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def start_frontend(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    """
    Start the web frontend server.

    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    print("\n🔄 Transform MYD Minimal - Web Frontend")
    print("=" * 50)
    print(f"Starting server on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    start_frontend(debug=True)
