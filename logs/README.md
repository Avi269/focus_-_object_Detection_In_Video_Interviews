# Logging System Documentation

## Log Files Overview

### 1. `general.log`
- **Purpose**: General application activity
- **Level**: INFO and above
- **Contains**: User actions, system events, routine operations
- **Max Size**: 10 MB (5 backups)

### 2. `errors.log`
- **Purpose**: Application errors and exceptions
- **Level**: ERROR and above
- **Contains**: Stack traces, error messages, critical failures
- **Max Size**: 10 MB (5 backups)

### 3. `security.log`
- **Purpose**: Security-related events
- **Level**: WARNING and above
- **Contains**: Failed logins, unauthorized access, permission violations
- **Max Size**: 10 MB (10 backups)

### 4. `detection.log`
- **Purpose**: AI detection engine activity
- **Level**: DEBUG and above
- **Contains**: Face detection, anomaly detection, event logging
- **Max Size**: 15 MB (7 backups)

### 5. `interviews.log`
- **Purpose**: Interview lifecycle events
- **Level**: INFO and above
- **Contains**: Interview start/end, status changes, candidate actions
- **Max Size**: 10 MB (5 backups)

### 6. `database.log` (DEBUG only)
- **Purpose**: Database query debugging
- **Level**: DEBUG
- **Contains**: SQL queries, database connections
- **Max Size**: 10 MB (3 backups)

## Log Files Directory

This directory contains application log files.

### Files Generated:
- general.log
- errors.log
- security.log
- detection.log
- interviews.log
- database.log (DEBUG mode only)

All log files are automatically rotated when they reach 10-15 MB.

## Usage Examples

### In Your Views:
```python
import logging

logger = logging.getLogger(__name__)

def my_view(request):
    logger.info(f"User {request.user} accessed the view")
    try:
        # Your code
        logger.debug("Processing data...")
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
```

## Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical messages for very serious errors

## Monitoring
Check logs regularly:
```bash
# View last 50 lines of errors
tail -n 50 logs/errors.log

# Monitor general log in real-time
tail -f logs/general.log

# Search for specific user actions
grep "username" logs/general.log
```