"""
Ultra-Simplified Universal Multi-Language Code Parser
Only FILES (no modules) - 3 relationships: CONTAINS, CALLS, IMPORTS
Works with ANY tree-sitter supported language (40+)
"""

from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from pathlib import Path


# Universal node type patterns across languages
NODE_PATTERNS = {
    # Class-like structures
    'class': [
        'class_definition',      # Python
        'class_declaration',     # JavaScript, TypeScript, Java, C++, C#
        'class_specifier',       # C++
        'struct_item',           # Rust
        'struct_specifier',      # C
        'type_declaration',      # Go (for structs)
        'class',                 # Ruby
        'object_definition',     # Scala
        'trait_definition',      # Rust, Scala
    ],

    # Function-like structures
    'function': [
        'function_definition',    # Python, C
        'function_declaration',   # JavaScript, TypeScript, Go, C++
        'function_item',          # Rust
        'method_declaration',     # Java, C#
        'method_definition',      # JavaScript (in class)
        'function',               # Ruby
        'method',                 # Ruby
        'arrow_function',         # JavaScript
        'lambda_expression',      # Java, C#
    ],

    # Import-like structures
    'import': [
        'import_statement',       # Python, JavaScript
        'import_from_statement',  # Python
        'import_declaration',     # Java, Go
        'use_declaration',        # Rust, PHP
        'require_call',           # Ruby
        'include_statement',      # C, C++
        'using_directive',        # C#
        'package_clause',         # Go
    ],

    # Function/Method calls
    'call': [
        'call',                   # Python
        'call_expression',        # JavaScript, TypeScript, C, C++
        'method_invocation',      # Java
        'function_call_expression',  # Lua
        'invocation_expression',  # C#
    ],

    # Identifier patterns (names of things)
    'identifier': [
        'identifier',             # Universal
        'type_identifier',        # TypeScript, Go, C++
        'property_identifier',    # JavaScript
        'field_identifier',       # C, C++
        'constant',               # Ruby
    ],

    # String literals (for import paths)
    'string': [
        'string',                 # Universal
        'string_literal',         # C, C++
        'interpreted_string_literal',  # Go
        'raw_string_literal',     # Rust
    ],
}

# Globals to filter out (don't create nodes for these)
GLOBAL_NAMES = {
    # JavaScript/TypeScript globals
    'console', 'window', 'document', 'navigator', 'process', 'global',
    'module', 'exports', 'require', 'setTimeout', 'setInterval',
    'localStorage', 'sessionStorage', 'fetch', 'URL', 'Promise',
    # Python builtins
    'print', 'len', 'str', 'int', 'list', 'dict', 'set', 'tuple',
    'open', 'range', 'map', 'filter', 'sum', 'max', 'min', 'sorted',
    'enumerate', 'zip', 'all', 'any', 'isinstance', 'type',
    # Common test/boilerplate
    'describe', 'it', 'test', 'expect', 'beforeEach', 'afterEach',
}


def parse_file(file_path, language):
    """
    Parse a code file using tree-sitter

    Args:
        file_path: Path to file
        language: Language name (python, javascript, etc.)

    Returns:
        Tuple of (tree, source_code)
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    parser = Parser(get_language(language))
    tree = parser.parse(bytes(code, 'utf8'))

    return tree, code


def extract_entities_and_relationships(tree, code, file_path, language, repo_root=None):
    """
    Universal extractor for ALL tree-sitter supported languages

    Args:
        tree: Tree-sitter parse tree
        code: Source code string
        file_path: Relative file path
        language: Language name
        repo_root: Repository root path (optional)

    Returns:
        Dictionary with 'entities' and 'relationships' lists
    """
    result = {
        'entities': {
            'directories': [],
            'files': [],
            'classes': [],
            'functions': [],
            'methods': [],
        },
        'relationships': {
            'CONTAINS': [],
            'CALLS': [],
            'IMPORTS': [],
        }
    }

    # Add file entity
    result['entities']['files'].append({
        'path': file_path,
        'name': Path(file_path).name,
        'language': language,
        'type': 'file'
    })

    # Extract directory hierarchy
    if repo_root:
        _extract_directory_hierarchy(file_path, repo_root, result)

    # Universal extraction - works for ALL languages
    _extract_universal(tree.root_node, code, file_path, language, result)

    return result


def _extract_directory_hierarchy(file_path, repo_root, result):
    """Extract directory structure as entities (universal)"""
    path = Path(file_path)
    directories = []

    current = path.parent
    while current != Path('.') and current != Path('/'):
        directories.insert(0, str(current))
        current = current.parent

    for i, dir_path in enumerate(directories):
        if not any(d['path'] == dir_path for d in result['entities']['directories']):
            result['entities']['directories'].append({
                'path': dir_path,
                'name': Path(dir_path).name,
                'type': 'directory'
            })

        # CONTAINS: directory -> subdirectory
        if i < len(directories) - 1:
            result['relationships']['CONTAINS'].append({
                'from': dir_path,
                'from_type': 'directory',
                'to': directories[i + 1],
                'to_type': 'directory'
            })
        # CONTAINS: directory -> file
        else:
            result['relationships']['CONTAINS'].append({
                'from': dir_path,
                'from_type': 'directory',
                'to': file_path,
                'to_type': 'file'
            })


def _extract_universal(node, code, file_path, language, result, context=None):
    """
    Universal extractor using pattern matching
    Works for ANY tree-sitter supported language

    Args:
        node: Current AST node
        code: Source code
        file_path: File path
        language: Language name
        result: Results dictionary
        context: Current context (class name, function name, etc.)
    """
    if context is None:
        context = {
            'current_class': None,
            'current_function': None,
        }

    node_type = node.type

    # ========== IMPORTS - SKIP (no longer tracking) ==========
    # We're not extracting imports anymore since we removed modules

    # ========== CLASSES ==========
    if _is_class_node(node_type):
        _extract_class(node, code, file_path, language, result, context)
        return  # Don't traverse further (handled in extract_class)

    # ========== FUNCTIONS ==========
    elif _is_function_node(node_type):
        if context['current_class']:
            # It's a method inside a class
            _extract_method(node, code, file_path, language, result, context)
        else:
            # It's a standalone function
            _extract_function(node, code, file_path, language, result, context)
        return  # Don't traverse further (handled in extract)

    # ========== FUNCTION CALLS ==========
    elif _is_call_node(node_type) and context['current_function']:
        _extract_call(node, code, context['current_function'], result)

    # Continue traversing children
    for child in node.children:
        _extract_universal(child, code, file_path, language, result, context)


# ========== PATTERN MATCHING HELPERS ==========

def _is_class_node(node_type):
    return node_type in NODE_PATTERNS['class']

def _is_function_node(node_type):
    return node_type in NODE_PATTERNS['function']

def _is_call_node(node_type):
    return node_type in NODE_PATTERNS['call']

def _is_identifier_node(node_type):
    return node_type in NODE_PATTERNS['identifier']


# ========== EXTRACTORS ==========

def _extract_class(node, code, file_path, language, result, context):
    """Extract class - works for all OOP languages"""
    class_name = _find_first_identifier(node, code)

    if not class_name or class_name.lower() in GLOBAL_NAMES:
        return

    full_name = f"{file_path}::{class_name}"

    # Add class entity
    result['entities']['classes'].append({
        'name': class_name,
        'full_name': full_name,
        'file': file_path,
        'start_line': node.start_point[0] + 1,
        'end_line': node.end_point[0] + 1,
        'language': language,
        'type': 'class'
    })

    # CONTAINS: file -> class
    result['relationships']['CONTAINS'].append({
        'from': file_path,
        'from_type': 'file',
        'to': full_name,
        'to_type': 'class'
    })

    # Extract class body with updated context
    new_context = context.copy()
    new_context['current_class'] = full_name

    for child in node.children:
        _extract_universal(child, code, file_path, language, result, new_context)


def _extract_function(node, code, file_path, language, result, context):
    """Extract standalone function - works for all languages"""
    func_name = _find_first_identifier(node, code)

    if not func_name or func_name.lower() in GLOBAL_NAMES:
        return

    full_name = f"{file_path}::{func_name}"

    # Add function entity
    result['entities']['functions'].append({
        'name': func_name,
        'full_name': full_name,
        'file': file_path,
        'start_line': node.start_point[0] + 1,
        'end_line': node.end_point[0] + 1,
        'code': code[node.start_byte:node.end_byte],
        'language': language,
        'type': 'function'
    })

    # CONTAINS: file -> function
    result['relationships']['CONTAINS'].append({
        'from': file_path,
        'from_type': 'file',
        'to': full_name,
        'to_type': 'function'
    })

    # Extract function body with updated context
    new_context = context.copy()
    new_context['current_function'] = full_name

    for child in node.children:
        _extract_universal(child, code, file_path, language, result, new_context)


def _extract_method(node, code, file_path, language, result, context):
    """Extract method - works for all OOP languages"""
    method_name = _find_first_identifier(node, code)

    if not method_name or method_name.lower() in GLOBAL_NAMES:
        return

    full_name = f"{context['current_class']}.{method_name}"

    # Add method entity
    result['entities']['methods'].append({
        'name': method_name,
        'full_name': full_name,
        'file': file_path,
        'class': context['current_class'],
        'start_line': node.start_point[0] + 1,
        'end_line': node.end_point[0] + 1,
        'code': code[node.start_byte:node.end_byte],
        'language': language,
        'type': 'method'
    })

    # CONTAINS: class -> method
    result['relationships']['CONTAINS'].append({
        'from': context['current_class'],
        'from_type': 'class',
        'to': full_name,
        'to_type': 'method'
    })

    # Extract method body
    new_context = context.copy()
    new_context['current_function'] = full_name

    for child in node.children:
        _extract_universal(child, code, file_path, language, result, new_context)


def _extract_call(node, code, caller_full_name, result):
    """Extract function call - works for all languages"""
    callee = _find_first_identifier(node, code)

    if not callee or callee.lower() in GLOBAL_NAMES:
        return

    # CALLS: function -> function
    result['relationships']['CALLS'].append({
        'from': caller_full_name,
        'from_type': 'function',
        'to': callee,
        'to_type': 'function'
    })


# ========== HELPER FUNCTIONS ==========

def _find_first_identifier(node, code):
    """Find the first identifier in a node (usually the name)"""
    for child in node.children:
        if _is_identifier_node(child.type):
            name = code[child.start_byte:child.end_byte]
            # Skip if it's a global/builtin
            if name.lower() not in GLOBAL_NAMES:
                return name

        # Recursively search in child
        result = _find_first_identifier(child, code)
        if result:
            return result

    return None