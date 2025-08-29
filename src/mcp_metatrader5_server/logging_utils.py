#!/usr/bin/env python3
"""
Shared logging utility for MCP MetaTrader 5 Server
Provides structured JSON logging with rotation to logs/command_name directories
Following user preference: logs saved in /logs/command_name format
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def __init__(self, command_name: str, transport: str = "unknown", session_id: Optional[str] = None):
        super().__init__()
        self.command_name = command_name
        self.transport = transport
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.pid = os.getpid()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_obj = {
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "name": record.name,
            "pid": self.pid,
            "transport": self.transport,
            "session_id": self.session_id,
            "event": getattr(record, 'event', 'log'),
            "message": record.getMessage(),
            "context": {}
        }
        
        # Add extra context if available
        if hasattr(record, 'context') and record.context:
            log_obj["context"] = record.context
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info', 'event', 'context']:
                log_obj["context"][key] = value
        
        return json.dumps(log_obj, ensure_ascii=False)

class PlainFormatter(logging.Formatter):
    """Plain text formatter for stderr output (no emojis for Windows compatibility)"""
    
    def __init__(self, command_name: str, session_id: Optional[str] = None):
        super().__init__()
        self.command_name = command_name
        self.session_id = session_id or str(uuid.uuid4())[:8]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as plain text"""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        event = getattr(record, 'event', 'log')
        
        # Clean message (no emojis)
        message = record.getMessage().replace('🚀', '').replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARN]').replace('📊', '[INFO]').replace('🔧', '[CONFIG]').replace('👋', '[BYE]').strip()
        
        base = f"[{timestamp}] {self.session_id[:4]} {record.levelname:5} {record.name}: {message}"
        
        if event != 'log':
            base = f"{base} (event={event})"
        
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"
        
        return base

def setup_logging(
    command_name: str,
    session_id: Optional[str] = None,
    log_level: str = None,
    transport: str = "unknown"
) -> logging.Logger:
    """
    Setup structured logging for MCP components
    
    Args:
        command_name: Name of the command (e.g., "run_fork_mcp", "mcp_client_simple")
        session_id: Optional session identifier
        log_level: Log level (DEBUG, INFO, WARN, ERROR)
        transport: Transport type (stdio, http, unknown)
    
    Returns:
        Configured logger instance
    """
    # Determine log level
    if log_level is None:
        log_level = os.environ.get("MCP_LOG_LEVEL", "INFO")
    
    # Create logs directory following user's rule: /logs/command_name
    root_dir = Path(__file__).parent.parent.parent  # Go to fork_mcp root
    logs_dir = root_dir / "logs" / command_name
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate session ID if not provided
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]
    
    # Create log filename
    timestamp = datetime.now().strftime("%Y%m%d")
    if command_name == "mcp_client_simple":
        # Include time for client sessions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"client_{timestamp}.log"
    else:
        log_file = logs_dir / f"server_{timestamp}.log"
    
    # Clear any existing handlers for this logger
    logger_name = f"mcp-{command_name}"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # File handler with JSON formatting and rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter(command_name, transport, session_id))
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    logger.addHandler(file_handler)
    
    # Stderr handler with plain formatting (no emojis for Windows)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(PlainFormatter(command_name, session_id))
    stderr_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.addHandler(stderr_handler)
    
    # Set propagate to False to avoid duplicate logs
    logger.propagate = False
    
    # Log initial setup
    logger.info(f"Logging initialized for {command_name}", extra={
        "event": "logging_initialized",
        "context": {
            "command_name": command_name,
            "session_id": session_id,
            "transport": transport,
            "log_level": log_level,
            "log_file": str(log_file),
            "pid": os.getpid()
        }
    })
    
    return logger

def reconfigure_stdio_for_windows():
    """
    Reconfigure stdout/stderr for Windows STDIO stability
    Must be called before any logging setup
    """
    try:
        # Ensure UTF-8 encoding and unbuffered I/O for Windows
        if sys.stdout:
            sys.stdout.reconfigure(encoding="utf-8", write_through=True)
        if sys.stderr:
            sys.stderr.reconfigure(encoding="utf-8", write_through=True)
    except (AttributeError, OSError):
        # Fallback for older Python versions or unsupported platforms
        pass

def create_structured_log_entry(
    event: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    level: str = "INFO"
) -> Dict[str, Any]:
    """
    Create a structured log entry dict
    
    Args:
        event: Event type (e.g., "mt5_connected", "stdio_frame_received_first")
        message: Human-readable message
        context: Additional context data
        level: Log level
    
    Returns:
        Structured log entry
    """
    return {
        "event": event,
        "message": message,
        "context": context or {},
        "level": level
    }

# Context managers for logging scopes
class LoggingScope:
    """Context manager for scoped logging with timing"""
    
    def __init__(self, logger: logging.Logger, scope_name: str, context: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.scope_name = scope_name
        self.context = context or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.debug(f"Starting {self.scope_name}", extra={
            "event": f"{self.scope_name}_start",
            "context": self.context
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(f"Failed {self.scope_name} after {duration:.2f}s", extra={
                "event": f"{self.scope_name}_failed",
                "context": {**self.context, "duration": duration, "error": str(exc_val)}
            })
        else:
            self.logger.info(f"Completed {self.scope_name} in {duration:.2f}s", extra={
                "event": f"{self.scope_name}_completed",
                "context": {**self.context, "duration": duration}
            })
