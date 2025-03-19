#!/usr/bin/env python3
"""
A simple utility script to test individual MCP tool functions directly from the command line.
"""

import asyncio
import argparse
import json
import sys
import os
from typing import Callable, Any, Dict

# Add the parent directory to the Python path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from leettools_mcp.server import (
    list_kb, kb_search, web_search, add_local_to_kb, create_kb
)

# Map of tool names to their functions
TOOL_MAP: Dict[str, Callable] = {
    "list_kb": list_kb,
    "kb_search": kb_search,
    "web_search": web_search,
    "add_local_to_kb": add_local_to_kb,
    "create_kb": create_kb,
}

async def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Test LeetTools MCP tool functions directly")
    parser.add_argument("tool", choices=TOOL_MAP.keys(), help="The MCP tool function to run")
    parser.add_argument("--query", "-q", help="Search query for search tools")
    parser.add_argument("--kb", "-k", help="Knowledge base name")
    parser.add_argument("--local-path", "-p", help="Local path for add_local_to_kb")
    parser.add_argument("--max-results", "-m", type=int, default=10, help="Maximum search results")
    parser.add_argument("--iteration", "-i", type=int, default=1, help="Search iteration")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON output")
    parser.add_argument("--debug", action="store_true", help="Show debug information")
    
    args = parser.parse_args()
    
    # Call the appropriate function based on the tool name
    try:
        print(f"Running {args.tool}...", file=sys.stderr)
        
        if args.tool == "list_kb":
            result = await list_kb()
        elif args.tool == "kb_search":
            if not args.query:
                parser.error("--query is required for kb_search")
            result = await kb_search(args.query, args.kb)
        elif args.tool == "web_search":
            if not args.query:
                parser.error("--query is required for web_search")
            result = await web_search(args.query, args.max_results, args.iteration)
        elif args.tool == "add_local_to_kb":
            if not args.local_path:
                parser.error("--local-path is required for add_local_to_kb")
            result = await add_local_to_kb(args.local_path, args.kb)
        elif args.tool == "create_kb":
            if not args.kb:
                parser.error("--kb is required for create_kb")
            result = await create_kb(args.kb)
        else:
            print(f"Tool {args.tool} not implemented yet", file=sys.stderr)
            return 1
        
        print(f"Got response from {args.tool}", file=sys.stderr)
        
        if args.debug:
            print(f"Raw result: {result}", file=sys.stderr)
        
        # Parse the JSON result and print
        try:
            result_dict = json.loads(result)
            if args.pretty:
                print(json.dumps(result_dict, indent=2))
            else:
                print(result)
            
            # Extract content if available
            if "content" in result_dict and result_dict["content"] and args.pretty:
                print("\n--- Content ---")
                print(result_dict["content"])
                
            return 0
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON result: {e}", file=sys.stderr)
            print("Raw output:", file=sys.stderr)
            print(result)
            return 1
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    # Make sure the LEET_HOME environment variable is set
    if not os.environ.get("LEET_HOME"):
        print("Warning: LEET_HOME environment variable is not set.", file=sys.stderr)
        print("LeetTools might not work correctly.", file=sys.stderr)
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
