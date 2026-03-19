"""
Enhanced Neo4j Database Handler
Supports multi-repo entities and relationships
"""

from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class Neo4jGraph:
    """Neo4j graph database handler with multi-repo support"""

    def __init__(self, uri, user, password, database=None):
        """
        Initialize Neo4j connection

        Args:
            uri: Neo4j URI
            user: Username
            password: Password
            database: Database name (None for default)
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.database = database
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Database connection closed")

    def _get_session(self):
        """Get session with database if specified"""
        if self.database:
            return self.driver.session(database=self.database)
        return self.driver.session()

    def clear_database(self):
        """Clear all nodes and relationships"""
        with self._get_session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Database cleared")

    def create_entity(self, entity_type, entity_data):
        """
        Universal entity creator

        Args:
            entity_type: Type of entity (repositories, files, classes, methods, etc.)
            entity_data: Dictionary with entity properties
        """
        # Map entity_type to Neo4j label
        label_map = {
            'repositories': 'Repository',
            'files': 'File',
            'classes': 'Class',
            'interfaces': 'Interface',
            'methods': 'Method',
            'exceptions': 'Exception',
            'annotations': 'Annotation',
        }

        label = label_map.get(entity_type, entity_type.capitalize())

        with self._get_session() as session:
            # Build SET clause for all properties
            set_clauses = ', '.join([f"n.{key} = ${key}" for key in entity_data.keys()])

            # Use MERGE to avoid duplicates
            if 'path' in entity_data:
                # For files, use path as unique key
                query = f"""
                    MERGE (n:{label} {{path: $path}})
                    SET {set_clauses}
                """
            elif 'full_name' in entity_data:
                # For classes, methods - use full_name
                query = f"""
                    MERGE (n:{label} {{full_name: $full_name}})
                    SET {set_clauses}
                """
            elif 'name' in entity_data:
                # For repositories, exceptions, annotations - use name
                query = f"""
                    MERGE (n:{label} {{name: $name}})
                    SET {set_clauses}
                """
            else:
                # Fallback: just create
                query = f"""
                    CREATE (n:{label})
                    SET {set_clauses}
                """

            session.run(query, **entity_data)

    def create_relationship(self, rel_type, rel_data):
        """
        Universal relationship creator

        Args:
            rel_type: Type of relationship (CONTAINS, CALLS, etc.)
            rel_data: Dictionary with 'from', 'from_type', 'to', 'to_type'
        """
        with self._get_session() as session:
            # Map type names to Neo4j labels
            label_map = {
                'repository': 'Repository',
                'file': 'File',
                'class': 'Class',
                'interface': 'Interface',
                'method': 'Method',
                'exception': 'Exception',
                'annotation': 'Annotation',
            }

            from_label = label_map.get(rel_data['from_type'], rel_data['from_type'].capitalize())
            to_label = label_map.get(rel_data['to_type'], rel_data['to_type'].capitalize())

            from_match = self._get_match_clause(from_label, rel_data['from'])
            to_match = self._get_match_clause(to_label, rel_data['to'])

            # Special handling for CALLS - only link existing methods
            if rel_type == 'CALLS':
                query = f"""
                    MATCH (from:{from_label} {from_match})
                    MATCH (to:{to_label} {to_match})
                    MERGE (from)-[:{rel_type}]->(to)
                """
            else:
                # For other relationships, create target if missing
                query = f"""
                    MATCH (from:{from_label} {from_match})
                    MERGE (to:{to_label} {to_match})
                    MERGE (from)-[:{rel_type}]->(to)
                """

            try:
                session.run(query)
            except Exception as e:
                logger.warning(f"Failed to create {rel_type}: {rel_data['from']} -> {rel_data['to']}: {e}")

    def _get_match_clause(self, label, identifier):
        """Helper to generate MATCH clause"""
        identifier_escaped = identifier.replace("'", "\\'")

        if label in ['File']:
            return f"{{path: '{identifier_escaped}'}}"
        elif label in ['Repository', 'Exception', 'Annotation']:
            return f"{{name: '{identifier_escaped}'}}"
        elif label in ['Class', 'Interface', 'Method']:
            return f"{{full_name: '{identifier_escaped}'}}"
        else:
            return f"{{name: '{identifier_escaped}'}}"

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