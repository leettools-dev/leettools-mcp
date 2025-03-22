#!/usr/bin/env node
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Helper to run shell commands with logging
function runCommand(cmd, options = {}) {
  console.log(`Running: ${cmd}`);
  execSync(cmd, { stdio: 'inherit', ...options });
}

// 1. Check if uv is installed; if not, install it
function ensureUv() {
  try {
    execSync('uv --version', { stdio: 'ignore' });
    console.log('uv is installed.');
  } catch (error) {
    console.log('uv is not installed. Installing uv...');
    runCommand('curl -LsSf https://astral.sh/uv/install.sh | sh');
  }
}

// 2. Ensure virtual environment is created (assumed to be at project root)
function ensureVenv() {
  const venvPath = path.join(__dirname, '.venv');
  if (!fs.existsSync(venvPath)) {
    console.log('Virtual environment not found. Creating venv...');
    runCommand('uv venv', { cwd: __dirname });
  } else {
    console.log('Virtual environment exists.');
  }
}

// 3. Install Python dependencies via uv (e.g. torch, mcp[cli], leettools)
function installDependencies() {
  console.log('Installing Python dependencies using uv...');
  // Change the command if you need additional options or different dependencies
  runCommand('uv add torch==2.2.2 "mcp[cli]" leettools', { cwd: __dirname });
}

// 4. Run the MCP server using uv
function runServer() {
  // Ensure required environment variables are set; users can override these
  process.env.LEET_HOME = process.env.LEET_HOME || '/default/leet_home';
  process.env.EDS_LLM_API_KEY = process.env.EDS_LLM_API_KEY || 'default_api_key';

  // Determine the absolute path to the directory containing your Python project.
  // For this example, we assume the Python code is in "src/leettools_mcp" and its parent is used by uv.
  const pythonProjectParent = path.join(__dirname, 'src');
  
  console.log('Starting LeetTools MCP server...');
  // Run the uv command to start the server.
  runCommand(`uv --directory "${pythonProjectParent}" run leettools-mcp`, { cwd: __dirname });
}

// Main flow
function main() {
  try {
    ensureUv();
    ensureVenv();
    installDependencies();
    runServer();
  } catch (error) {
    console.error('Error during execution:', error);
    process.exit(1);
  }
}

main();
