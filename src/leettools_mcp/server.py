"""
FastMCP server implementation for LeetTools search functionality.

This module provides a FastMCP-based server that can be used with Claude
and other AI assistants that support the Model Context Protocol.
"""

import os
import sys
import logging
from typing import List

from mcp.server.fastmcp import FastMCP

from leettools_mcp.command_options import CommandOptions
from leettools_mcp.utils import (
    get_output_filepath,
    run_leet_command,
    CommandError,
)

from leettools_mcp.constants import CommandArgs, EnvironmentVars, ErrorCodes

from leettools_mcp.tools import Tools

MCP_SERVER_NAME = "leettools_mcp"
# Configure logging to write to stderr instead of stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(MCP_SERVER_NAME)

# Initialize FastMCP server with the name
mcp = FastMCP(MCP_SERVER_NAME)


async def _handle_command_failure(operation_type: str, result, options: CommandOptions) -> str:
    """Handle command execution failure."""
    error_msg = result.stderr or "Unknown error"
    logger.error(f"{operation_type} operation failed: {error_msg}")
    error = CommandError(
        message=f"Error running {operation_type}",
        details=error_msg,
        code=options.error_code or f"{operation_type.upper()}_FAILED",
    )
    return error.model_dump_json(indent=2)

async def _process_output_file(operation_type: str, output_path: str, options: CommandOptions) -> str:
    """Process the output file and handle content."""
    content = ""
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        with open(output_path, "r") as f:
            content = f.read()
        logger.info(f"Read {len(content)} bytes from output file: {output_path}")
    else:
        logger.warning(f"Output file empty or missing: {output_path}")

    if not content and options.no_results_message:
        error = CommandError(
            message=options.no_results_message,
            details=f"The {operation_type} operation did not produce any content.",
            code=options.no_results_code or f"NO_{operation_type.upper()}_RESULTS",
        )
        return error.model_dump_json(indent=2)

    # Check if debug logging is enabled
    context_length = os.environ.get(EnvironmentVars.CONTEXT_LENGTH)
    if context_length is not None:
        logger.info(f"Context length is defined: {context_length}, truncating content")
        content = content[:int(context_length)]

    return content

async def _process_stdout(operation_type: str, result, options: CommandOptions) -> None:
    """Process stdout using the tool-specific processor if available."""
    if options.stdout_processor and result.stdout:
        try:
            processed_result = options.stdout_processor(result.stdout)
            for key, value in processed_result.items():
                setattr(result, key, value)
            logger.info(f"Processed stdout for {operation_type}")
        except Exception as e:
            logger.error(f"Error processing stdout: {str(e)}")

async def perform_operation(
    operation_type: str,
    args: List[str],
    knowledge_base_name: str = None,
) -> str:
    """
    Common operation handler for all LeetTools operations.

    Args:
        operation_type: Type of operation (from Tools enum)
        args: Command line arguments to pass to leet
        knowledge_base_name: Optional knowledge base name for relevant operations

    Returns:
        JSON string with the operation results
    """
    try:
        logger.info(f"Performing {operation_type} operation")
        options = CommandOptions.get_command_options(operation_type, knowledge_base_name)

        # Setup output paths and command arguments
        output_path, log_path = get_output_filepath(options.output_prefix)
        logger.info(f"Will save output to: {output_path}")
        logger.info(f"Will save logs to: {log_path}")

        cmd_args = args.copy()
        if options.read_output_file:
            cmd_args.extend(["-o", output_path])

        # Execute command
        result = await run_leet_command(cmd_args, log_path)
        if not result.success:
            return await _handle_command_failure(operation_type, result, options)

        # Process output file if needed
        if options.read_output_file:
            content = await _process_output_file(operation_type, output_path, options)
            if isinstance(content, str) and content.startswith('{'): # Check if it's an error JSON
                return content
            result.content = content
            if options.instructins:
                result.instructions = options.instructins

        # Process stdout if needed
        await _process_stdout(operation_type, result, options)

        # Clean up result
        if options.no_stdout_return:
            result.stdout = None
        if options.no_stderr_return:
            result.stderr = None

        return result.model_dump_json()

    except Exception as e:
        logger.exception(f"Exception in {operation_type} operation: {str(e)}")
        error = CommandError(
            message=f"An error occurred performing {operation_type}",
            details=str(e),
            code=f"{operation_type.upper()}_EXCEPTION",
        )
        return error.model_dump_json(indent=2)


@mcp.tool()
async def add_local_to_kb(
    local_path: str,
    knowledge_base_name: str = None,
) -> str:
    """
    Add files in a local folder to a knowledge base using LeetTools.

    Args:
        local_path: path to the local folder to add.
        knowledge_base_name: name of the knowledge base to add to.
    """
    # Check if local path exists before proceeding
    if not os.path.exists(local_path):
        error = CommandError(
            message="Local path does not exist",
            details=f"The specified path '{local_path}' does not exist.",
            code=ErrorCodes.LOCAL_PATH_NOT_FOUND,
        )
        return error.model_dump_json(indent=2)

    # If knowledge base name is not provided, use the local_path to form the name
    if not knowledge_base_name:
        knowledge_base_name = (
            os.path.basename(local_path)
            .replace(" ", "_")
            .replace("-", "_")
            .replace(".", "_")
            .lower()
        )

    return await perform_operation(
        operation_type=Tools.ADD_LOCAL_TO_KB,
        args=[
            "kb",
            "add-local",
            "-p",
            local_path,
            "-k",
            knowledge_base_name,
            "-l",
            CommandArgs.LOG_LEVEL_DEBUG
        ],
        knowledge_base_name=knowledge_base_name,
    )


@mcp.tool()
async def create_kb(
    knowledge_base_name: str,
) -> str:
    """
    Create a local knowledge base using LeetTools.

    Args:
        knowledge_base_name: name of the knowledge base to create.
    """
    return await perform_operation(
        operation_type=Tools.CREATE_KB,
        args=["kb", "create", "-k", knowledge_base_name],
        knowledge_base_name=knowledge_base_name,
    )


@mcp.tool()
async def list_kb() -> str:
    """
    List all local knowledge bases using LeetTools.

    Returns information about available knowledge bases in the format:
    Org: <org-name>    KB: <kb-name>    ID: <kb-id>
    """
    return await perform_operation(
        operation_type=Tools.LIST_KB,
        args=["kb", "list"],
        knowledge_base_name=None,
    )


@mcp.tool()
async def web_search(
    query: str,
    search_max_results: int = 10,
    search_iteration: int = 1,
    knowledge_base_name: str = CommandArgs.DEFAULT_KB_NAME,
) -> str:
    """
    Search the web for information on a topic using LeetTools.

    Args:
        query: the search query.
        search_max_results: maximum search results to process (default: 10).
        search_iteration: number of search iterations to perform (default: 1).
        knowledge_base_name: name of the knowledge base to search (defaults to mcp_search).
    """
    return await perform_operation(
        operation_type=Tools.WEB_SEARCH,
        args=[
            "flow",
            "-t",
            "search",
            "-k",
            CommandArgs.DEFAULT_KB_NAME,
            "-q",
            query,
            "-p",
            f"search_max_results={search_max_results}",
            "-p",
            f"search_iteration={search_iteration}",
        ],
        knowledge_base_name=knowledge_base_name,
    )


@mcp.tool()
async def kb_search(
    query: str,
    knowledge_base_name: str = CommandArgs.DEFAULT_KB_NAME,
) -> str:
    """
    Search a local knowledge base for information on a topic.

    Args:
        query: the search query.
        knowledge_base_name: name of the knowledge base to search (defaults to mcp_search).
    """
    return await perform_operation(
        operation_type=Tools.KB_SEARCH,
        args=[
            "flow",
            "-t",
            "search",
            "-k",
            knowledge_base_name,
            "-q",
            query,
            "-p",
            "retriever_type=local",
        ],
        knowledge_base_name=knowledge_base_name,
    )


@mcp.tool()
async def extract(
    query: str,
    extract_pydantic: str,
    knowledge_base_name: str = CommandArgs.DEFAULT_KB_NAME,
    days_limit: int = 30,
) -> str:
    """
    Extract information from a knowledge base based on a query and a time limit.

    Args:
        query: the search query to extract relevant data.
        extract_pydantic: the Pydantic model python file full path to use for extracting the data.
        knowledge_base_name: name of the knowledge base to search (defaults to mcp_search).
        days_limit: the number of days to search for (defaults to 30).
    """
    return await perform_operation(
        operation_type=Tools.EXTRACT,
        args=[
            "flow",
            "-t",
            "extract",
            "-k",   
            knowledge_base_name,
            "-q",
            query,
            "-p",
            f"extract_pydantic={extract_pydantic}",
            "-p",
            f"days_limit={days_limit}",
            "-p",
            "extract_output_format=csv",
        ],
        knowledge_base_name=knowledge_base_name,
    )

def main():
    """Main entry point for running the LeetTools MCP server."""
    logger.info("Starting LeetTools MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
