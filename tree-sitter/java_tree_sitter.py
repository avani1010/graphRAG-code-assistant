"""
Tree-sitter Java Parser Demo
Shows how tree-sitter parses Java code and what node types we get
"""

from tree_sitter import Parser
from tree_sitter_language_pack import get_language


def parse_java_file(file_path):
    """Parse a Java file and show the AST structure"""

    # Read the Java code
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Create parser
    parser = Parser(get_language('java'))
    tree = parser.parse(bytes(code, 'utf8'))

    return tree, code


def print_tree(node, code, indent=0, max_depth=10):
    """
    Print the AST tree structure
    Shows node types and their text content
    """
    if indent > max_depth:
        return

    # Get the text for this node
    node_text = code[node.start_byte:node.end_byte]

    # Limit text display length
    if len(node_text) > 50:
        node_text = node_text[:50] + "..."

    # Clean up newlines for display
    node_text = node_text.replace('\n', '\\n')

    # Print this node
    print("  " * indent + f"├─ {node.type}: '{node_text}'")

    # Print children
    for child in node.children:
        print_tree(child, code, indent + 1, max_depth)


def explore_class_declaration(node, code):
    """Detailed exploration of a class_declaration node"""
    print("\n" + "="*60)
    print("EXPLORING CLASS DECLARATION")
    print("="*60)

    for child in node.children:
        print(f"\nChild Type: {child.type}")
        print(f"Text: {code[child.start_byte:child.end_byte][:100]}")

        if child.type == 'modifiers':
            print("  -> Found modifiers:")
            for mod_child in child.children:
                if mod_child.type == 'marker_annotation':
                    print(f"     Annotation: {code[mod_child.start_byte:mod_child.end_byte]}")
                else:
                    print(f"     {mod_child.type}: {code[mod_child.start_byte:mod_child.end_byte]}")

        elif child.type == 'identifier':
            print(f"  -> Class name: {code[child.start_byte:child.end_byte]}")

        elif child.type == 'superclass':
            print(f"  -> Extends: {code[child.start_byte:child.end_byte]}")

        elif child.type == 'super_interfaces':
            print(f"  -> Implements: {code[child.start_byte:child.end_byte]}")


def explore_method_declaration(node, code):
    """Detailed exploration of a method_declaration node"""
    print("\n" + "="*60)
    print("EXPLORING METHOD DECLARATION")
    print("="*60)

    method_name = None
    annotations = []
    throws_list = []

    for child in node.children:
        print(f"\nChild Type: {child.type}")
        print(f"Text: {code[child.start_byte:child.end_byte][:100]}")

        if child.type == 'modifiers':
            print("  -> Found modifiers:")
            for mod_child in child.children:
                if mod_child.type == 'marker_annotation':
                    ann = code[mod_child.start_byte:mod_child.end_byte]
                    annotations.append(ann)
                    print(f"     Annotation: {ann}")
                elif 'annotation' in mod_child.type:
                    ann = code[mod_child.start_byte:mod_child.end_byte]
                    annotations.append(ann)
                    print(f"     Annotation: {ann}")

        elif child.type == 'identifier':
            method_name = code[child.start_byte:child.end_byte]
            print(f"  -> Method name: {method_name}")

        elif child.type == 'throws':
            print("  -> Throws clause found:")
            for throws_child in child.children:
                if throws_child.type == 'type_identifier':
                    exc = code[throws_child.start_byte:throws_child.end_byte]
                    throws_list.append(exc)
                    print(f"     Exception: {exc}")

        elif child.type == 'block':
            print("  -> Method body found")
            explore_method_body(child, code, indent=2)

    print(f"\n  Summary:")
    print(f"    Method: {method_name}")
    print(f"    Annotations: {annotations}")
    print(f"    Throws: {throws_list}")


def explore_method_body(node, code, indent=0):
    """Explore method body for try-catch, method calls, etc."""
    prefix = "  " * indent

    for child in node.children:
        if child.type == 'try_statement':
            print(f"{prefix}  -> Try-catch block found")
            explore_try_catch(child, code, indent + 2)

        elif child.type == 'throw_statement':
            exc_text = code[child.start_byte:child.end_byte]
            print(f"{prefix}  -> Throw statement: {exc_text[:50]}")

        elif child.type == 'method_invocation':
            method_call = code[child.start_byte:child.end_byte]
            print(f"{prefix}  -> Method call: {method_call[:50]}")

        # Recurse into children
        elif child.children:
            explore_method_body(child, code, indent)


def explore_try_catch(node, code, indent=0):
    """Explore try-catch statement"""
    prefix = "  " * indent

    for child in node.children:
        if child.type == 'catch_clause':
            print(f"{prefix}  -> Catch clause:")
            for catch_child in child.children:
                if catch_child.type == 'catch_formal_parameter':
                    for param_child in catch_child.children:
                        if param_child.type == 'catch_type':
                            exc_type = code[param_child.start_byte:param_child.end_byte]
                            print(f"{prefix}     Catches: {exc_type}")


def find_all_nodes_of_type(node, node_type, results=None):
    """Recursively find all nodes of a specific type"""
    if results is None:
        results = []

    if node.type == node_type:
        results.append(node)

    for child in node.children:
        find_all_nodes_of_type(child, node_type, results)

    return results


def main():
    """Main demo function"""

    print("="*60)
    print("TREE-SITTER JAVA PARSER DEMO")
    print("="*60)

    # Parse the sample Java file
    tree, code = parse_java_file('../parser/sample_code.java')
    for child in tree.root_node.children:
        print(f"\n {child}" )

    # print("\n1. FULL AST TREE (Top 3 levels)")
    # print("-" * 60)
    # print_tree(tree.root_node, code, max_depth=3)
    #
    # # Find all class declarations
    # print("\n\n2. CLASS DECLARATIONS")
    # print("-" * 60)
    # classes = find_all_nodes_of_type(tree.root_node, 'class_declaration')
    # print(f"Found {len(classes)} class(es)")
    #
    # if classes:
    #     explore_class_declaration(classes[0], code)
    #
    # # Find all method declarations
    # print("\n\n3. METHOD DECLARATIONS")
    # print("-" * 60)
    # methods = find_all_nodes_of_type(tree.root_node, 'method_declaration')
    # print(f"Found {len(methods)} method(s)")
    #
    # for i, method in enumerate(methods[:2], 1):  # Show first 2 methods
    #     print(f"\n--- Method {i} ---")
    #     explore_method_declaration(method, code)
    #
    # # Find all imports
    # print("\n\n4. IMPORTS")
    # print("-" * 60)
    # imports = find_all_nodes_of_type(tree.root_node, 'import_declaration')
    # print(f"Found {len(imports)} import(s)")
    # for imp in imports:
    #     imp_text = code[imp.start_byte:imp.end_byte]
    #     print(f"  - {imp_text}")
    #
    # # Find all annotations
    # print("\n\n5. ANNOTATIONS")
    # print("-" * 60)
    # annotations = (
    #         find_all_nodes_of_type(tree.root_node, 'marker_annotation') +
    #         find_all_nodes_of_type(tree.root_node, 'annotation')
    # )
    # print(f"Found {len(annotations)} annotation(s)")
    # for ann in annotations:
    #     ann_text = code[ann.start_byte:ann.end_byte]
    #     print(f"  - {ann_text}")
    #
    # # Find all try statements
    # print("\n\n6. TRY-CATCH BLOCKS")
    # print("-" * 60)
    # try_stmts = find_all_nodes_of_type(tree.root_node, 'try_statement')
    # print(f"Found {len(try_stmts)} try-catch block(s)")
    # for try_stmt in try_stmts:
    #     print("\n  Exploring try-catch:")
    #     explore_try_catch(try_stmt, code, indent=2)
    #
    # # Find all method invocations (calls)
    # print("\n\n7. METHOD CALLS")
    # print("-" * 60)
    # calls = find_all_nodes_of_type(tree.root_node, 'method_invocation')
    # print(f"Found {len(calls)} method call(s)")
    # for call in calls[:10]:  # Show first 10
    #     call_text = code[call.start_byte:call.end_byte]
    #     # Get just the method name if possible
    #     for child in call.children:
    #         if child.type == 'identifier':
    #             method_name = code[child.start_byte:child.end_byte]
    #             print(f"  - {method_name}()")
    #             break
    #     else:
    #         print(f"  - {call_text[:40]}...")
    #
    # print("\n" + "="*60)
    # print("DEMO COMPLETE")
    # print("="*60)
    # print("\nKey Node Types for Java:")
    # print("  - class_declaration")
    # print("  - method_declaration")
    # print("  - field_declaration")
    # print("  - marker_annotation / annotation")
    # print("  - modifiers")
    # print("  - superclass (extends)")
    # print("  - super_interfaces (implements)")
    # print("  - throws")
    # print("  - try_statement")
    # print("  - catch_clause")
    # print("  - throw_statement")
    # print("  - method_invocation")
    # print("  - import_declaration")
    # print("  - constructor_declaration")


if __name__ == "__main__":
    main()