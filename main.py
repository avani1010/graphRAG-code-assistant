"""
Main application - Parse GitHub repo and store in Neo4j
Simplified version with only 3 relationships: CONTAINS, CALLS, IMPORTS
"""

import sys
from pathlib import Path

from config.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, LANGUAGE_MAP, SKIP_DIRS
from utils.git_utils import clone_repo, get_code_files
from parser.tree_sitter_parser_univ import parse_file, extract_entities_and_relationships
from database.neo4j_db import Neo4jGraph


def should_skip_file(filename):
    """Check if file should be skipped"""
    # # Skip test files
    # if 'test.' in filename.lower() or 'spec.' in filename.lower():
    #     return True

    return False


def parse_repository_to_neo4j(repo_url, target_dir="./temp_repo", clear_db=True):
    """
    Clone a GitHub repository, parse it, and store in Neo4j

    Args:
        repo_url: GitHub repository URL
        target_dir: Local directory to clone into
        clear_db: Whether to clear database before inserting
    """

    print("="*60)
    print("GitHub Repository → Neo4j Graph Parser")
    print("Simplified: 3 Relationships (CONTAINS, CALLS, IMPORTS)")
    print("="*60)

    # Step 1: Clone repository
    print("\n[1/4] Cloning repository...")
    repo_path = clone_repo(repo_url, target_dir)

    # Step 2: Get all code files
    print("\n[2/4] Finding code files...")
    all_files = get_code_files(repo_path, LANGUAGE_MAP, SKIP_DIRS)

    # Filter out boilerplate files
    code_files = [(rel, lang, full) for rel, lang, full in all_files
                  if not should_skip_file(Path(rel).name)]

    print(f"✓ Found {len(code_files)} code files ({len(all_files) - len(code_files)} skipped)")

    # Step 3: Connect to Neo4j
    print("\n[3/4] Connecting to Neo4j...")
    db = Neo4jGraph(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

    if clear_db:
        db.clear_database()

    # Step 4: Parse and insert
    print("\n[4/4] Parsing files and inserting into Neo4j...")

    # Tracking stats
    stats = {
        'directories': 0,
        'files': 0,
        'classes': 0,
        'functions': 0,
        'methods': 0,
        'relationships': {
            'CONTAINS': 0,
            'CALLS': 0,
        }
    }

    for i, (relative_path, language, full_path) in enumerate(code_files, 1):
        try:
            print(f"  [{i}/{len(code_files)}] {relative_path} ({language})")

            # Parse file with simplified universal parser
            tree, code = parse_file(full_path, language)
            result = extract_entities_and_relationships(
                tree, code, relative_path, language, repo_root=str(repo_path)
            )

            # Insert all entities
            for entity_type, entities in result['entities'].items():
                for entity in entities:
                    db.create_entity(entity_type, entity)
                    stats[entity_type] += 1

            # Insert all relationships
            for rel_type, relationships in result['relationships'].items():
                for rel in relationships:
                    db.create_relationship(rel_type, rel)
                    stats['relationships'][rel_type] += 1

        except Exception as e:
            print(f"    ✗ Error: {e}")

    # Print results
    print("\n" + "="*60)
    print("✓ Parsing Complete!")
    print("="*60)

    print("\nEntities inserted:")
    for entity_type, count in stats.items():
        if entity_type != 'relationships' and count > 0:
            print(f"  - {entity_type}: {count}")

    print("\nRelationships inserted:")
    for rel_type, count in stats['relationships'].items():
        if count > 0:
            print(f"  - {rel_type}: {count}")

    # Get final Neo4j stats
    print("\n" + "="*60)
    print("Neo4j Database Stats:")
    print("="*60)
    db_stats = db.get_stats()

    for node_type, count in sorted(db_stats.items()):
        if node_type != 'relationships':
            print(f"  {node_type}: {count}")

    total_relationships = db_stats.get('relationships', 0)
    print(f"\n  Total relationships: {total_relationships}")

    db.close()
    print("\n✓ Done!")


if __name__ == "__main__":
    # Get repo URL from command line or use default
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
    else:
        # Default: Small example repo
        repo_url = "https://github.com/miguelgrinberg/react-flask-app"
        print(f"No repo specified, using default: {repo_url}")
        print("Usage: python main.py <github_repo_url>\n")

    parse_repository_to_neo4j(repo_url)