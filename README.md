# LeetTools MCP Server

An MCP server implementation that integrates the LeetTools, providing both web and local search capabilities.

## What is LeetTools?
LeetTools is an AI-powered search assistant that enables highly customizable search workflows and delivers tailored output formats from both web and local knowledge bases. Its automated document pipeline handles data ingestion, indexing, and storage, so you can focus on developing workflows without worrying about the underlying infrastructure.

For more details, visit the [LeetTools GitHub Repository](https://github.com/leettools-dev/leettools).

## Smart Search

LeetTools MCP server distinguishes itself from other web search MCP servers by integrating searching, scraping, and filtering into a single tool. By leveraging web search and an in-memory vector database, it delivers highly relevant and accurate results.

## Tools

### `web_search`
- Execute web searches with pagination and filtering
- **Inputs:**
  - `query` (string): web search query
  - `search_max_results` (number, optional): Maximum Search Results (default 1)
  - `search_iteration` (number, optional): Search Pagination (default 1)

### `knowledge_base_search`
- Search for local knowledge base
- **Inputs:**
  - `query` (string): search query for local knowledge base
  - `knowledge_base_name` (string, optional): name of local knowledge base

## Set up your environment (MacOS/Linux)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone this repository

git clone https://github.com/leettools-dev/leettools-mcp.git
cd leettools-mcp

# Create virtual environment and install package in development mode
uv venv
source .venv/bin/activate
uv add torch==2.2.2 "mcp[cli]" leettools

# LeetHome: By default the data is saved under ${HOME}/leettools, you can set a different LeetHome
export LEET_HOME=<your_leet_home>
export EDS_LLM_API_KEY=<your_openai_api_key>

# Test local exectuion of leettools
leet flow -t search -k mcp_search -q "Anthropic MCP"
```

## Usage with Claude Desktop
1. Follow this [link](https://support.anthropic.com/en/articles/10065433-installing-claude-for-desktop) to install Claude Destop App.

2. Go to Claude > Settings > Developer > Edit Config > claude_desktop_config.json to include the following:

    ```json
    {
        "mcpServers": {
            "leettools": {
                "command": "uv",
                "args": [
                    "--directory",
                    "/ABSOLUTE/PATH/TO/PARENT/FOLDER/leettools-mcp",
                    "run",
                    "leettools-mcp"
                ],
                "env": {
                    "LEET_HOME": "Your LeetHome location",
                    "EDS_LLM_API_KEY": "Your OpenAI API Key"
                }
            }
        }
    }
    ```
    > **Important:** You may need to put the full path to the `uv` executable in the command field. 
    > Find it by running `which uv` on macOS/Linux or `where uv` on Windows.

3. Restart Claude Desktop then make sure it is picking up the tools we've exposed in this mcp server. You can do this by looking for the hammer icon:
   <p align="center">
     <img src="assets/mcp-server-hammer.png" alt="Logo" width="450"/>
   </p>

   After clicking on the hammer icon, you should see two tools listed:
   <p align="center">
     <img src="assets/mcp-server-tools.png" alt="Logo" width="450"/>
   </p>

4. If you encounter issues, follow this [link](https://modelcontextprotocol.io/docs/tools/debugging#debugging-in-claude-desktop) for debugging guidance. You can also check the MCP server log with the following command:
    ```bash
    tail -n 200 -F ~/Library/Logs/Claude/mcp-server-leettools.log
    ```

## Example Usage

### Web Search Examples

Try asking Claude:

> "Can you do a web search and tell me why ServiceNow acquired Moveworks?"

Claude will use the `web_search` tool to retrieve the latest information about the acquisition.

### Knowledge Base Search Examples

Follow these steps to search your own documents:

1. **First, add a document to your knowledge base**:
   ```bash
   leet kb add-url -k llmbook -r "https://arxiv.org/pdf/2501.09223"
   ```

2. **Then ask a question in Claude Desktop**:
   > "Can you search knowledge base 'llmbook' and give me a brief explanation of LLM?"

Claude will retrieve information from your knowledge base and provide a response based on the documents you've added.

## License

The LeetTools MCP server is licensed under the Apache License, Version 2.0 (the "License"). You may not use this software except in compliance with the License. A copy of the License is provided in the LICENSE file in this repository.

Unless required by applicable law or agreed to in writing, the software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.