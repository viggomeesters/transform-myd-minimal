# Logging Configuration

Transform MYD Minimal now uses Python's standard `logging` module instead of print statements for better control over output and debugging.

## Log Levels

The following log levels are available:
- **DEBUG**: Detailed information for debugging
- **INFO**: General information messages (default)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical error messages

## Configuration

### Environment Variables

You can control logging behavior using environment variables:

- `LOG_LEVEL`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  ```bash
  LOG_LEVEL=WARNING python -m transform_myd_minimal map -object m140 -variant bnka
  ```

- `LOG_FORMAT`: Set the output format
  - `simple` (default): `LEVEL: message`
  - `detailed`: `timestamp - module - LEVEL - message`
  
  ```bash
  LOG_FORMAT=detailed python -m transform_myd_minimal map -object m140 -variant bnka
  ```

### Examples

1. **Normal operation** (INFO level messages):
   ```bash
   python -m transform_myd_minimal map -object m140 -variant bnka
   ```

2. **Quiet operation** (only warnings and errors):
   ```bash
   LOG_LEVEL=WARNING python -m transform_myd_minimal map -object m140 -variant bnka
   ```

3. **Debug mode** (all messages including debug info):
   ```bash
   LOG_LEVEL=DEBUG python -m transform_myd_minimal map -object m140 -variant bnka
   ```

4. **Detailed timestamps** (for troubleshooting):
   ```bash
   LOG_FORMAT=detailed python -m transform_myd_minimal map -object m140 -variant bnka
   ```

## Message Types

The application now uses appropriate log levels for different types of messages:

- **INFO**: Progress updates, statistics, successful operations
- **WARNING**: Non-fatal issues (e.g., missing config files, failed optional operations)
- **ERROR**: Fatal errors that prevent operation completion

This provides better control over what information is displayed and makes it easier to filter output based on importance.