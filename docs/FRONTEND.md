# Web Frontend - Visual Workflow Designer

Transform MYD Minimal now includes a web-based visual workflow designer inspired by Alteryx Designer. This provides an easy-to-use graphical interface for executing all CLI commands without requiring command-line knowledge.

## Overview

The web frontend provides a clean, modern interface with six workflow steps:
1. **Input** - Manage and view source files
2. **Index Source** - Parse source fields from Excel files
3. **Index Target** - Parse target fields from XML files
4. **Map** - Generate field mappings
5. **Transform** - Execute data transformation
6. **Output** - View results, reports, and logs

## Starting the Frontend

### Basic Usage

```bash
# Start the frontend server (default: http://127.0.0.1:5000)
python -m transform_myd_minimal frontend

# Custom host and port
python -m transform_myd_minimal frontend --host 0.0.0.0 --port 8080

# With debug mode
python -m transform_myd_minimal frontend --debug
```

### Windows PowerShell

```powershell
# Using Python module
py -3.12 -m transform_myd_minimal frontend

# With custom port
py -3.12 -m transform_myd_minimal frontend --port 8080
```

### Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Host address to bind to |
| `--port` | `5000` | Port number to listen on |
| `--debug` | `False` | Enable Flask debug mode |

## Using the Interface

### 1. Input Step

**Purpose:** View and manage input files

**Features:**
- View Source Files (`data/01_source/`)
- View Target Files (`data/02_target/`)
- View Raw Data (`data/07_raw/`)

**Usage:**
1. Click one of the "View" buttons
2. A file list appears showing all files in that directory
3. Click on any file to download it

### 2. Index Source Step

**Purpose:** Parse and index source fields from Excel files

**Inputs:**
- Object Name (e.g., `m140`)
- Variant Name (e.g., `bnka`)

**Requirements:**
- Input file must exist: `data/01_source/{object}_{variant}.xlsx`

**Process:**
1. Enter object and variant names
2. Click "Run Index Source"
3. View results in the status area
4. Output saved to: `migrations/{object}/{variant}/index_source.yaml`

### 3. Index Target Step

**Purpose:** Parse and index target fields from XML files

**Inputs:**
- Object Name (e.g., `m140`)
- Variant Name (e.g., `bnka`)

**Requirements:**
- Input file must exist: `data/02_target/{object}_{variant}.xml`

**Process:**
1. Enter object and variant names
2. Click "Run Index Target"
3. View results in the status area
4. Output saved to: `migrations/{object}/{variant}/index_target.yaml`

### 4. Map Step

**Purpose:** Generate field mappings between source and target

**Inputs:**
- Object Name (e.g., `m140`)
- Variant Name (e.g., `bnka`)

**Requirements:**
- `migrations/{object}/{variant}/index_source.yaml` (from step 2)
- `migrations/{object}/{variant}/index_target.yaml` (from step 3)

**Process:**
1. Enter object and variant names
2. Click "Run Mapping"
3. View mapping results in the status area
4. Output saved to: `migrations/{object}/{variant}/mapping.yaml`

### 5. Transform Step

**Purpose:** Execute data transformation pipeline

**Inputs:**
- Object Name (e.g., `m140`)
- Variant Name (e.g., `bnka`)

**Requirements:**
- Raw data file: `data/07_raw/{object}_{variant}.xlsx`
- Mapping file: `migrations/{object}/{variant}/mapping.yaml`
- Template files: `data/06_template/S_{VARIANT}#*.csv`

**Process:**
1. Enter object and variant names
2. Click "Run Transform"
3. View transformation results in the status area
4. Output saved to: `data/10_transformed/`

### 6. Output Step

**Purpose:** View results, validation reports, and logs

**Features:**
- View Transformed Data (`data/10_transformed/`)
- View Validation Reports (`data/08_raw_validation/`)
- View Logs (`data/99_logging/`)

**Usage:**
1. Click one of the "View" buttons
2. Browse generated files
3. Click on any file to download and view it

## Features

### Visual Design
- **Modern UI**: Clean, professional interface with gradient styling
- **Card-based Layout**: Each workflow step is a separate card
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Icon-based Navigation**: Clear visual indicators for each step

### Status Feedback
- **Real-time Updates**: See command output as it happens
- **Color-coded Status**: 
  - 🟡 Yellow: Loading/In Progress
  - 🟢 Green: Success
  - 🔴 Red: Error
  - 🔵 Blue: Information
- **Detailed Output**: View complete command output in the interface

### File Management
- **Directory Browsing**: Easy navigation through data directories
- **File Previews**: See file names and sizes
- **Download Support**: Click to download any file
- **Automatic Refresh**: File lists update after each command

## Architecture

### Backend
- **Flask** web framework
- **Subprocess** for CLI command execution
- **RESTful API** for command execution and file management

### Frontend
- **Pure HTML/CSS/JS**: No external dependencies
- **Embedded Design**: All styles and scripts inline
- **Async Communication**: AJAX requests for smooth UX

### API Endpoints

#### GET /
Returns the main frontend HTML page

#### POST /run
Execute a CLI command

**Request:**
```json
{
  "command": "index_source",
  "object": "m140",
  "variant": "bnka"
}
```

**Response:**
```json
{
  "success": true,
  "output": "Command output...",
  "returncode": 0
}
```

#### GET /list-files?directory={dir}
List files in a data directory

**Response:**
```json
{
  "success": true,
  "files": [
    {
      "name": "m140_bnka.xlsx",
      "path": "data/01_source/m140_bnka.xlsx",
      "size": "1.2 MB"
    }
  ]
}
```

#### GET /download?path={path}
Download a file

## Security Considerations

⚠️ **Important:** This is a development server intended for local use only.

### Default Configuration
- Binds to `127.0.0.1` (localhost only)
- No authentication required
- Direct filesystem access

### Production Use
If you need to deploy this in a production environment:

1. **Use a Production WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8080 transform_myd_minimal.frontend:app
   ```

2. **Add Authentication**
   - Implement user authentication
   - Use environment variables for credentials
   - Add HTTPS/SSL support

3. **Restrict File Access**
   - Validate all file paths
   - Implement access controls
   - Sanitize user inputs

4. **Network Security**
   - Use reverse proxy (nginx, Apache)
   - Configure firewall rules
   - Implement rate limiting

## Troubleshooting

### Server Won't Start

**Problem:** Port already in use
```
Error: Address already in use
```

**Solution:** Use a different port
```bash
python -m transform_myd_minimal frontend --port 8080
```

### Commands Fail

**Problem:** Missing input files
```
Error: Input file not found: data/01_source/m140_bnka.xlsx
```

**Solution:** Ensure required files exist in the correct directories

### Browser Can't Connect

**Problem:** Firewall blocking connection

**Solution:** 
1. Check firewall settings
2. Verify server is running
3. Try accessing from `http://localhost:5000` instead of IP address

## Example Workflow

Complete workflow example using the frontend:

1. **Start the Server**
   ```bash
   python -m transform_myd_minimal frontend
   ```

2. **Open Browser**
   Navigate to: http://127.0.0.1:5000

3. **Verify Input Files**
   - Click "View Source Files" in Input step
   - Confirm `m140_bnka.xlsx` exists
   - Click "View Target Files"
   - Confirm `m140_bnka.xml` exists

4. **Index Source**
   - Enter "m140" for Object Name
   - Enter "bnka" for Variant Name
   - Click "Run Index Source"
   - Wait for success message

5. **Index Target**
   - Enter "m140" for Object Name
   - Enter "bnka" for Variant Name
   - Click "Run Index Target"
   - Wait for success message

6. **Generate Mapping**
   - Enter "m140" for Object Name
   - Enter "bnka" for Variant Name
   - Click "Run Mapping"
   - Review mapping results

7. **Transform Data**
   - Verify raw data file exists in `data/07_raw/`
   - Enter "m140" for Object Name
   - Enter "bnka" for Variant Name
   - Click "Run Transform"
   - Wait for completion

8. **View Results**
   - Click "View Transformed Data" in Output step
   - Download and review transformed CSV files
   - Click "View Validation Reports" for quality checks
   - Click "View Logs" for detailed execution logs

## Integration with CLI

The frontend seamlessly integrates with the existing CLI:
- All commands use the same backend code
- Results are identical to CLI execution
- File paths and structures remain consistent
- Can switch between frontend and CLI at any time

## Benefits Over CLI

- **Visual Progress**: See what's happening in real-time
- **No Command Memorization**: All commands accessible via buttons
- **File Browser**: Easy navigation through output directories
- **Error Handling**: Clear error messages with context
- **Beginner Friendly**: No command-line knowledge required
- **Multi-user**: Multiple users can access via network (with proper security)

## Future Enhancements

Potential improvements for future versions:
- Drag-and-drop file upload
- Visual workflow builder with connections between steps
- Real-time log streaming
- Batch processing for multiple objects/variants
- Configuration editor
- Result visualization and charts
- Export workflow as CLI script
- Workflow templates and presets

## Support

For issues or questions:
1. Check the main [README.md](../README.md)
2. Review [USAGE.md](USAGE.md) for CLI documentation
3. Check logs in `data/99_logging/`
4. Open an issue on GitHub
