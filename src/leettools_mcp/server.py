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

from leettools_mcp.constants import CommandArgs, ErrorCodes

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


async def perform_operation(
    operation_type: str, args: List[str], options: CommandOptions
) -> str:
    """
    Common operation handler for all LeetTools operations.

    Args:
        operation_type: Type of operation (for logging)
        args: Command line arguments to pass to leet
        options: CommandOptions object with execution options

    Returns:
        JSON string with the operation results
    """
    try:
        logger.info(f"Performing {operation_type} operation")

        # Create the output file paths
        output_path, log_path = get_output_filepath(options.output_prefix)
        logger.info(f"Will save output to: {output_path}")
        logger.info(f"Will save logs to: {log_path}")

        # Add output path to arguments if we're going to read it
        cmd_args = args.copy()
        if options.read_output_file:
            cmd_args.extend(["-o", output_path])

        # Run the command
        result = await run_leet_command(cmd_args, log_path)

        # Handle command failure
        if not result.success:
            error_msg = result.stderr or "Unknown error"
            logger.error(f"{operation_type} operation failed: {error_msg}")
            error = CommandError(
                message=f"Error running {operation_type}",
                details=error_msg,
                code=options.error_code or f"{operation_type.upper()}_FAILED",
            )
            return error.model_dump_json(indent=2)

        # If we need to read the output file
        if options.read_output_file:
            content = ""
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                with open(output_path, "r") as f:
                    content = f.read()
                logger.info(
                    f"Read {len(content)} bytes from output file: {output_path}"
                )
            else:
                logger.warning(f"Output file empty or missing: {output_path}")

            # Check if we have any content
            if not content and options.no_results_message:
                error = CommandError(
                    message=options.no_results_message,
                    details=f"The {operation_type} operation did not produce any content.",
                    code=options.no_results_code
                    or f"NO_{operation_type.upper()}_RESULTS",
                )
                return error.model_dump_json(indent=2)

            # Update the result with content from the output file
            result.content = content

            # Add instructions to the result if available
            if options.instructins:
                result.instructions = options.instructins

        # Process stdout if needed using the tool-specific processor
        if options.stdout_processor and result.stdout:
            try:
                # Apply the tool-specific stdout processor
                processed_result = options.stdout_processor(result.stdout)

                # Update the result object with processed fields
                for key, value in processed_result.items():
                    setattr(result, key, value)

                logger.info(f"Processed stdout for {operation_type}")
            except Exception as e:
                logger.error(f"Error processing stdout: {str(e)}")

        # remove stdout and stderr from the result if not required
        if options.no_stdout_return:
            result.stdout = None
        if options.no_stderr_return:
            result.stderr = None

        # Convert result to JSON string
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
        options=CommandOptions.for_kb_operation("add_local_to_kb"),
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
        options=CommandOptions.for_kb_operation("create_kb"),
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
        options=CommandOptions.for_list_kb(),
    )


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
        options=CommandOptions.for_web_search(CommandArgs.DEFAULT_KB_NAME),
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
        options=CommandOptions.for_kb_search(knowledge_base_name),
    )


def main():
    """Main entry point for running the LeetTools MCP server."""
    logger.info("Starting LeetTools MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
