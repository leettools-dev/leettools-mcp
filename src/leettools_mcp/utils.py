"""
Utility functions for LeetTools MCP server.

This module provides common utility functions used by the MCP server.
"""

import os
import sys
import logging
import asyncio
import subprocess
from datetime import datetime
from typing import List, Tuple, Optional

from pydantic import BaseModel

from leettools_mcp.constants import (
    EnvironmentVars, Paths, ErrorCodes, FilePatterns, Instructions
)

logger = logging.getLogger("leettools_mcp")

# Ensure output directory exists
Paths.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Pydantic Models for structured return types
class CommandError(BaseModel):
    """Error response from a command execution"""
    error: bool = True
    message: str
    details: str
    code: str


class CommandResult(BaseModel):
    """Result of running a command or search operation"""
    success: bool
    log_path: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    content: Optional[str] = None
    instructions: Optional[str] = None
    error: Optional[str] = None


def find_leet_executable() -> str:
    """Find the correct leet executable."""
    # First check if there's a specific path set in environment
    if env_path := os.environ.get(EnvironmentVars.LEET_EXECUTABLE):
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
    venv_path = os.environ.get(EnvironmentVars.VIRTUAL_ENV)
    if venv_path:
        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        leet_path = os.path.join(venv_path, bin_dir, "leet")
        if os.path.exists(leet_path):
            logger.info(f"Found leet in virtual environment at: {leet_path}")
            return leet_path
    
    # Fall back to using the command name, which works if it's in PATH
    logger.info("Falling back to 'leet' command")
    return "leet"


def get_output_filepath(prefix: str) -> Tuple[str, str]:
    """Generate unique filepaths for saving output and logs."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Paths.OUTPUT_DIR / f"{prefix}_{timestamp}{FilePatterns.OUTPUT_SUFFIX}"
    log_file = Paths.OUTPUT_DIR / f"{prefix}_{timestamp}{FilePatterns.LOG_SUFFIX}"
    return str(output_file), str(log_file)


async def run_leet_command(cmd_args: List[str], log_path: str) -> CommandResult:
    """Run a LeetTools command asynchronously."""
    try:
        leet_executable = find_leet_executable()
        # Check if leet is available
        if not leet_executable or (leet_executable != "leet" and not os.path.exists(leet_executable)):
            error_content = CommandError(
                message="LeetTools executable not found",
                details="Please install LeetTools and make sure it's in your PATH.",
                code=ErrorCodes.EXECUTABLE_NOT_FOUND,
            )
            return CommandResult(
                success=False,
                content=error_content.model_dump_json(indent=2),
                stdout="",
                stderr="LeetTools executable not found."
            )

        # Construct the full command
        cmd = [leet_executable] + cmd_args
        
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
            return CommandResult(
                success=False,
                stdout=stdout_str,
                stderr=stderr_str,
                log_path=log_path
            )

        return CommandResult(
            success=True,
            log_path=log_path,
            stdout=stdout_str,
            stderr=stderr_str,
        )

    except Exception as e:
        logger.exception(f"Error running LeetTools command: {str(e)}")
        error_content = CommandError(
            message="Error running LeetTools command",
            details=str(e),
            code=ErrorCodes.COMMAND_EXECUTION_ERROR,
        )
        return CommandResult(
            success=False,
            content=error_content.model_dump_json(indent=2),
            error=str(e),
        )
