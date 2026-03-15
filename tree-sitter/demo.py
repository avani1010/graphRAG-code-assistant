"""
SUPER SIMPLE Tree-sitter Examples
The absolute minimum you need to know
"""

from tree_sitter import Parser
from tree_sitter_language_pack import get_language

print("="*60)
print("MINIMAL TREE-SITTER EXAMPLES")
print("="*60)

# ============================================================
# EXAMPLE 1: Parse Python (3 lines)
# ============================================================
print("\n📝 Example 1: Parse Python Code (Simplest)")
print("-"*60)

code = """
class AuthService:
    def login(self, username, password):
        return vale(username, password)

    def validate(self, username, password):
        return True
class someother:
    def login(self, username, password):
        return vale(username, password)
print("stuff")
"""

parser = Parser(get_language('python'))
tree = parser.parse(bytes(code, 'utf8'))
print(f"root: {tree.root_node.type}")
for child in tree.root_node.children:
    print(f"\ntype: {child.type} , \nid : {child.id}, \nchildren : {child.children}, \nparent: {child.parent.type}")
# print(f"Code: {code}")
# print(f"Root node type: {tree.root_node.type}")
# print(f"First child type: {tree.root_node.children[0].type}")
# print(tree.root_node)
# print(tree.root_node.children[1].children)
# print(dir(tree))
# # ============================================================
# # EXAMPLE 2: Get the actual text from nodes
# # ============================================================
# print("\n📝 Example 2: Extract Text from Nodes")
# print("-"*60)
#
# code = """
# def add(a, b):
#     return a + b
# """
#
# parser = Parser(get_language('python'))
# tree = parser.parse(bytes(code, 'utf8'))
#
# # Loop through top-level children
# for node in tree.root_node.children:
#     if node.type == 'function_definition':
#         # Get the text for this node
#         text = code[node.start_byte:node.end_byte]
#         print(f"Found function:\n{text}")
#
#
# # ============================================================
# # EXAMPLE 3: Find all function names
# # ============================================================
# print("\n📝 Example 3: Find All Function Names")
# print("-"*60)
#
# code = """
# def foo():
#     pass
#
# def bar():
#     pass
#
# def baz():
#     pass
# """
#
# parser = Parser(get_language('python'))
# tree = parser.parse(bytes(code, 'utf8'))
#
# # Simple recursive search
# def find_functions(node):
#     if node.type == 'function_definition':
#         # Get function name (it's an 'identifier' child)
#         for child in node.children:
#             if child.type == 'identifier':
#                 name = code[child.start_byte:child.end_byte]
#                 print(f"  - {name}")
#                 break
#
#     # Keep searching in children
#     for child in node.children:
#         find_functions(child)
#
# print("Functions found:")
# find_functions(tree.root_node)
#
#
# # ============================================================
# # EXAMPLE 4: Parse JavaScript
# # ============================================================
# print("\n📝 Example 4: Parse JavaScript")
# print("-"*60)
#
# js_code = """
# function greet(name) {
#     return "Hello " + name;
# }
# """
#
# parser = Parser(get_language('javascript'))
# tree = parser.parse(bytes(js_code, 'utf8'))
#
# print(f"Code: {js_code.strip()}")
# print(f"Root type: {tree.root_node.type}")
# print(f"Has function: {any(c.type == 'function_declaration' for c in tree.root_node.children)}")
#
#
# # ============================================================
# # EXAMPLE 5: Parse TypeScript
# # ============================================================
# print("\n📝 Example 5: Parse TypeScript")
# print("-"*60)
#
# ts_code = """
# function add(a: number, b: number): number {
#     return a + b;
# }
# """
#
# parser = Parser(get_language('typescript'))
# tree = parser.parse(bytes(ts_code, 'utf8'))
#
# print(f"Code: {ts_code.strip()}")
# print(f"Successfully parsed TypeScript: {tree.root_node.type == 'program'}")
#
#
# # ============================================================
# # EXAMPLE 6: Parse Go
# # ============================================================
# print("\n📝 Example 6: Parse Go")
# print("-"*60)
#
# go_code = """
# package main
#
# func add(a int, b int) int {
#     return a + b
# }
# """
#
# parser = Parser(get_language('go'))
# tree = parser.parse(bytes(go_code, 'utf8'))
#
# print(f"Code: {go_code.strip()}")
# print(f"Root type: {tree.root_node.type}")
#
#
# # ============================================================
# # EXAMPLE 7: Find function calls
# # ============================================================
# print("\n📝 Example 7: Find Function Calls")
# print("-"*60)
#
# code = """
# def helper():
#     return 42
#
# def main():
#     x = helper()
#     y = print(x)
#     return x
# """
#
# parser = Parser(get_language('python'))
# tree = parser.parse(bytes(code, 'utf8'))
#
# def find_calls(node):
#     if node.type == 'call':
#         # Get what's being called
#         func = node.children[0]
#         name = code[func.start_byte:func.end_byte]
#         print(f"  - Calling: {name}")
#
#     for child in node.children:
#         find_calls(child)
#
# print("Function calls found:")
# find_calls(tree.root_node)
#
#
# # ============================================================
# # EXAMPLE 8: Parse a class
# # ============================================================
# print("\n📝 Example 8: Parse a Class")
# print("-"*60)
#
# code = """
# class Calculator:
#     def add(self, a, b):
#         return a + b
#
#     def subtract(self, a, b):
#         return a - b
# """
#
# parser = Parser(get_language('python'))
# tree = parser.parse(bytes(code, 'utf8'))
#
# def find_classes(node):
#     if node.type == 'class_definition':
#         # Get class name
#         for child in node.children:
#             if child.type == 'identifier':
#                 name = code[child.start_byte:child.end_byte]
#                 print(f"\nClass: {name}")
#
#                 # Find methods in this class
#                 for subchild in node.children:
#                     if subchild.type == 'block':
#                         for method in subchild.children:
#                             if method.type == 'function_definition':
#                                 for m in method.children:
#                                     if m.type == 'identifier':
#                                         method_name = code[m.start_byte:m.end_byte]
#                                         print(f"  - Method: {method_name}")
#                                         break
#                 break
#
#     for child in node.children:
#         find_classes(child)
#
# find_classes(tree.root_node)
#
#
# # ============================================================
# # EXAMPLE 9: Detect language from file extension
# # ============================================================
# print("\n📝 Example 9: Detect Language from Filename")
# print("-"*60)
#
# def get_language_from_file(filename):
#     """Map file extension to tree-sitter language"""
#     ext_map = {
#         '.py': 'python',
#         '.js': 'javascript',
#         '.ts': 'typescript',
#         '.go': 'go',
#         '.java': 'java',
#         '.cpp': 'cpp',
#         '.c': 'c',
#         '.rs': 'rust',
#         '.rb': 'ruby',
#     }
#
#     for ext, lang in ext_map.items():
#         if filename.endswith(ext):
#             return lang
#
#     return None
#
# filenames = ['app.py', 'script.js', 'main.go', 'server.ts']
# for filename in filenames:
#     lang = get_language_from_file(filename)
#     print(f"{filename} → {lang}")
#
#
# # ============================================================
# # EXAMPLE 10: The ABSOLUTE MINIMUM
# # ============================================================
# print("\n📝 Example 10: Absolute Minimum (Copy-Paste This!)")
# print("-"*60)
#
# print("""
# # Just 3 lines to parse any code:
#
# from tree_sitter import Parser
# from tree_sitter_language_pack import get_language
#
# code = "def hello(): pass"
# tree = Parser(get_language('python')).parse(bytes(code, 'utf8'))
# print(tree.root_node.type)  # Output: module
# """)
#
# print("\nKey takeaways:")
# print("1. Parser(get_language('python')) - creates a parser")
# print("2. parser.parse(bytes(code, 'utf8')) - parses code")
# print("3. tree.root_node - gets the root of parse tree")
# print("4. node.children - gets child nodes")
# print("5. code[node.start_byte:node.end_byte] - gets text")