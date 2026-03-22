from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PythonParser:
    def __init__(self):
        self.parser = Parser(get_language('python'))

    def parse_file(self, file_path, repo_name):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return self._empty_result()

        try:
            tree = self.parser.parse(bytes(code, 'utf8'))
        except Exception as e:
            logger.warning(f"Failed to parse AST for {file_path}: {e}")
            return self._empty_result()

        result = {
            'entities': {
                'modules': [],
                'classes': [],
                'functions': [],
                'methods': [],
                'decorators': set(),
                'imports': [],
                'exceptions': set()
            },
            'relationships': {
                'CONTAINS': [],
                'CALLS': [],
                'RAISES': [],
                'CATCHES': [],
                'INHERITS': [],
                'IMPLEMENTS': [],
                'DECORATES': [],
                'IMPORTS': [],
                'DEFINES_ROUTE': [],
                'USES_DEPENDENCY': []
            }
        }

        try:
            # Extract module info
            relative_path = str(file_path)
            module_info = self._extract_module(relative_path, repo_name)
            result['entities']['modules'].append(module_info)

            # Extract imports
            import_nodes = self._find_all_nodes(tree.root_node, 'import_statement')
            import_from_nodes = self._find_all_nodes(tree.root_node, 'import_from_statement')

            for import_node in import_nodes:
                self._extract_import(import_node, code, module_info['full_name'], result)

            for import_from_node in import_from_nodes:
                self._extract_import_from(import_from_node, code, module_info['full_name'], result)

            # Extract classes
            class_nodes = self._find_all_nodes(tree.root_node, 'class_definition')
            for class_node in class_nodes:
                self._extract_class(class_node, code, module_info['full_name'], repo_name, result)

            # Extract standalone functions (not in classes)
            function_nodes = self._find_all_nodes(tree.root_node, 'function_definition')
            # Filter out functions that are inside classes
            standalone_functions = [fn for fn in function_nodes if not self._is_inside_class(fn)]

            for func_node in standalone_functions:
                self._extract_function(func_node, code, module_info['full_name'], repo_name, result)

        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")

        return result

    def _empty_result(self):
        """Return empty result structure"""
        return {
            'entities': {
                'modules': [],
                'classes': [],
                'functions': [],
                'methods': [],
                'decorators': set(),
                'imports': [],
                'exceptions': set()
            },
            'relationships': {
                'CONTAINS': [],
                'CALLS': [],
                'RAISES': [],
                'CATCHES': [],
                'INHERITS': [],
                'IMPLEMENTS': [],
                'DECORATES': [],
                'IMPORTS': [],
                'DEFINES_ROUTE': [],
                'USES_DEPENDENCY': []
            }
        }

    def _extract_module(self, file_path, repo_name):
        """Extract module information from file path"""
        path_obj = Path(file_path)

        # Get module name from path
        # e.g., "repos/flask-app/api/routes/payment.py" -> "api.routes.payment"
        parts = path_obj.parts

        # Find where the actual package starts (skip repos/repo_name/)
        try:
            # Skip until we find src/ or the repo name
            start_idx = 0
            for i, part in enumerate(parts):
                if part in ['src', 'app', repo_name.replace('-', '_')]:
                    start_idx = i + 1
                    break

            module_parts = list(parts[start_idx:])
            # Remove .py extension from last part
            if module_parts:
                module_parts[-1] = module_parts[-1].replace('.py', '')

            package = '.'.join(module_parts[:-1]) if len(module_parts) > 1 else None
            module_name = module_parts[-1] if module_parts else path_obj.stem
            full_name = '.'.join(module_parts) if module_parts else path_obj.stem
        except:
            module_name = path_obj.stem
            package = None
            full_name = module_name

        return {
            'path': file_path,
            'name': module_name,
            'full_name': full_name,
            'package': package,
            'is_init': path_obj.name == '__init__.py',
            'repository': repo_name
        }

    def _extract_import(self, import_node, code, module_name, result):
        """Extract import statement: import X"""
        for child in import_node.children:
            if child.type == 'dotted_name':
                imported = code[child.start_byte:child.end_byte]
                import_info = {
                    'module': module_name,
                    'imported_name': imported,
                    'import_type': 'module',
                    'alias': None
                }
                result['entities']['imports'].append(import_info)

                # Create relationship
                result['relationships']['IMPORTS'].append({
                    'from': module_name,
                    'from_type': 'module',
                    'to': imported,
                    'to_type': 'module',
                    'import_type': 'module'
                })

            elif child.type == 'aliased_import':
                # import X as Y
                name_node = child.child_by_field_name('name')
                alias_node = child.child_by_field_name('alias')

                if name_node:
                    imported = code[name_node.start_byte:name_node.end_byte]
                    alias = code[alias_node.start_byte:alias_node.end_byte] if alias_node else None

                    import_info = {
                        'module': module_name,
                        'imported_name': imported,
                        'import_type': 'module',
                        'alias': alias
                    }
                    result['entities']['imports'].append(import_info)

                    result['relationships']['IMPORTS'].append({
                        'from': module_name,
                        'from_type': 'module',
                        'to': imported,
                        'to_type': 'module',
                        'import_type': 'module',
                        'alias': alias
                    })

    def _extract_import_from(self, import_from_node, code, module_name, result):
        """Extract from X import Y statements"""
        module_node = import_from_node.child_by_field_name('module_name')

        if not module_node:
            return

        from_module = code[module_node.start_byte:module_node.end_byte]

        # Find what's being imported
        for child in import_from_node.children:
            if child.type == 'dotted_name' and child != module_node:
                imported = code[child.start_byte:child.end_byte]

                import_info = {
                    'module': module_name,
                    'imported_name': f"{from_module}.{imported}",
                    'import_type': 'from_import',
                    'alias': None
                }
                result['entities']['imports'].append(import_info)

                result['relationships']['IMPORTS'].append({
                    'from': module_name,
                    'from_type': 'module',
                    'to': f"{from_module}.{imported}",
                    'to_type': 'symbol',
                    'import_type': 'from_import'
                })

            elif child.type == 'aliased_import':
                name_node = child.child_by_field_name('name')
                alias_node = child.child_by_field_name('alias')

                if name_node:
                    imported = code[name_node.start_byte:name_node.end_byte]
                    alias = code[alias_node.start_byte:alias_node.end_byte] if alias_node else None

                    import_info = {
                        'module': module_name,
                        'imported_name': f"{from_module}.{imported}",
                        'import_type': 'from_import',
                        'alias': alias
                    }
                    result['entities']['imports'].append(import_info)

                    result['relationships']['IMPORTS'].append({
                        'from': module_name,
                        'from_type': 'module',
                        'to': f"{from_module}.{imported}",
                        'to_type': 'symbol',
                        'import_type': 'from_import',
                        'alias': alias
                    })

    def _extract_class(self, class_node, code, module_name, repo_name, result):
        """Extract class definition"""
        class_info = {
            'name': None,
            'full_name': None,
            'module': module_name,
            'repository': repo_name,
            'base_classes': [],
            'decorators': [],
            'is_dataclass': False,
            'is_protocol': False,
            'is_abc': False,
            'docstring': None,
            'start_line': class_node.start_point[0] + 1,
            'end_line': class_node.end_point[0] + 1
        }

        # Get class name
        name_node = class_node.child_by_field_name('name')
        if name_node:
            class_info['name'] = code[name_node.start_byte:name_node.end_byte]
            class_info['full_name'] = f"{module_name}.{class_info['name']}"

        # Get decorators
        decorators = self._get_decorators(class_node, code)
        class_info['decorators'] = decorators

        # Check for special decorators
        for dec in decorators:
            if '@dataclass' in dec or '@dataclasses.dataclass' in dec:
                class_info['is_dataclass'] = True
            result['entities']['decorators'].add(dec)

        # Get base classes
        superclasses_node = class_node.child_by_field_name('superclasses')
        if superclasses_node:
            for child in superclasses_node.children:
                if child.type in ['identifier', 'attribute']:
                    base = code[child.start_byte:child.end_byte]
                    class_info['base_classes'].append(base)

                    # Check for special base classes
                    if 'Protocol' in base:
                        class_info['is_protocol'] = True
                    if 'ABC' in base:
                        class_info['is_abc'] = True

        # Get docstring
        body_node = class_node.child_by_field_name('body')
        if body_node:
            docstring = self._extract_docstring(body_node, code)
            class_info['docstring'] = docstring

        result['entities']['classes'].append(class_info)

        # Module CONTAINS Class
        result['relationships']['CONTAINS'].append({
            'from': module_name,
            'from_type': 'module',
            'to': class_info['full_name'],
            'to_type': 'class'
        })

        # Decorators DECORATE Class
        for dec in decorators:
            result['relationships']['DECORATES'].append({
                'from': dec,
                'from_type': 'decorator',
                'to': class_info['full_name'],
                'to_type': 'class'
            })

        # Class INHERITS base classes
        for base in class_info['base_classes']:
            result['relationships']['INHERITS'].append({
                'from': class_info['full_name'],
                'from_type': 'class',
                'to': base,
                'to_type': 'class'
            })

        # Extract methods inside this class
        if body_node:
            method_nodes = self._find_all_nodes(body_node, 'function_definition')
            for method_node in method_nodes:
                # Only direct children (not nested functions)
                if method_node.parent.parent == class_node:
                    self._extract_method(method_node, code, class_info['full_name'], repo_name, result)

    def _extract_function(self, func_node, code, module_name, repo_name, result):
        """Extract standalone function (not in a class)"""
        func_info = {
            'name': None,
            'full_name': None,
            'module': module_name,
            'repository': repo_name,
            'decorators': [],
            'is_async': False,
            'is_route': False,
            'route_path': None,
            'route_method': None,
            'params': [],
            'return_type': None,
            'code': code[func_node.start_byte:func_node.end_byte],
            'calls': [],
            'raises': [],
            'catches': [],
            'docstring': None,
            'start_line': func_node.start_point[0] + 1,
            'end_line': func_node.end_point[0] + 1
        }

        # Check if async
        if code[func_node.start_byte:func_node.start_byte+5] == 'async':
            func_info['is_async'] = True

        # Get function name
        name_node = func_node.child_by_field_name('name')
        if name_node:
            func_info['name'] = code[name_node.start_byte:name_node.end_byte]
            func_info['full_name'] = f"{module_name}.{func_info['name']}"

        # Get decorators
        decorators = self._get_decorators(func_node, code)
        func_info['decorators'] = decorators

        # Detect route decorators (FastAPI/Flask)
        for dec in decorators:
            if self._is_route_decorator(dec):
                func_info['is_route'] = True
                route_info = self._parse_route_decorator(dec)
                func_info['route_path'] = route_info.get('path')
                func_info['route_method'] = route_info.get('method')
            result['entities']['decorators'].add(dec)

        # Get parameters
        params_node = func_node.child_by_field_name('parameters')
        if params_node:
            func_info['params'] = self._extract_parameters(params_node, code)

        # Get return type
        return_type_node = func_node.child_by_field_name('return_type')
        if return_type_node:
            func_info['return_type'] = code[return_type_node.start_byte:return_type_node.end_byte].strip(': ')

        # Get body and extract calls, exceptions
        body_node = func_node.child_by_field_name('body')
        if body_node:
            func_info['docstring'] = self._extract_docstring(body_node, code)
            self._extract_from_body(body_node, code, func_info, result)

        result['entities']['functions'].append(func_info)

        # Module CONTAINS Function
        result['relationships']['CONTAINS'].append({
            'from': module_name,
            'from_type': 'module',
            'to': func_info['full_name'],
            'to_type': 'function'
        })

        # Decorators DECORATE Function
        for dec in decorators:
            result['relationships']['DECORATES'].append({
                'from': dec,
                'from_type': 'decorator',
                'to': func_info['full_name'],
                'to_type': 'function'
            })

        # If route, create DEFINES_ROUTE relationship
        if func_info['is_route'] and func_info['route_path']:
            result['relationships']['DEFINES_ROUTE'].append({
                'from': func_info['full_name'],
                'from_type': 'function',
                'to': f"{func_info['route_method']} {func_info['route_path']}",
                'to_type': 'endpoint',
                'method': func_info['route_method'],
                'path': func_info['route_path']
            })

        # Function CALLS other functions
        for call in func_info['calls']:
            result['relationships']['CALLS'].append({
                'from': func_info['full_name'],
                'from_type': 'function',
                'to': call,
                'to_type': 'function'
            })

        # Function RAISES exceptions
        for exc in func_info['raises']:
            result['relationships']['RAISES'].append({
                'from': func_info['full_name'],
                'from_type': 'function',
                'to': exc,
                'to_type': 'exception'
            })
            result['entities']['exceptions'].add(exc)

        # Function CATCHES exceptions
        for exc in func_info['catches']:
            result['relationships']['CATCHES'].append({
                'from': func_info['full_name'],
                'from_type': 'function',
                'to': exc,
                'to_type': 'exception'
            })
            result['entities']['exceptions'].add(exc)

    def _extract_method(self, method_node, code, class_name, repo_name, result):
        """Extract method inside a class"""
        method_info = {
            'name': None,
            'full_name': None,
            'class': class_name,
            'repository': repo_name,
            'decorators': [],
            'is_async': False,
            'is_static': False,
            'is_classmethod': False,
            'is_property': False,
            'is_abstract': False,
            'params': [],
            'return_type': None,
            'code': code[method_node.start_byte:method_node.end_byte],
            'calls': [],
            'raises': [],
            'catches': [],
            'docstring': None,
            'start_line': method_node.start_point[0] + 1,
            'end_line': method_node.end_point[0] + 1
        }

        # Check if async
        if code[method_node.start_byte:method_node.start_byte+5] == 'async':
            method_info['is_async'] = True

        # Get method name
        name_node = method_node.child_by_field_name('name')
        if name_node:
            method_info['name'] = code[name_node.start_byte:name_node.end_byte]
            method_info['full_name'] = f"{class_name}.{method_info['name']}"

        # Get decorators
        decorators = self._get_decorators(method_node, code)
        method_info['decorators'] = decorators

        # Check for special decorators
        for dec in decorators:
            if '@staticmethod' in dec:
                method_info['is_static'] = True
            elif '@classmethod' in dec:
                method_info['is_classmethod'] = True
            elif '@property' in dec:
                method_info['is_property'] = True
            elif '@abstractmethod' in dec or '@abc.abstractmethod' in dec:
                method_info['is_abstract'] = True
            result['entities']['decorators'].add(dec)

        # Get parameters
        params_node = method_node.child_by_field_name('parameters')
        if params_node:
            method_info['params'] = self._extract_parameters(params_node, code)

        # Get return type
        return_type_node = method_node.child_by_field_name('return_type')
        if return_type_node:
            method_info['return_type'] = code[return_type_node.start_byte:return_type_node.end_byte].strip(': ')

        # Get body
        body_node = method_node.child_by_field_name('body')
        if body_node:
            method_info['docstring'] = self._extract_docstring(body_node, code)
            self._extract_from_body(body_node, code, method_info, result)

        result['entities']['methods'].append(method_info)

        # Class CONTAINS Method
        result['relationships']['CONTAINS'].append({
            'from': class_name,
            'from_type': 'class',
            'to': method_info['full_name'],
            'to_type': 'method'
        })

        # Decorators DECORATE Method
        for dec in decorators:
            result['relationships']['DECORATES'].append({
                'from': dec,
                'from_type': 'decorator',
                'to': method_info['full_name'],
                'to_type': 'method'
            })

        # Method CALLS other methods/functions
        for call in method_info['calls']:
            result['relationships']['CALLS'].append({
                'from': method_info['full_name'],
                'from_type': 'method',
                'to': call,
                'to_type': 'method'
            })

        # Method RAISES exceptions
        for exc in method_info['raises']:
            result['relationships']['RAISES'].append({
                'from': method_info['full_name'],
                'from_type': 'method',
                'to': exc,
                'to_type': 'exception'
            })
            result['entities']['exceptions'].add(exc)

        # Method CATCHES exceptions
        for exc in method_info['catches']:
            result['relationships']['CATCHES'].append({
                'from': method_info['full_name'],
                'from_type': 'method',
                'to': exc,
                'to_type': 'exception'
            })
            result['entities']['exceptions'].add(exc)

    def _get_decorators(self, node, code):
        """Extract decorators from a function/class/method"""
        decorators = []

        # Look at siblings before this node
        if node.parent:
            for sibling in node.parent.children:
                if sibling.type == 'decorator':
                    dec_text = code[sibling.start_byte:sibling.end_byte]
                    decorators.append(dec_text)

        return decorators

    def _extract_parameters(self, params_node, code):
        """Extract function/method parameters"""
        parameters = []

        for child in params_node.children:
            if child.type == 'identifier':
                param_name = code[child.start_byte:child.end_byte]
                if param_name not in ['self', 'cls']:  # Skip self/cls
                    parameters.append(param_name)
            elif child.type == 'typed_parameter':
                # param: Type
                name_node = child.child_by_field_name('name')
                if not name_node and child.children:
                    name_node = child.children[0]

                if name_node:
                    param_name = code[name_node.start_byte:name_node.end_byte]
                    if param_name not in ['self', 'cls']:
                        parameters.append(param_name)
            elif child.type == 'default_parameter':
                # param = default
                name_node = child.child_by_field_name('name')
                if not name_node and child.children:
                    name_node = child.children[0]

                if name_node:
                    param_name = code[name_node.start_byte:name_node.end_byte]
                    if param_name not in ['self', 'cls']:
                        parameters.append(param_name)

        return parameters

    def _extract_docstring(self, body_node, code):
        """Extract docstring from function/class body"""
        if body_node and body_node.children:
            first_statement = body_node.children[0]
            if first_statement.type == 'expression_statement':
                string_node = first_statement.children[0]
                if string_node.type == 'string':
                    docstring = code[string_node.start_byte:string_node.end_byte]
                    # Remove quotes
                    docstring = docstring.strip('"""').strip("'''").strip('"').strip("'")
                    return docstring
        return None

    def _extract_from_body(self, body_node, code, func_info, result):
        """Extract calls, raises, catches from function/method body"""

        def recurse(node):
            # Find raise statements
            if node.type == 'raise_statement':
                for child in node.children:
                    if child.type in ['identifier', 'call']:
                        exc = code[child.start_byte:child.end_byte]
                        # Extract just the exception name (before parentheses)
                        if '(' in exc:
                            exc = exc.split('(')[0]
                        if exc not in func_info['raises']:
                            func_info['raises'].append(exc)

            # Find try-except blocks
            elif node.type == 'try_statement':
                for child in node.children:
                    if child.type == 'except_clause':
                        # Get exception type
                        for exc_child in child.children:
                            if exc_child.type in ['identifier', 'attribute']:
                                exc = code[exc_child.start_byte:exc_child.end_byte]
                                if exc not in func_info['catches']:
                                    func_info['catches'].append(exc)
                                break

            # Find function calls
            elif node.type == 'call':
                func_node = node.child_by_field_name('function')
                if func_node:
                    call_name = code[func_node.start_byte:func_node.end_byte]
                    # Filter out built-ins and common methods
                    if not self._is_builtin(call_name):
                        if call_name not in func_info['calls']:
                            func_info['calls'].append(call_name)

            # Recurse into children
            for child in node.children:
                recurse(child)

        recurse(body_node)

    def _is_route_decorator(self, decorator):
        """Check if decorator is a route decorator (FastAPI/Flask)"""
        route_patterns = [
            '@app.route', '@app.get', '@app.post', '@app.put', '@app.delete', '@app.patch',
            '@router.route', '@router.get', '@router.post', '@router.put', '@router.delete',
            '@route', '@get', '@post', '@put', '@delete'
        ]
        return any(pattern in decorator for pattern in route_patterns)

    def _parse_route_decorator(self, decorator):
        """Parse route decorator to extract path and method"""
        # Simple parsing - can be enhanced
        route_info = {'path': None, 'method': None}

        # Extract method from decorator name
        if '.get(' in decorator or '@get(' in decorator:
            route_info['method'] = 'GET'
        elif '.post(' in decorator or '@post(' in decorator:
            route_info['method'] = 'POST'
        elif '.put(' in decorator or '@put(' in decorator:
            route_info['method'] = 'PUT'
        elif '.delete(' in decorator or '@delete(' in decorator:
            route_info['method'] = 'DELETE'
        elif '.patch(' in decorator or '@patch(' in decorator:
            route_info['method'] = 'PATCH'
        elif '.route(' in decorator:
            # Try to find method parameter
            if 'methods=' in decorator:
                route_info['method'] = 'ROUTE'  # Generic
            else:
                route_info['method'] = 'GET'  # Default

        # Extract path (first string in parentheses)
        if '("' in decorator or "('" in decorator:
            start = decorator.find('(') + 1
            end = decorator.find(')', start)
            if end > start:
                path_part = decorator[start:end].strip()
                # Extract first quoted string
                if path_part.startswith('"') or path_part.startswith("'"):
                    quote = path_part[0]
                    end_quote = path_part.find(quote, 1)
                    if end_quote > 0:
                        route_info['path'] = path_part[1:end_quote]

        return route_info

    def _is_builtin(self, name):
        """Check if name is a Python builtin or common method"""
        builtins = {
            'print', 'len', 'range', 'enumerate', 'zip', 'map', 'filter',
            'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
            'open', 'close', 'read', 'write', 'append', 'get', 'set',
            'items', 'keys', 'values', 'pop', 'update', 'clear'
        }
        return name in builtins or name.startswith('__')

    def _is_inside_class(self, func_node):
        """Check if function node is inside a class definition"""
        parent = func_node.parent
        while parent:
            if parent.type == 'class_definition':
                return True
            parent = parent.parent
        return False

    def _find_all_nodes(self, node, node_type):
        """Recursively find all nodes of a specific type"""
        results = []

        if node.type == node_type:
            results.append(node)

        for child in node.children:
            results.extend(self._find_all_nodes(child, node_type))

        return results