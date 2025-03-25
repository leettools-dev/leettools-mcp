#!/usr/bin/env node
const { execSync, spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Setup log file in ~/.npm/_logs/
const homeDir = process.env.HOME || '';
const logDir = path.join(homeDir, '.npm', '_logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}
const LOG_FILE = path.join(logDir, 'leettools-mcp-server-debug.log');

// Helper to format extra info as key=value pairs.
function formatExtra(extra) {
  return Object.entries(extra)
    .map(([key, value]) => `${key}=${value}`)
    .join(' ');
}

// Write a plain text log entry to LOG_FILE.
function writeLog(level, message, extra = {}) {
  const extraStr = Object.keys(extra).length ? ` ${formatExtra(extra)}` : '';
  const entry = `${new Date().toISOString()} [${level.toUpperCase()}] ${message}${extraStr}\n`;
  try {
    fs.appendFileSync(LOG_FILE, entry);
  } catch (err) {
    process.exit(1);
  }
}

function logInfo(message, extra = {}) {
  writeLog('info', message, extra);
}

function logError(message, extra = {}) {
  writeLog('error', message, extra);
}

// Synchronous command runner that captures output and logs it.
function runCommandSync(cmd, args, options = {}) {
  logInfo(`Running command: ${cmd} ${args.join(' ')}`, { cwd: options.cwd || process.cwd() });
  const result = spawnSync(cmd, args, { encoding: 'utf8', shell: true, stdio: 'pipe', ...options });
  if (result.stdout) {
    result.stdout.split('\n').forEach(line => {
      if (line.trim()) logInfo(line.trim());
    });
  }
  if (result.stderr) {
    result.stderr.split('\n').forEach(line => {
      if (line.trim()) logError(line.trim());
    });
  }
  if (result.status !== 0) {
    logError(`Command "${cmd} ${args.join(' ')}" exited with code ${result.status}`);
    process.exit(result.status);
  }
}

// Asynchronous command runner that captures stdout and stderr and logs them.
function runCommandAsync(cmd, args, options = {}) {
  logInfo(`Running command: ${cmd} ${args.join(' ')}`, { cwd: options.cwd || process.cwd() });
  const proc = spawn(cmd, args, { stdio: 'pipe', shell: true, ...options });
  
  proc.stdout.on('data', (data) => {
    data.toString().split('\n').forEach(line => {
      if (line.trim()) logInfo(line.trim());
    });
  });
  
  proc.stderr.on('data', (data) => {
    data.toString().split('\n').forEach(line => {
      if (line.trim()) logError(line.trim());
    });
  });
  
  proc.on('error', (err) => {
    logError(`Failed to run command: ${cmd} ${args.join(' ')}`, { error: err.toString() });
    process.exit(1);
  });
  
  proc.on('exit', (code) => {
    if (code !== 0) {
      logError(`Command "${cmd} ${args.join(' ')}" exited with code ${code}`);
      process.exit(code);
    }
  });
  
  return proc;
}

// Retrieve the full path of uv. If uv is missing or not working, try to install it,
// then fall back to $HOME/.local/bin/uv if necessary.
function getUvPath() {
  try {
    const uvPath = execSync('which uv', { encoding: 'utf8', stdio: 'pipe' }).trim();
    execSync(`${uvPath} --version`, { stdio: 'pipe' });
    return uvPath;
  } catch (error) {
    logInfo('uv not found or not working. Attempting to install uv...');
    try {
      const installOutput = execSync('curl -LsSf https://astral.sh/uv/install.sh | sh', { encoding: 'utf8', shell: true, stdio: 'pipe' });
      if (installOutput) logInfo(installOutput);
    } catch (installError) {
      logError('Failed to install uv. Please install uv manually.', { installError: installError.toString() });
      process.exit(1);
    }
    try {
      const uvPath = execSync('which uv', { encoding: 'utf8', stdio: 'pipe' }).trim();
      execSync(`${uvPath} --version`, { stdio: 'pipe' });
      return uvPath;
    } catch (error2) {
      const fallbackPath = path.join(homeDir, '.local', 'bin', 'uv');
      if (fs.existsSync(fallbackPath)) {
        try {
          execSync(`${fallbackPath} --version`, { stdio: 'pipe' });
          logInfo(`Using fallback uv at ${fallbackPath}`);
          return fallbackPath;
        } catch (fallbackError) {
          logError('uv at fallback location is not working.', { fallbackError: fallbackError.toString() });
        }
      }
      logError('Error: uv still not found or working after installation.');
      process.exit(1);
    }
  }
}

const uvExecutable = getUvPath();
logInfo(`uv executable to be used: ${uvExecutable}`);

// Ensure that the repository "leettools-mcp" is cloned into the LEET_HOME folder.
// If LEET_HOME doesn't exist, create it.
function ensureClone() {
  if (!process.env.LEET_HOME) {
    logError('LEET_HOME environment variable is missing.');
    process.exit(1);
  }
  const targetDir = process.env.LEET_HOME;
  if (!fs.existsSync(targetDir)) {
    logInfo(`LEET_HOME directory (${targetDir}) does not exist. Creating it...`);
    fs.mkdirSync(targetDir, { recursive: true });
  }
  const repoDir = path.join(targetDir, 'leettools-mcp');
  if (!fs.existsSync(repoDir)) {
    logInfo(`Repository "leettools-mcp" not found in ${targetDir}. Cloning repository...`);
    runCommandSync('git', ['clone', 'https://github.com/leettools-dev/leettools-mcp.git', repoDir], { cwd: targetDir });
  } else {
    logInfo(`Repository "leettools-mcp" already exists in ${targetDir}.`);
  }
  return repoDir;
}

// Ensure the virtual environment exists inside the cloned repository.
function ensureVenv(repoDir) {
  const venvPath = path.join(repoDir, '.venv');
  if (!fs.existsSync(venvPath)) {
    logInfo('Virtual environment not found. Creating venv...');
    runCommandSync(uvExecutable, ['venv'], { cwd: repoDir });
  } else {
    logInfo('Virtual environment exists.');
  }
}

// Install Python dependencies via uv inside the cloned repository.
function installDependencies(repoDir) {
  logInfo('Installing Python dependencies using uv...');
  runCommandSync(uvExecutable, ['add', 'torch==2.2.2', 'mcp[cli]', 'leettools'], { cwd: repoDir });
}

function runServer(repoDir) {
  // Check for required environment variables; exit if missing.
  if (!process.env.LEET_HOME) {
    logError('LEET_HOME environment variable is missing.');
    process.exit(1);
  }
  if (!process.env.EDS_LLM_API_KEY) {
    logError('EDS_LLM_API_KEY environment variable is missing.');
    process.exit(1);
  }
  logInfo('Environment variables set', {
    LEET_HOME: process.env.LEET_HOME,
    EDS_LLM_API_KEY: process.env.EDS_LLM_API_KEY,
    UV_HTTP_TIMEOUT: 300
  });
  logInfo('Starting LeetTools MCP server...');

  // Run the uv command with stdio 'inherit' so that its output appears normally.
  const proc = spawn(uvExecutable, ['--directory', repoDir, 'run', 'leettools-mcp'], { 
    stdio: 'inherit', 
    shell: true, 
    cwd: repoDir,
    env: { ...process.env, UV_HTTP_TIMEOUT: '300' }
  });
  
  proc.on('error', (err) => {
    logError(`Failed to run server command: ${uvExecutable} --directory ${repoDir} run leettools-mcp`, { error: err.toString() });
    process.exit(1);
  });
  
  proc.on('exit', (code) => {
    if (code !== 0) {
      logError(`Server command exited with code ${code}`);
      process.exit(code);
    }
  });
}

// Main flow: clone repo into LEET_HOME, ensure uv, create venv, install dependencies, then run the server.
function main() {
  try {
    const repoDir = ensureClone();
    ensureVenv(repoDir);
    installDependencies(repoDir);
    runServer(repoDir);
  } catch (error) {
    logError('Error during execution', { error: error.toString() });
    process.exit(1);
  }
}

main();
