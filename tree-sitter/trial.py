import subprocess
import os
from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from pathlib import Path

repo_url = "https://github.com/psf/requests"
target_dir = "../temp_repo"
tree=None

def clone_repo(url, dest):
    if not os.path.exists(dest):
        print(f"Cloning {url}...")
        # This is the same as typing 'git clone <url> <dest>' in the terminal
        result = subprocess.run(["git", "clone", url, dest], capture_output=True, text=True)

        if result.returncode == 0:
            print("Clone successful!")
        else:
            print(f"Error cloning: {result.stderr}")
    else:
        print("Directory already exists.")

def get_language_from_file(filename):
    """Map file extension to tree-sitter language"""
    ext_map = {
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

    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang

    return None

def print_tree(node, depth=0):
    # Create indentation based on how deep the node is
    indent = "  " * depth

    # Print the type of node and its text content (if it's a leaf node)
    node_text = node.text.decode('utf8').replace('\n', ' ')
    if len(node_text) > 30:  # Keep it short for the console
        node_text = node_text[:27] + "..."

    print(f"{indent}{node.type} [{node_text}]")

    # Recursively print all children
    for child in node.children:
        print_tree(child, depth + 1)


def find_functions(node):
    if node.type == 'function_definition':
        # Get function name (it's an 'identifier' child)
        for child in node.children:
            if child.type == 'identifier':
                name = code[child.start_byte:child.end_byte]
                print(f"  - {name}")
                break

    # Keep searching in children
    for child in node.children:
        find_functions(child)

print("Functions found:")



# Usage:
clone_repo(repo_url, target_dir)
repo_path = Path(target_dir)

for root, dirs, files in os.walk(repo_path):
    for file in files:
        lang = get_language_from_file(file)
        if lang == 'python':
            file_path = os.path.join(root, file)
            print(f"Parsing {file_path} as {lang}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            parser = Parser(get_language(lang))
            tree = parser.parse(bytes(code, "utf8"))
            print(f"Parsed {file} successfully!")

print_tree(tree.root_node)
find_functions(tree.root_node)


