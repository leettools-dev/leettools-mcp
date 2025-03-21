# LeetTools MCP Scripts

This directory contains utility scripts for testing and working with the LeetTools MCP server.

## Available Scripts

### test_tool.py

A utility script to test individual MCP tool functions directly from the command line.

#### Setup

First, make the script executable:

```bash
chmod +x scripts/test_tool.py
```

#### Usage

When running from the project root directory:

```bash
# List all knowledge bases
scripts/test_tool.py list_kb --pretty

# Search a knowledge base
scripts/test_tool.py kb_search --query "What is MCP?" --kb mcp_search --pretty

# Execute a web search
scripts/test_tool.py web_search --query "Claude 3 model context protocol" --max-results 5 --pretty 

# Create a new knowledge base
scripts/test_tool.py create_kb --kb my_test_kb --pretty

# Add local files to a knowledge base
scripts/test_tool.py add_local_to_kb --local-path ~/Documents/papers --kb paper_kb --pretty
```

When running from within the scripts directory:

```bash
# List all knowledge bases
./test_tool.py list_kb --pretty
```

The `--pretty` flag formats the JSON output and displays the content separately for better readability.
