from typing import Optional, Callable, Dict, Any
from pydantic import BaseModel

from leettools_mcp.constants import Instructions

class CommandOptions(BaseModel):
    """Options for command execution"""
    output_prefix: str
    error_code: str
    instructins: Optional[str] = None
    no_results_message: Optional[str] = None
    no_results_code: Optional[str] = None
    read_output_file: bool = False
    no_stdout_return: bool = True
    no_stderr_return: bool = True
    stdout_processor: Optional[Callable[[str], Dict[str, Any]]] = None

    @staticmethod
    def for_kb_search(kb_name: str) -> 'CommandOptions':
        """Create options for knowledge base search"""
        from leettools_mcp.constants import FilePrefixes, ErrorCodes
        return CommandOptions(
            output_prefix=f"{FilePrefixes.KB_SEARCH}_{kb_name}",
            error_code=ErrorCodes.KB_SEARCH_FAILED,
            instructins="".join(Instructions.SEARCH_CITATIONS),
            no_results_message="No knowledge base results found",
            no_results_code=ErrorCodes.NO_KB_RESULTS,
            read_output_file=True
        )
        
    @staticmethod
    def for_web_search(kb_name: str) -> 'CommandOptions':
        """Create options for web search"""
        from leettools_mcp.constants import FilePrefixes, ErrorCodes
        return CommandOptions(
            output_prefix=f"{FilePrefixes.WEB_SEARCH}_{kb_name}",
            error_code=ErrorCodes.WEB_SEARCH_FAILED,
            instructins="".join(Instructions.SEARCH_CITATIONS),
            no_results_message="No web search results found",
            no_results_code=ErrorCodes.NO_WEB_SEARCH_RESULTS,
            read_output_file=True
        )
        
    @staticmethod
    def for_kb_operation(operation: str) -> 'CommandOptions':
        """Create options for knowledge base operations"""
        from leettools_mcp.constants import FilePrefixes, ErrorCodes
        return CommandOptions(
            output_prefix=f"{FilePrefixes.KB_OPS}_{operation}",
            error_code=ErrorCodes.KB_OPERATION_FAILED,
            read_output_file=False,
            no_stdout_return=True,
            no_stderr_return=True
        )

    @staticmethod
    def for_list_kb() -> 'CommandOptions':
        """Create options specifically for list_kb operation"""
        from leettools_mcp.constants import FilePrefixes, ErrorCodes
        
        def process_list_kb_stdout(stdout: str) -> Dict[str, Any]:
            """Process stdout from list_kb command to extract KB information"""
            kb_lines = []
            for line in stdout.splitlines():
                if line.startswith("Org:"):
                    kb_lines.append(line)
            
            result = {
                "content": "\n".join(kb_lines) if kb_lines else "No knowledge bases found."
            }
            return result
        
        return CommandOptions(
            output_prefix=f"{FilePrefixes.KB_OPS}_list_kb",
            error_code=ErrorCodes.KB_OPERATION_FAILED,
            read_output_file=False,
            no_stdout_return=False,
            no_stderr_return=True,
            stdout_processor=process_list_kb_stdout
        )

