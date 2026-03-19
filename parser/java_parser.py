from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from pathlib import Path


class JavaParser:

    def __init__(self):
        self.parser = Parser(get_language('java'))

    def parse_file(self, file_path, repo_name):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        tree = self.parser.parse(bytes(code, 'utf8'))

        result = {
            'entities': {
                'files': [],
                'classes': [],
                'methods': [],
                'interfaces': [],
                'exceptions': set(),
                'annotations': set()
            },
            'relationships': {
                'CONTAINS': [],
                'CALLS': [],
                'THROWS': [],
                'CATCHES': [],
                'INHERITS': [],
                'IMPLEMENTS': [],
                'ANNOTATES': []
            }
        }

        # Get package name
        package = self._extract_package(tree.root_node, code)

        # Add file entity
        relative_path = str(file_path)
        result['entities']['files'].append({
            'path': relative_path,
            'name': Path(file_path).name,
            'language': 'java',
            'package': package,
            'repository': repo_name
        })

        # Extract all class declarations
        class_nodes = self._find_all_nodes(tree.root_node, 'class_declaration')
        for class_node in class_nodes:
            self._extract_class(class_node, code, relative_path, package, repo_name, result)

        # Extract all interface declarations
        interface_nodes = self._find_all_nodes(tree.root_node, 'interface_declaration')
        for interface_node in interface_nodes:
            self._extract_interface(interface_node, code, relative_path, package, repo_name, result)

        return result

    def _extract_package(self, node, code):
        """Extract package declaration"""
        for child in node.children:
            if child.type == 'package_declaration':
                for pkg_child in child.children:
                    if pkg_child.type == 'scoped_identifier':
                        return code[pkg_child.start_byte:pkg_child.end_byte]
        return None

    def _extract_class(self, class_node, code, file_path, package, repo_name, result):
        """Extract class information"""
        class_info = {
            'name': None,
            'full_name': None,
            'file': file_path,
            'package': package,
            'repository': repo_name,
            'start_line': class_node.start_point[0] + 1,
            'end_line': class_node.end_point[0] + 1,
            'access_modifier': 'package-private',
            'is_abstract': False,
            'is_static': False,
            'annotations': [],
            'extends': None,
            'implements': [],
            'fields': []
        }

        # Extract class details
        for child in class_node.children:
            if child.type == 'identifier':
                class_info['name'] = code[child.start_byte:child.end_byte]
                if package:
                    class_info['full_name'] = f"{package}.{class_info['name']}"
                else:
                    class_info['full_name'] = class_info['name']

            elif child.type == 'modifiers':
                self._extract_modifiers(child, code, class_info)

            elif child.type == 'superclass':
                for sc_child in child.children:
                    if sc_child.type == 'type_identifier':
                        class_info['extends'] = code[sc_child.start_byte:sc_child.end_byte]

            elif child.type == 'super_interfaces':
                for si_child in child.children:
                    if si_child.type == 'type_identifier':
                        class_info['implements'].append(code[si_child.start_byte:si_child.end_byte])

            elif child.type == 'class_body':
                # Extract fields
                field_nodes = self._find_all_nodes(child, 'field_declaration')
                field_names = []
                for field_node in field_nodes:
                    field_info = self._extract_field(field_node, code)
                    if field_info and field_info.get('name'):
                        field_names.append(field_info['name'])
                class_info['fields'] = field_names

        result['entities']['classes'].append(class_info)

        # Add annotations to entities
        for ann in class_info['annotations']:
            result['entities']['annotations'].add(ann)

        # Create relationships
        # File CONTAINS Class
        result['relationships']['CONTAINS'].append({
            'from': file_path,
            'from_type': 'file',
            'to': class_info['full_name'],
            'to_type': 'class'
        })

        # Class INHERITS Parent
        if class_info['extends']:
            result['relationships']['INHERITS'].append({
                'from': class_info['full_name'],
                'from_type': 'class',
                'to': class_info['extends'],
                'to_type': 'class'
            })

        # Class IMPLEMENTS Interface
        for interface in class_info['implements']:
            result['relationships']['IMPLEMENTS'].append({
                'from': class_info['full_name'],
                'from_type': 'class',
                'to': interface,
                'to_type': 'interface'
            })

        # Class ANNOTATES (annotations on class)
        for ann in class_info['annotations']:
            result['relationships']['ANNOTATES'].append({
                'from': ann,
                'from_type': 'annotation',
                'to': class_info['full_name'],
                'to_type': 'class'
            })

        # Extract methods in this class
        method_nodes = self._find_all_nodes(class_node, 'method_declaration')
        for method_node in method_nodes:
            self._extract_method(method_node, code, class_info['full_name'], repo_name, result)

        # Extract constructors
        constructor_nodes = self._find_all_nodes(class_node, 'constructor_declaration')
        for constructor_node in constructor_nodes:
            self._extract_method(constructor_node, code, class_info['full_name'], repo_name, result, is_constructor=True)

    def _extract_interface(self, interface_node, code, file_path, package, repo_name, result):
        """Extract interface information"""
        interface_info = {
            'name': None,
            'full_name': None,
            'file': file_path,
            'package': package,
            'repository': repo_name,
            'start_line': interface_node.start_point[0] + 1,
            'end_line': interface_node.end_point[0] + 1
        }

        for child in interface_node.children:
            if child.type == 'identifier':
                interface_info['name'] = code[child.start_byte:child.end_byte]
                if package:
                    interface_info['full_name'] = f"{package}.{interface_info['name']}"
                else:
                    interface_info['full_name'] = interface_info['name']

        result['entities']['interfaces'].append(interface_info)

        # File CONTAINS Interface
        result['relationships']['CONTAINS'].append({
            'from': file_path,
            'from_type': 'file',
            'to': interface_info['full_name'],
            'to_type': 'interface'
        })

    def _extract_method(self, method_node, code, class_name, repo_name, result, is_constructor=False):
        """Extract method information"""
        method_info = {
            'name': None,
            'full_name': None,
            'class': class_name,
            'repository': repo_name,
            'start_line': method_node.start_point[0] + 1,
            'end_line': method_node.end_point[0] + 1,
            'access_modifier': 'package-private',
            'is_static': False,
            'is_abstract': False,
            'is_constructor': is_constructor,
            'return_type': None,
            'annotations': [],
            'throws': [],
            'catches': [],
            'calls': [],
            'code': code[method_node.start_byte:method_node.end_byte]
        }

        for child in method_node.children:
            if child.type == 'identifier':
                method_info['name'] = code[child.start_byte:child.end_byte]
                # Simple signature (can be enhanced to include parameters)
                method_info['full_name'] = f"{class_name}.{method_info['name']}"

            elif child.type == 'modifiers':
                self._extract_modifiers(child, code, method_info)

            elif child.type in ['type_identifier', 'void_type', 'integral_type', 'floating_point_type', 'boolean_type']:
                method_info['return_type'] = code[child.start_byte:child.end_byte]

            elif child.type == 'throws':
                for throws_child in child.children:
                    if throws_child.type == 'type_identifier':
                        exc = code[throws_child.start_byte:throws_child.end_byte]
                        method_info['throws'].append(exc)
                        result['entities']['exceptions'].add(exc)

            elif child.type == 'block':
                self._extract_from_block(child, code, method_info, result)

        result['entities']['methods'].append(method_info)

        # Class CONTAINS Method
        result['relationships']['CONTAINS'].append({
            'from': class_name,
            'from_type': 'class',
            'to': method_info['full_name'],
            'to_type': 'method'
        })

        # Method THROWS Exception
        for exc in method_info['throws']:
            result['relationships']['THROWS'].append({
                'from': method_info['full_name'],
                'from_type': 'method',
                'to': exc,
                'to_type': 'exception'
            })

        # Method CATCHES Exception
        for exc in method_info['catches']:
            result['relationships']['CATCHES'].append({
                'from': method_info['full_name'],
                'from_type': 'method',
                'to': exc,
                'to_type': 'exception'
            })
            result['entities']['exceptions'].add(exc)

        # Method CALLS Method
        for call in method_info['calls']:
            result['relationships']['CALLS'].append({
                'from': method_info['full_name'],
                'from_type': 'method',
                'to': call,
                'to_type': 'method'
            })

        # Annotation ANNOTATES Method
        for ann in method_info['annotations']:
            result['relationships']['ANNOTATES'].append({
                'from': ann,
                'from_type': 'annotation',
                'to': method_info['full_name'],
                'to_type': 'method'
            })
            result['entities']['annotations'].add(ann)

    def _extract_modifiers(self, modifiers_node, code, info_dict):
        """Extract modifiers (public, private, static, annotations, etc.)"""
        for mod in modifiers_node.children:
            mod_text = code[mod.start_byte:mod.end_byte]

            if mod.type in ['marker_annotation', 'annotation']:
                info_dict['annotations'].append(mod_text)
            elif mod_text == 'public':
                info_dict['access_modifier'] = 'public'
            elif mod_text == 'private':
                info_dict['access_modifier'] = 'private'
            elif mod_text == 'protected':
                info_dict['access_modifier'] = 'protected'
            elif mod_text == 'static':
                info_dict['is_static'] = True
            elif mod_text == 'abstract':
                info_dict['is_abstract'] = True

    def _extract_field(self, field_node, code):
        """Extract field/attribute information"""
        field_info = {
            'name': None,
            'type': None,
            'is_static': False,
            'is_final': False,
            'access_modifier': 'package-private'
        }

        for child in field_node.children:
            if child.type == 'modifiers':
                for mod in child.children:
                    mod_text = code[mod.start_byte:mod.end_byte]
                    if mod_text == 'static':
                        field_info['is_static'] = True
                    elif mod_text == 'final':
                        field_info['is_final'] = True
                    elif mod_text in ['public', 'private', 'protected']:
                        field_info['access_modifier'] = mod_text

            elif child.type == 'variable_declarator':
                for var_child in child.children:
                    if var_child.type == 'identifier':
                        field_info['name'] = code[var_child.start_byte:var_child.end_byte]

            elif child.type in ['type_identifier', 'integral_type', 'floating_point_type', 'boolean_type']:
                field_info['type'] = code[child.start_byte:child.end_byte]

        return field_info if field_info['name'] else None

    def _extract_from_block(self, block_node, code, method_info, result):
        """Extract catches and calls from method body"""
        def recurse(node):
            # Find try-catch blocks
            if node.type == 'try_statement':
                for child in node.children:
                    if child.type == 'catch_clause':
                        for catch_child in child.children:
                            if catch_child.type == 'catch_formal_parameter':
                                for param_child in catch_child.children:
                                    if param_child.type == 'catch_type':
                                        for type_child in param_child.children:
                                            if type_child.type == 'type_identifier':
                                                exc = code[type_child.start_byte:type_child.end_byte]
                                                if exc not in method_info['catches']:
                                                    method_info['catches'].append(exc)

            # Find method calls
            elif node.type == 'method_invocation':
                for child in node.children:
                    if child.type == 'identifier':
                        call = code[child.start_byte:child.end_byte]
                        # Filter out common built-ins
                        if call not in ['println', 'print', 'toString', 'equals', 'hashCode', 'size', 'get', 'set', 'add', 'remove']:
                            if call not in method_info['calls']:
                                method_info['calls'].append(call)
                        break

            # Recurse into children
            for child in node.children:
                recurse(child)

        recurse(block_node)

    def _find_all_nodes(self, node, node_type):
        """Recursively find all nodes of a specific type"""
        results = []

        if node.type == node_type:
            results.append(node)

        for child in node.children:
            results.extend(self._find_all_nodes(child, node_type))

        return results