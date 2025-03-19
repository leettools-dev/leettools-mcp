"""
Enum definitions for tools and operations supported by the LeetTools MCP server.
"""

from enum import Enum

class Tools(str, Enum):
    """Enum of tool names used in the MCP server"""
    WEB_SEARCH = "web_search"
    KB_SEARCH = "kb_search"
    LIST_KB = "list_kb"
    CREATE_KB = "create_kb"
    ADD_LOCAL_TO_KB = "add_local_to_kb"
    DIGEST = "digest"
