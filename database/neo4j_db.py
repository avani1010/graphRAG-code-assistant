from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class Neo4jGraph:
    """Neo4j graph database handler"""

    def __init__(self, uri, user, password, database=None):
        """
        Initialize Neo4j connection

        Args:
            uri: Neo4j URI (e.g., neo4j+s://xxx.databases.neo4j.io)
            user: Username (usually 'neo4j')
            password: Password
            database: Database name (None for default)
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.database = database

            # Test connection
            self.driver.verify_connectivity()
            logger.info(f"✓ Connected to Neo4j at {uri}")

        except Exception as e:
            logger.error(f"✗ Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("✓ Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto cleanup"""
        self.close()

    def _get_session(self):
        """Get session with database if specified"""
        if self.database:
            return self.driver.session(database=self.database)
        return self.driver.session()

    def clear_database(self):
        """Clear all nodes and relationships (use carefully!)"""
        with self._get_session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("✓ Database cleared")

    def create_entity(self, entity_type, entity_data):
        """
        Universal entity creator - handles all entity types

        Args:
            entity_type: Type of entity (directories, files, classes, functions, etc.)
            entity_data: Dictionary with entity properties
        """
        # Map entity_type to Neo4j label (singular, capitalized)
        label_map = {
            'directories': 'Directory',
            'files': 'File',
            'classes': 'Class',
            'functions': 'Function',
            'methods': 'Method',
        }

        label = label_map.get(entity_type, entity_type.capitalize())

        with self._get_session() as session:
            # Build SET clause for all properties
            set_clauses = ', '.join([f"n.{key} = ${key}" for key in entity_data.keys()])

            # Use MERGE to avoid duplicates (based on unique identifier)
            if 'path' in entity_data:
                # For files and directories, use path as unique key
                query = f"""
                    MERGE (n:{label} {{path: $path}})
                    SET {set_clauses}
                """
            elif 'full_name' in entity_data:
                # For classes, functions, methods - use full_name
                query = f"""
                    MERGE (n:{label} {{full_name: $full_name}})
                    SET {set_clauses}
                """
            elif 'name' in entity_data:
                # For modules, variables, constants - use name
                query = f"""
                    MERGE (n:{label} {{name: $name}})
                    SET {set_clauses}
                """
            else:
                # Fallback: just create without merge
                query = f"""
                    CREATE (n:{label})
                    SET {set_clauses}
                """

            session.run(query, **entity_data)

    def create_relationship(self, rel_type, rel_data):
        """
        Universal relationship creator - handles all relationship types

        Args:
            rel_type: Type of relationship (CONTAINS, DECLARES, CALLS, etc.)
            rel_data: Dictionary with 'from', 'from_type', 'to', 'to_type'
        """
        with self._get_session() as session:
            # Map type names to Neo4j labels
            label_map = {
                'file': 'File',
                'directory': 'Directory',
                'class': 'Class',
                'function': 'Function',
                'method': 'Method',
                'struct': 'Class',  # Treat structs as classes
            }

            from_label = label_map.get(rel_data['from_type'], rel_data['from_type'].capitalize())
            to_label = label_map.get(rel_data['to_type'], rel_data['to_type'].capitalize())

            from_identifier = rel_data['from']
            to_identifier = rel_data['to']

            # Determine match criteria based on what we're linking
            # Files and directories match on path
            # Classes, functions, methods match on full_name
            # Modules, variables match on name

            from_match = self._get_match_clause(from_label, from_identifier)
            to_match = self._get_match_clause(to_label, to_identifier)

            query = f"""
                MATCH {from_match}
                MERGE {to_match}
                MERGE (from)-[:{rel_type}]->(to)
            """

            try:
                session.run(query)
            except Exception as e:
                # Log but don't fail on relationship creation errors
                logger.warning(f"Failed to create {rel_type} relationship from {from_identifier} to {to_identifier}: {e}")

    def _get_match_clause(self, label, identifier):
        """
        Get the appropriate MATCH clause based on label type

        Args:
            label: Neo4j label
            identifier: The identifier value

        Returns:
            MATCH clause string
        """
        # Files and directories use 'path'
        if label in ['File', 'Directory']:
            return f"(from:{label} {{path: '{identifier}'}})" if label == label else f"(to:{label} {{path: '{identifier}'}})"

        # Classes, Functions, Methods use 'full_name'
        elif label in ['Class', 'Interface', 'Function', 'Method']:
            identifier_escaped = identifier.replace("'", "\\'")
            return f"(from:{label} {{full_name: '{identifier_escaped}'}})" if 'from' in str(label) else f"(to:{label} {{full_name: '{identifier_escaped}'}})"

        # Everything else uses 'name'
        else:
            identifier_escaped = identifier.replace("'", "\\'")
            return f"(from:{label} {{name: '{identifier_escaped}'}})" if 'from' in str(label) else f"(to:{label} {{name: '{identifier_escaped}'}})"

    def _get_match_clause(self, label, identifier):
        """Helper to generate MATCH clause - fixed version"""
        identifier_escaped = identifier.replace("'", "\\'")

        if label in ['File', 'Directory']:
            return f"{{path: '{identifier_escaped}'}}"
        elif label in ['Class', 'Interface', 'Function', 'Method']:
            return f"{{full_name: '{identifier_escaped}'}}"
        else:
            return f"{{name: '{identifier_escaped}'}}"

    def create_relationship(self, rel_type, rel_data):
        """
        Universal relationship creator - handles all relationship types (FIXED)

        Args:
            rel_type: Type of relationship (CONTAINS, DECLARES, CALLS, etc.)
            rel_data: Dictionary with 'from', 'from_type', 'to', 'to_type'
        """
        with self._get_session() as session:
            # Map type names to Neo4j labels
            label_map = {
                'file': 'File',
                'directory': 'Directory',
                'module': 'Module',
                'class': 'Class',
                'interface': 'Interface',
                'function': 'Function',
                'method': 'Method',
                'variable': 'Variable',
                'constant': 'Constant',
                'struct': 'Class',
                'exported_entity': 'ExportedEntity',
                'decorator': 'Decorator',
            }

            from_label = label_map.get(rel_data['from_type'], rel_data['from_type'].capitalize())
            to_label = label_map.get(rel_data['to_type'], rel_data['to_type'].capitalize())

            from_match = self._get_match_clause(from_label, rel_data['from'])
            to_match = self._get_match_clause(to_label, rel_data['to'])

            query = f"""
                MATCH (from:{from_label} {from_match})
                MERGE (to:{to_label} {to_match})
                MERGE (from)-[:{rel_type}]->(to)
            """

            try:
                session.run(query)
            except Exception as e:
                logger.warning(f"Failed to create {rel_type}: {rel_data['from']} -> {rel_data['to']}: {e}")

    def get_stats(self):
        """Get database statistics"""
        with self._get_session() as session:
            # Get node counts by label
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as type, count(*) as count
            """)

            stats = {}
            for record in result:
                stats[record['type']] = record['count']

            # Get relationship count
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            stats['relationships'] = rel_result.single()['count']

            return stats

    # ========== LEGACY METHODS (for backwards compatibility) ==========

    def create_file_node(self, file_path, language):
        """Legacy method - redirects to create_entity"""
        self.create_entity('files', {
            'path': file_path,
            'language': language,
            'type': 'file'
        })

    def create_class_node(self, class_data):
        """Legacy method - redirects to create_entity"""
        self.create_entity('classes', class_data)

        # Create DECLARES relationship (File -> Class)
        if 'file' in class_data and 'full_name' in class_data:
            self.create_relationship('DECLARES', {
                'from': class_data['file'],
                'from_type': 'file',
                'to': class_data['full_name'],
                'to_type': 'class'
            })

    def create_function_node(self, func_data):
        """Legacy method - redirects to create_entity"""
        self.create_entity('functions', func_data)

        # Create DECLARES relationship
        if 'parent' in func_data and 'full_name' in func_data:
            self.create_relationship('DECLARES', {
                'from': func_data['parent'],
                'from_type': func_data.get('parent_type', 'file'),
                'to': func_data['full_name'],
                'to_type': 'function'
            })

    def create_call_relationship(self, caller_full_name, callee_name):
        """Legacy method - redirects to create_relationship"""
        self.create_relationship('CALLS', {
            'from': caller_full_name,
            'from_type': 'function',
            'to': callee_name,
            'to_type': 'function'
        })