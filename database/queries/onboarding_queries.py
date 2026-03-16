"""
Query Module
High-level queries for codebase analysis
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class OnboardingQueries:
    """Queries to help onboard new developers"""

    def __init__(self, db):
        """
        Initialize with Neo4j database connection

        Args:
            db: Neo4jGraph instance
        """
        self.db = db

    def get_entry_points(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find good starting points for new developers
        Returns functions that are called by many but don't call many others

        Args:
            limit: Maximum number of entry points to return

        Returns:
            List of dicts with: name, file, line, called_by, calls_out
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:Function)
                OPTIONAL MATCH (f)-[:CALLS]->(outgoing)
                OPTIONAL MATCH (incoming)-[:CALLS]->(f)
                WITH f, 
                     count(DISTINCT outgoing) as calls_out, 
                     count(DISTINCT incoming) as called_by
                WHERE calls_out <= 3 AND called_by >= 2
                RETURN f.full_name as name, 
                       f.file as file, 
                       f.start_line as line,
                       calls_out,
                       called_by
                ORDER BY called_by DESC
                LIMIT $limit
            """, limit=limit)

            return [dict(record) for record in result]

    def get_learning_path(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Generate learning path: simple functions first, complex later
        Complexity = number of function calls + (lines / 10)

        Args:
            limit: Maximum number of functions in path

        Returns:
            List of dicts with: name, file, line, complexity_score
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:Function)
                OPTIONAL MATCH (f)-[:CALLS]->()
                WITH f, 
                     count(*) as num_calls,
                     COALESCE(f.end_line - f.start_line, 0) as lines
                WITH f, 
                     (num_calls + toFloat(lines) / 10.0) as complexity
                RETURN f.name as name,
                       f.file as file,
                       f.start_line as line,
                       toInteger(complexity) as complexity_score
                ORDER BY complexity
                LIMIT $limit
            """, limit=limit)

            return [dict(record) for record in result]

    def get_file_summary(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get summary of what's in a specific file

        Args:
            file_path: Path to the file

        Returns:
            List of dicts with: type, name, line
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:File {path: $path})-[:CONTAINS]->(entity)
                RETURN labels(entity)[0] as type,
                       entity.name as name,
                       COALESCE(entity.start_line, 0) as line
                ORDER BY line
            """, path=file_path)

            return [dict(record) for record in result]

    def get_function_context(self, function_name: str) -> Dict[str, Any]:
        """
        Get full context for a function: what calls it, what it calls

        Args:
            function_name: Name of the function

        Returns:
            Dict with: function, callers, callees
        """
        with self.db._get_session() as session:
            # Get function details
            func_result = session.run("""
                MATCH (f:Function)
                WHERE f.name = $name OR f.name = $name
                RETURN f.name as name,
                       f.file as file,
                       f.start_line as start_line,
                       f.end_line as end_line
                LIMIT 1
            """, name=function_name)

            func_record = func_result.single()
            if not func_record:
                return {'error': f'Function {function_name} not found'}

            function_data = dict(func_record)

            # Get callers
            callers_result = session.run("""
                MATCH (f:Function)
                WHERE f.name = $name OR f.name = $name
                MATCH (caller)-[:CALLS]->(f)
                RETURN caller.name as name,
                       caller.file as file
            """, name=function_name)

            callers = [dict(record) for record in callers_result]

            # Get callees
            callees_result = session.run("""
                MATCH (f:Function)
                WHERE f.name = $name OR f.name = $name
                MATCH (f)-[:CALLS]->(callee)
                RETURN callee.name as name,
                       COALESCE(callee.file, 'external') as file
            """, name=function_name)

            callees = [dict(record) for record in callees_result]

            return {
                'function': function_data,
                'callers': callers,
                'callees': callees
            }

    def find_similar_functions(self, function_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find functions similar to the given one
        Similar = similar number of calls and lines

        Args:
            function_name: Name of the function to compare
            limit: Maximum number of similar functions

        Returns:
            List of dicts with: name, file, similarity_score
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (target:Function)
                WHERE target.name = $name OR target.name = $name
                WITH target
                MATCH (target)-[:CALLS]->()
                WITH target, count(*) as target_calls
                
                MATCH (other:Function)
                WHERE other.name <> target.name
                OPTIONAL MATCH (other)-[:CALLS]->()
                WITH target, target_calls, other, count(*) as other_calls,
                     COALESCE(target.end_line - target.start_line, 0) as target_lines,
                     COALESCE(other.end_line - other.start_line, 0) as other_lines
                
                WITH other,
                     abs(target_calls - other_calls) + abs(target_lines - other_lines) as diff
                
                RETURN other.name as name,
                       other.file as file,
                       other.start_line as line,
                       100 - diff as similarity_score
                ORDER BY similarity_score DESC
                LIMIT $limit
            """, name=function_name, limit=limit)

            return [dict(record) for record in result]


