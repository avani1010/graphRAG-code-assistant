import os

# Neo4j connection settings (can be overridden by environment variables)
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Language detection mapping
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.go': 'go',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.html': 'html',
    '.css' : 'css',
    '.json' : 'json',
    '.yaml' : 'yaml',
    '.yml' : 'yaml',
    '.toml' : 'toml',
    '.rst' : 'rst'
}

# Directories to skip
SKIP_DIRS = {
    'node_modules',
    'venv',
    '.venv',
    'env',
    '__pycache__',
    '.git',
    'build',
    'dist',
    '.egg-info',
    'vendor',
}