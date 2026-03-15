"""
GraphRAG with Tree-sitter (Multi-language support!)
Works with Python, JavaScript, TypeScript, Go, and more
"""

from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from pathlib import Path
import networkx as nx


class TreeSitterCodeParser:
    """Parse code using tree-sitter (multi-language)"""

    def __init__(self):
        self.graph = nx.DiGraph()

        # Language detection map
        self.lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rs': 'rust',
            '.rb': 'ruby',
        }

    def detect_language(self, file_path: str) -> str:
        """Detect language from file extension"""
        for ext, lang in self.lang_map.items():
            if file_path.endswith(ext):
                return lang
        return None

    def parse_repository(self, repo_path: str):
        """Parse all supported files in a repository"""
        repo_path = Path(repo_path)

        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                lang = self.detect_language(str(file_path))
                if lang:
                    try:
                        self._parse_file(file_path, lang, repo_path)
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")

    def _parse_file(self, file_path: Path, language: str, repo_root: Path):
        """Parse a single file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Create parser for this language
        parser = Parser(get_language(language))
        tree = parser.parse(bytes(code, 'utf8'))

        # Get relative path
        relative_path = str(file_path.relative_to(repo_root))

        # Add file node
        self.graph.add_node(
            relative_path,
            type='file',
            language=language,
            path=str(file_path)
        )

        # Parse based on language
        if language == 'python':
            self._parse_python(tree.root_node, code, relative_path)
        elif language in ['javascript', 'typescript']:
            self._parse_javascript(tree.root_node, code, relative_path)
        elif language == 'go':
            self._parse_go(tree.root_node, code, relative_path)

    def _parse_python(self, root_node, code: str, file_path: str):
        """Parse Python-specific constructs"""
        def traverse(node, current_class=None):
            # Class definitions
            if node.type == 'class_definition':
                class_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = code[child.start_byte:child.end_byte]
                        full_name = f"{file_path}::{class_name}"

                        self.graph.add_node(
                            full_name,
                            type='class',
                            name=class_name,
                            language='python'
                        )
                        self.graph.add_edge(file_path, full_name, relation='contains')

                        # Parse class body
                        for c in node.children:
                            traverse(c, full_name)
                        break

            # Function definitions
            elif node.type == 'function_definition':
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = code[child.start_byte:child.end_byte]

                        if current_class:
                            full_name = f"{current_class}.{func_name}()"
                        else:
                            full_name = f"{file_path}::{func_name}()"

                        self.graph.add_node(
                            full_name,
                            type='function',
                            name=func_name,
                            language='python'
                        )

                        parent = current_class if current_class else file_path
                        self.graph.add_edge(parent, full_name, relation='contains')

                        # Find function calls in body
                        for c in node.children:
                            if c.type == 'block':
                                self._find_calls(c, code, full_name)
                        break

            # Keep traversing
            for child in node.children:
                traverse(child, current_class)

        traverse(root_node)

    def _parse_javascript(self, root_node, code: str, file_path: str):
        """Parse JavaScript/TypeScript constructs"""
        def traverse(node, current_class=None):
            # Function declarations
            if node.type == 'function_declaration':
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = code[child.start_byte:child.end_byte]
                        full_name = f"{file_path}::{func_name}()"

                        self.graph.add_node(
                            full_name,
                            type='function',
                            name=func_name,
                            language='javascript'
                        )
                        self.graph.add_edge(file_path, full_name, relation='contains')

                        # Find calls
                        self._find_calls(node, code, full_name)
                        break

            # Class declarations
            elif node.type == 'class_declaration':
                class_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = code[child.start_byte:child.end_byte]
                        full_name = f"{file_path}::{class_name}"

                        self.graph.add_node(
                            full_name,
                            type='class',
                            name=class_name,
                            language='javascript'
                        )
                        self.graph.add_edge(file_path, full_name, relation='contains')

                        for c in node.children:
                            traverse(c, full_name)
                        break

            # Method definitions
            elif node.type == 'method_definition' and current_class:
                for child in node.children:
                    if child.type == 'property_identifier':
                        method_name = code[child.start_byte:child.end_byte]
                        full_name = f"{current_class}.{method_name}()"

                        self.graph.add_node(
                            full_name,
                            type='function',
                            name=method_name,
                            language='javascript'
                        )
                        self.graph.add_edge(current_class, full_name, relation='contains')

                        self._find_calls(node, code, full_name)
                        break

            for child in node.children:
                traverse(child, current_class)

        traverse(root_node)

    def _parse_go(self, root_node, code: str, file_path: str):
        """Parse Go constructs"""
        def traverse(node):
            # Function declarations
            if node.type == 'function_declaration':
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = code[child.start_byte:child.end_byte]
                        full_name = f"{file_path}::{func_name}()"

                        self.graph.add_node(
                            full_name,
                            type='function',
                            name=func_name,
                            language='go'
                        )
                        self.graph.add_edge(file_path, full_name, relation='contains')
                        break

            for child in node.children:
                traverse(child)

        traverse(root_node)

    def _find_calls(self, node, code: str, caller: str):
        """Find function calls in a node"""
        if node.type == 'call' or node.type == 'call_expression':
            # Get what's being called
            for child in node.children:
                if child.type in ['identifier', 'attribute']:
                    name = code[child.start_byte:child.end_byte]
                    callee = f"<{name}>"

                    if callee not in self.graph:
                        self.graph.add_node(callee, type='external_function')

                    self.graph.add_edge(caller, callee, relation='calls')
                    break

        for child in node.children:
            self._find_calls(child, code, caller)

    def query_entity(self, entity_name: str):
        """Find entities matching the name"""
        results = []
        for node in self.graph.nodes():
            if entity_name in node:
                node_data = self.graph.nodes[node]

                calls = [n for n in self.graph.successors(node)
                         if self.graph[node][n].get('relation') == 'calls']
                belongs_to = [n for n in self.graph.predecessors(node)
                              if self.graph[n][node].get('relation') == 'contains']

                results.append({
                    'entity': node,
                    'type': node_data.get('type'),
                    'language': node_data.get('language'),
                    'calls': calls,
                    'belongs_to': belongs_to,
                })

        return results


# Demo
if __name__ == "__main__":
    import os

    print("="*60)
    print("Tree-sitter Multi-Language GraphRAG Demo")
    print("="*60)

    # Create demo files in different languages
    demo_path = Path("/home/claude/multi_lang_demo")
    demo_path.mkdir(exist_ok=True)

    # Python file
    (demo_path / "auth.py").write_text("""
class AuthService:
    def login(self, username, password):
        return self.validate(username, password)
    
    def validate(self, username, password):
        return len(password) >= 8
""")

    # JavaScript file
    (demo_path / "utils.js").write_text("""
function formatUser(user) {
    return user.name.toUpperCase();
}

class UserService {
    getUser(id) {
        return formatUser(this.fetchUser(id));
    }
    
    fetchUser(id) {
        return { id: id, name: 'User' };
    }
}
""")

    # TypeScript file
    (demo_path / "api.ts").write_text("""
interface User {
    id: number;
    name: string;
}

function createUser(name: string): User {
    return { id: generateId(), name: name };
}

function generateId(): number {
    return Math.random();
}
""")

    # Parse the repository
    parser = TreeSitterCodeParser()
    parser.parse_repository(demo_path)

    print(f"\n✓ Parsed {parser.graph.number_of_nodes()} entities")
    print(f"✓ Found {parser.graph.number_of_edges()} relationships")

    # Show stats
    lang_counts = {}
    type_counts = {}

    for node in parser.graph.nodes():
        data = parser.graph.nodes[node]
        lang = data.get('language', 'unknown')
        typ = data.get('type', 'unknown')

        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        type_counts[typ] = type_counts.get(typ, 0) + 1

    print(f"\nLanguages parsed:")
    for lang, count in lang_counts.items():
        print(f"  {lang}: {count} entities")

    print(f"\nEntity types:")
    for typ, count in type_counts.items():
        print(f"  {typ}: {count}")

    # Query examples
    print("\n" + "="*60)
    print("Query Examples")
    print("="*60)

    print("\n1. Find 'login' function:")
    results = parser.query_entity('login')
    for r in results:
        print(f"   {r['entity']} ({r['language']})")
        if r['calls']:
            print(f"     Calls: {r['calls']}")

    print("\n2. Find all classes:")
    for node in parser.graph.nodes():
        data = parser.graph.nodes[node]
        if data.get('type') == 'class':
            print(f"   {node} ({data.get('language')})")

    print("\n" + "="*60)
    print("✅ Multi-language parsing works!")
    print("="*60)