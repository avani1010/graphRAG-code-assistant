from tree_sitter import Parser
from tree_sitter_language_pack import get_language


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


def extract_entities(tree, code, file_path, language):
    """
    Extract code entities (functions, classes) from parse tree

    Args:
        tree: Tree-sitter parse tree
        code: Source code string
        file_path: Relative file path
        language: Language name

    Returns:
        Dictionary with 'functions', 'classes', 'calls' lists
    """
    entities = {
        'functions': [],
        'classes': [],
        'calls': []  # (caller, callee) pairs
    }

    if language == 'python':
        _extract_python_entities(tree.root_node, code, file_path, entities)
    elif language in ['javascript', 'typescript']:
        _extract_js_entities(tree.root_node, code, file_path, entities)
    elif language == 'go':
        _extract_go_entities(tree.root_node, code, file_path, entities)

    return entities


def _extract_python_entities(node, code, file_path, entities, current_class=None, current_function=None):
    """Extract Python functions and classes"""

    # Class definition
    if node.type == 'class_definition':
        class_name = None
        for child in node.children:
            if child.type == 'identifier':
                class_name = code[child.start_byte:child.end_byte]

                entities['classes'].append({
                    'name': class_name,
                    'file': file_path,
                    'full_name': f"{file_path}::{class_name}",
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                })

                # Parse class body
                for c in node.children:
                    _extract_python_entities(c, code, file_path, entities, current_class=class_name, current_function=None)
                return

    # Function definition
    elif node.type == 'function_definition':
        func_name = None
        for child in node.children:
            if child.type == 'identifier':
                func_name = code[child.start_byte:child.end_byte]

                if current_class:
                    full_name = f"{file_path}::{current_class}.{func_name}"
                    parent = f"{file_path}::{current_class}"
                else:
                    full_name = f"{file_path}::{func_name}"
                    parent = file_path

                entities['functions'].append({
                    'name': func_name,
                    'file': file_path,
                    'full_name': full_name,
                    'parent': parent,
                    'parent_type': 'class' if current_class else 'file',
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'code': code[node.start_byte:node.end_byte],
                })

                # Find calls in function body
                for c in node.children:
                    if c.type == 'block':
                        _find_calls(c, code, full_name, entities)
                return

    # Continue traversing
    for child in node.children:
        _extract_python_entities(child, code, file_path, entities, current_class, current_function)


def _extract_js_entities(node, code, file_path, entities, current_class=None):
    """Extract JavaScript/TypeScript functions and classes"""

    # Function declaration
    if node.type == 'function_declaration':
        func_name = None
        for child in node.children:
            if child.type == 'identifier':
                func_name = code[child.start_byte:child.end_byte]
                full_name = f"{file_path}::{func_name}"

                entities['functions'].append({
                    'name': func_name,
                    'file': file_path,
                    'full_name': full_name,
                    'parent': file_path,
                    'parent_type': 'file',
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'code': code[node.start_byte:node.end_byte],
                })

                _find_calls(node, code, full_name, entities)
                return

    # Class declaration
    elif node.type == 'class_declaration':
        class_name = None
        for child in node.children:
            if child.type == 'identifier':
                class_name = code[child.start_byte:child.end_byte]

                entities['classes'].append({
                    'name': class_name,
                    'file': file_path,
                    'full_name': f"{file_path}::{class_name}",
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                })

                for c in node.children:
                    _extract_js_entities(c, code, file_path, entities, current_class=class_name)
                return

    # Method definition (inside class)
    elif node.type == 'method_definition' and current_class:
        for child in node.children:
            if child.type == 'property_identifier':
                method_name = code[child.start_byte:child.end_byte]
                full_name = f"{file_path}::{current_class}.{method_name}"

                entities['functions'].append({
                    'name': method_name,
                    'file': file_path,
                    'full_name': full_name,
                    'parent': f"{file_path}::{current_class}",
                    'parent_type': 'class',
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'code': code[node.start_byte:node.end_byte],
                })

                _find_calls(node, code, full_name, entities)
                return

    # Continue traversing
    for child in node.children:
        _extract_js_entities(child, code, file_path, entities, current_class)


def _extract_go_entities(node, code, file_path, entities):
    """Extract Go functions"""

    if node.type == 'function_declaration':
        func_name = None
        for child in node.children:
            if child.type == 'identifier':
                func_name = code[child.start_byte:child.end_byte]
                full_name = f"{file_path}::{func_name}"

                entities['functions'].append({
                    'name': func_name,
                    'file': file_path,
                    'full_name': full_name,
                    'parent': file_path,
                    'parent_type': 'file',
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'code': code[node.start_byte:node.end_byte],
                })
                return

    for child in node.children:
        _extract_go_entities(child, code, file_path, entities)


def _find_calls(node, code, caller_name, entities):
    """Find function calls within a node"""

    if node.type in ['call', 'call_expression']:
        # Get the called function name
        for child in node.children:
            if child.type in ['identifier', 'attribute']:
                callee = code[child.start_byte:child.end_byte]
                entities['calls'].append((caller_name, callee))
                break

    for child in node.children:
        _find_calls(child, code, caller_name, entities)