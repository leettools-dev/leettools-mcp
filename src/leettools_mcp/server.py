"""
FastMCP server implementation for LeetTools search functionality.

This module provides a FastMCP-based server that can be used with Claude
and other AI assistants that support the Model Context Protocol.
"""

import os
import sys
import subprocess
import json
import logging
import asyncio

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Configure logging to write to stderr instead of stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("leettools_mcp")

# Initialize FastMCP server with the name "leettools_mcp"
mcp = FastMCP("leettools_mcp")

# Output directory for saving generated content
LEET_HOME = os.getenv("LEET_HOME")
OUTPUT_DIR = Path(os.path.expanduser(f"{LEET_HOME}/mcp_outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Identify the correct leet executable path
def find_leet_executable() -> str:
    """Find the correct leet executable."""
    # First check if there's a specific path set in environment
    if env_path := os.environ.get("LEET_EXECUTABLE"):
        logger.info(f"Using LEET_EXECUTABLE environment variable: {env_path}")
        return env_path
        
    try:
        # Try to find using which command
        result = subprocess.run(
            ["which", "leet"], capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            logger.info(f"Found leet executable at: {result.stdout.strip()}")
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.info("Could not find leet with 'which' command")
    
    # Try to find in the activated virtual environment
    venv_path = os.environ.get("VIRTUAL_ENV")
    if venv_path:
        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        leet_path = os.path.join(venv_path, bin_dir, "leet")
        if os.path.exists(leet_path):
            logger.info(f"Found leet in virtual environment at: {leet_path}")
            return leet_path
    
    # Fall back to using the command name, which works if it's in PATH
    logger.info("Falling back to 'leet' command")
    return "leet"


# Find leet executable at startup
LEET_EXECUTABLE = find_leet_executable()


def get_output_filepath(prefix: str) -> Tuple[str, str]:
    """Generate unique filepaths for saving output and logs."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"{prefix}_{timestamp}.md"
    log_file = OUTPUT_DIR / f"{prefix}_{timestamp}.log"
    return str(output_file), str(log_file)


async def run_leet_command(args: List[str], output_prefix: str) -> Dict[str, Any]:
    """Run a LeetTools command asynchronously."""
    try:
        # Check if leet is available
        if not LEET_EXECUTABLE or (LEET_EXECUTABLE != "leet" and not os.path.exists(LEET_EXECUTABLE)):
            return {
                "success": False,
                "content": json.dumps({
                    "error": True,
                    "message": "LeetTools executable not found",
                    "details": "Please install LeetTools and make sure it's in your PATH.",
                    "code": "EXECUTABLE_NOT_FOUND",
                }, indent=2),
                "stdout": "",
                "stderr": "LeetTools executable not found."
            }

        # Create the output file paths
        output_path, log_path = get_output_filepath(output_prefix)
        logger.info(f"Will save output to: {output_path}")
        logger.info(f"Will save logs to: {log_path}")

        # Add the output path to the arguments
        cmd = [LEET_EXECUTABLE] + args + ["-o", output_path]
        
        # Log the command (with query parameter specially formatted)
        display_cmd = []
        i = 0
        while i < len(cmd):
            if i < len(cmd) - 1 and cmd[i] == "-q":
                display_cmd.extend([cmd[i], f'"{cmd[i+1]}"'])
                i += 2
            else:
                display_cmd.append(cmd[i])
                i += 1
        logger.info(f"Running command: {' '.join(display_cmd)}")

        # Open the log file
        with open(log_path, 'w') as log_file:
            # Write command information to log file
            log_file.write(f"Command: {' '.join(display_cmd)}\n")
            log_file.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            log_file.write("=== STDOUT & STDERR ===\n\n")
            log_file.flush()  # Flush to ensure header is written
            
            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )

            # Process stdout and stderr streams concurrently
            async def read_stream(stream, prefix):
                collected = []
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8')
                    collected.append(line_str)
                    log_file.write(f"{prefix}: {line_str}")
                    log_file.flush()
                return ''.join(collected)

            # Wait for both streams to complete
            stdout_task = asyncio.create_task(read_stream(process.stdout, "STDOUT"))
            stderr_task = asyncio.create_task(read_stream(process.stderr, "STDERR"))
            stdout_str, stderr_str = await asyncio.gather(stdout_task, stderr_task)
            
            # Wait for process to complete
            await process.wait()
            
            # Write exit code to log
            log_file.write(f"\nProcess exited with code: {process.returncode}\n")

        if process.returncode != 0:
            logger.error(f"Command failed with exit code {process.returncode}: {stderr_str}")
            return {
                "success": False,
                "content": "",
                "stdout": stdout_str,
                "stderr": stderr_str,
                "log_path": log_path
            }

        # Read output file directly
        content = ""
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            with open(output_path, "r") as f:
                content = f.read()
            logger.info(f"Read {len(content)} bytes from output file: {output_path}")
        else:
            logger.warning(f"Output file empty or missing: {output_path}")

        return {
            "success": True,
            "content": content,
            "log_path": log_path,
            "instructions": (
                "When present the results, please show the references of the articles with title and full web link. ",
                "For references, only show relevant links for articles. Don't show links for images. ",
                "If the full web link is not available, then don't show that reference.",
            )
        }

    except Exception as e:
        logger.exception(f"Error running LeetTools command: {str(e)}")
        return {
            "success": False,
            "content": json.dumps({
                "error": True,
                "message": "Error running LeetTools command",
                "details": str(e),
                "code": "COMMAND_EXECUTION_ERROR",
            }, indent=2),
            "error": str(e),
        }


async def perform_search(search_type: str, query: str, kb_name: str, args: Optional[List[str]] = None) -> str:
    """Perform a search using specified search type."""
    try:
        logger.info(f"Performing {search_type} search for: {query}")

        # Base command for both search types
        cmd_args = ["flow", "-t", "search", "-k", kb_name, "-q", query, "-l", "INFO"]
        
        # Configure search-specific settings
        if search_type == "web":
            error_code = "WEB_SEARCH_FAILED"
            output_prefix = f"web_search_{kb_name}"
            no_results_message = "No web search results found"
            no_results_code = "NO_WEB_SEARCH_RESULTS"
        elif search_type == "kb":
            error_code = "KB_SEARCH_FAILED"
            output_prefix = f"kb_search_{kb_name}"
            no_results_message = "No knowledge base results found"
            no_results_code = "NO_KB_RESULTS"
        else:
            return json.dumps({
                "error": True,
                "message": f"Unknown search type: {search_type}",
                "details": "Supported types are 'web' and 'kb'",
                "code": "UNKNOWN_SEARCH_TYPE",
            }, indent=2)

        # Add additional arguments if provided
        if args:
            cmd_args.extend(args)

        # Run the search command with the output prefix
        result = await run_leet_command(cmd_args, output_prefix)
        if not result["success"]:
            error_msg = result.get("stderr", "Unknown error")
            logger.error(f"{search_type.capitalize()} search failed: {error_msg}")
            return json.dumps({
                "error": True,
                "message": f"Error running {search_type} search",
                "details": error_msg,
                "code": error_code,
            }, indent=2)
        
        if not result["content"]:
            return json.dumps({
                "error": True,
                "message": no_results_message,
                "details": f"The {search_type} search did not produce any content.",
                "code": no_results_code,
            }, indent=2)

        return result

    except Exception as e:
        logger.exception(f"Exception in {search_type} search: {str(e)}")
        return json.dumps({
            "error": True,
            "message": f"An error occurred performing {search_type} search",
            "details": str(e),
            "code": f"{search_type.upper()}_SEARCH_EXCEPTION",
        }, indent=2)


@mcp.tool()
async def web_search(
    query: str,
    search_max_results: int = 10,
    search_iteration: int = 1,
) -> str:
    """
    Search the web for information on a topic using LeetTools.

    Args:
        query: the search query.
        search_max_results: maximum search results to process (default: 10).
        search_iteration: number of search iterations to perform (default: 1).
    """
    return await perform_search(
        search_type="web",
        query=query,
        kb_name="mcp_search",
        args=[
            "-p", f"search_max_results={search_max_results}",
            "-p", f"search_iteration={search_iteration}",
        ]
    )


@mcp.tool()
async def kb_search(
    query: str,
    knowledge_base_name: str = "mcp_search",
) -> str:
    """
    Search a local knowledge base for information on a topic.

    Args:
        query: the search query.
        kb_name: name of the knowledge base to search (defaults to mcp_search).
    """
    return await perform_search(
        search_type="kb",
        query=query,
        kb_name=knowledge_base_name,
        args=["-p", "retriever_type=local"]
    )

def main():
    """Main entry point for running the LeetTools MCP server."""
    logger.info("Starting LeetTools MCP server...")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()