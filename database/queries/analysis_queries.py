from typing import List, Dict, Any, Optional

class AnalysisQueries:
    """General codebase analysis queries"""

    def __init__(self, db):
        """
        Initialize with Neo4j database connection

        Args:
            db: Neo4jGraph instance
        """
        self.db = db

    def get_most_called_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find most frequently called functions (most critical)

        Args:
            limit: Maximum number of functions to return

        Returns:
            List of dicts with: name, file, times_called
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:Function)
                MATCH ()-[:CALLS]->(f)
                WITH f, count(*) as times_called
                RETURN f.name as name,
                       f.file as file,
                       f.start_line as line,
                       times_called
                ORDER BY times_called DESC
                LIMIT $limit
            """, limit=limit)

            return [dict(record) for record in result]

    def get_file_dependencies(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Show what files this file depends on

        Args:
            file_path: Path to the file

        Returns:
            List of dicts with: dependency_file, call_count
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (source_file:File {path: $path})-[:CONTAINS]->(f:Function)
                MATCH (f)-[:CALLS]->(called:Function)
                MATCH (target_file:File)-[:CONTAINS]->(called)
                WHERE target_file.path <> source_file.path
                WITH target_file.path as dependency_file, count(*) as call_count
                RETURN dependency_file, call_count
                ORDER BY call_count DESC
            """, path=file_path)

            return [dict(record) for record in result]

    def get_complexity_hotspots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find files with most connections (high complexity)

        Args:
            limit: Maximum number of files to return

        Returns:
            List of dicts with: file, entities, outgoing, incoming, hotspot_score
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (file:File)
                OPTIONAL MATCH (file)-[:CONTAINS]->(entity)
                WITH file, count(DISTINCT entity) as entity_count
                
                OPTIONAL MATCH (file)-[:CONTAINS]->(f1:Function)-[:CALLS]->(f2:Function)
                MATCH (other_file:File)-[:CONTAINS]->(f2)
                WHERE other_file.path <> file.path
                WITH file, entity_count, count(DISTINCT other_file) as outgoing_files
                
                OPTIONAL MATCH (other_file2:File)-[:CONTAINS]->(f3:Function)-[:CALLS]->(f4:Function)
                MATCH (file)-[:CONTAINS]->(f4)
                WHERE other_file2.path <> file.path
                WITH file, entity_count, outgoing_files, count(DISTINCT other_file2) as incoming_files
                
                WITH file, entity_count, outgoing_files, incoming_files,
                     (entity_count + outgoing_files + incoming_files) as hotspot_score
                WHERE hotspot_score > 0
                RETURN file.path as file,
                       entity_count as entities,
                       outgoing_files as outgoing,
                       incoming_files as incoming,
                       hotspot_score
                ORDER BY hotspot_score DESC
                LIMIT $limit
            """, limit=limit)

            return [dict(record) for record in result]

    def get_complexity_distribution(self) -> Dict[str, Any]:
        """
        Get overview of codebase complexity distribution

        Returns:
            Dict with: simple, medium, complex, very_complex counts and average
        """
        with self.db._get_session() as session:
            result = session.run("""
                MATCH (f:Function)
                OPTIONAL MATCH (f)-[:CALLS]->()
                WITH f, 
                     count(*) as num_calls,
                     COALESCE(f.end_line - f.start_line, 0) as lines,
                     (count(*) + toFloat(COALESCE(f.end_line - f.start_line, 0)) / 10.0) as complexity
                
                RETURN 
                    count(CASE WHEN complexity < 10 THEN 1 END) as simple,
                    count(CASE WHEN complexity >= 10 AND complexity < 30 THEN 1 END) as medium,
                    count(CASE WHEN complexity >= 30 AND complexity < 50 THEN 1 END) as complex,
                    count(CASE WHEN complexity >= 50 THEN 1 END) as very_complex,
                    avg(complexity) as average_complexity,
                    count(f) as total_functions
            """)

            record = result.single()
            return dict(record) if record else {}

    def get_codebase_stats(self) -> Dict[str, Any]:
        """
        Get overall codebase statistics

        Returns:
            Dict with counts of files, classes, functions, methods, etc.
        """
        with self.db._get_session() as session:
            result = session.run("""
                RETURN 
                    count{(f:File)} as files,
                    count{(d:Directory)} as directories,
                    count{(c:Class)} as classes,
                    count{(f:Function)} as functions,
                    count{(m:Method)} as methods,
                    count{()-[:CALLS]->()} as call_relationships,
                    count{()-[:CONTAINS]->()} as contains_relationships
            """)

            record = result.single()
            return dict(record) if record else {}