"""
Constants used throughout the LeetTools MCP server.

This module contains constant values categorized by their usage area.
"""

import os
from pathlib import Path
from re import L


class EnvironmentVars:
    """Environment variable names"""
    LEET_HOME = "LEET_HOME"
    LEET_EXECUTABLE = "LEET_EXECUTABLE"
    VIRTUAL_ENV = "VIRTUAL_ENV"
    ENABLE_DEBUG_LOGGING = "ENABLE_DEBUG_LOGGING"
    CONTEXT_LENGTH = "CONTEXT_LENGTH"


class Paths:
    """File and directory paths"""
    LEET_HOME = os.getenv(EnvironmentVars.LEET_HOME)
    OUTPUT_DIR = Path(os.path.expanduser(f"{LEET_HOME}/mcp_outputs"))


class CommandArgs:
    """Command line arguments and defaults"""
    LOG_LEVEL_INFO = "INFO"
    LOG_LEVEL_DEBUG = "DEBUG"
    DEFAULT_KB_NAME = "mcp_search"


class ErrorCodes:
    """Error codes for various failure scenarios"""
    EXECUTABLE_NOT_FOUND = "EXECUTABLE_NOT_FOUND"
    KB_OPERATION_FAILED = "KB_OPERATION_FAILED"
    WEB_SEARCH_FAILED = "WEB_SEARCH_FAILED"
    KB_SEARCH_FAILED = "KB_SEARCH_FAILED"
    UNKNOWN_SEARCH_TYPE = "UNKNOWN_SEARCH_TYPE"
    NO_WEB_SEARCH_RESULTS = "NO_WEB_SEARCH_RESULTS"
    NO_KB_RESULTS = "NO_KB_RESULTS"
    COMMAND_EXECUTION_ERROR = "COMMAND_EXECUTION_ERROR"
    LOCAL_PATH_NOT_FOUND = "LOCAL_PATH_NOT_FOUND"


class SearchTypes:
    """Search type identifiers"""
    WEB = "web"
    KB = "kb"


class FilePrefixes:
    """File name prefixes for outputs"""
    WEB_SEARCH = "web_search"
    KB_SEARCH = "kb_search"
    KB_OPS = "kb_ops"


class FilePatterns:
    """File patterns and extensions"""
    OUTPUT_SUFFIX = ".md"
    LOG_SUFFIX = ".log"


class Instructions:
    """Instructions for AI presentation"""
    SEARCH_CITATIONS = [
        "When present the results, please show the references of the articles with title and full web link. ",
        "For references, only show relevant links for articles. Don't show links for images. ",
        "If the full web link is not available, then don't show that reference.",
    ]
