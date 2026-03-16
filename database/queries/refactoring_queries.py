from typing import List, Dict, Any, Optional

class RefactoringQueries:
    """Queries to help with code refactoring"""

    def __init__(self, db):
        """
        Initialize with Neo4j database connection

        Args:
            db: Neo4jGraph instance
        """
        self.db = db

    def get_blast_radius(self, function_name: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Find what breaks if this function changes
        Shows all functions that depend on it (directly or indirectly)

        Args:
            function_name: Name of the function to analyze
            max_depth: Maximum depth to traverse

        Returns:
            List of dicts with: affected_function, affected_file, depth
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (target:Function)
                WHERE target.name = $name OR target.full_name = $name
                MATCH path = (caller)-[:CALLS*1..$depth]->(target)
                WHERE caller:Function OR caller:Method
                RETURN DISTINCT caller.name as affected_function,
                       caller.file as affected_file,
                       length(path) as depth
                ORDER BY depth, affected_file
            """, name=function_name, depth=max_depth)

            return [dict(record) for record in result]

    def find_dead_code(self) -> List[Dict[str, Any]]:
        """
        Find functions that are never called (potential dead code)

        Returns:
            List of dicts with: name, file, line
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:Function)
                WHERE NOT ()-[:CALLS]->(f)
                  AND NOT f.name IN ['main', '__init__', '__main__', 'init', 'setup']
                RETURN f.name as name,
                       f.file as file,
                       f.start_line as line
                ORDER BY f.file, f.start_line
            """)

            return [dict(record) for record in result]

    def find_circular_dependencies(self, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Find circular call chains (A calls B, B calls C, C calls A)

        Args:
            max_depth: Maximum cycle length to search for

        Returns:
            List of dicts with: cycle (list of function names), length
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH path = (f:Function)-[:CALLS*1..$depth]->(f)
                WHERE length(path) > 1
                WITH path, [n in nodes(path) | n.name] as cycle
                RETURN DISTINCT cycle,
                       length(path) as length
                ORDER BY length
                LIMIT 20
            """, depth=max_depth)

            return [dict(record) for record in result]

    def find_god_functions(self, min_calls: int = 10, min_lines: int = 100) -> List[Dict[str, Any]]:
        """
        Find overly complex functions that need refactoring

        Args:
            min_calls: Minimum number of function calls
            min_lines: Minimum number of lines

        Returns:
            List of dicts with: name, file, lines, calls, complexity_score
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:Function)
                OPTIONAL MATCH (f)-[:CALLS]->()
                WITH f, 
                     count(*) as num_calls,
                     COALESCE(f.end_line - f.start_line, 0) as lines
                WHERE num_calls >= $min_calls OR lines >= $min_lines
                WITH f, num_calls, lines,
                     (num_calls + toFloat(lines) / 10.0) as complexity
                RETURN f.name as name,
                       f.file as file,
                       f.start_line as line,
                       lines,
                       num_calls as calls,
                       toInteger(complexity) as complexity_score
                ORDER BY complexity DESC
            """, min_calls=min_calls, min_lines=min_lines)

            return [dict(record) for record in result]

    def find_isolated_modules(self, max_incoming: int = 2, max_outgoing: int = 3) -> List[Dict[str, Any]]:
        """
        Find functions with few dependencies - safe refactoring targets

        Args:
            max_incoming: Maximum incoming calls
            max_outgoing: Maximum outgoing calls

        Returns:
            List of dicts with: name, file, lines, incoming, outgoing
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:Function)
                OPTIONAL MATCH (f)-[:CALLS]->(outgoing)
                OPTIONAL MATCH (incoming)-[:CALLS]->(f)
                WITH f,
                     count(DISTINCT incoming) as incoming_count,
                     count(DISTINCT outgoing) as outgoing_count,
                     COALESCE(f.end_line - f.start_line, 0) as lines
                WHERE incoming_count <= $max_incoming
                  AND outgoing_count <= $max_outgoing
                  AND lines >= 50
                RETURN f.name as name,
                       f.file as file,
                       f.start_line as line,
                       lines,
                       incoming_count as incoming,
                       outgoing_count as outgoing
                ORDER BY lines DESC
            """, max_incoming=max_incoming, max_outgoing=max_outgoing)

            return [dict(record) for record in result]