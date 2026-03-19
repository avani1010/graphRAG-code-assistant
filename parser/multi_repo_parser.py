import os
import subprocess
from pathlib import Path
import fnmatch
import logging
from parser.java_parser import JavaParser
from database.neo4j_db import Neo4jGraph
from config.config import (
    REPOSITORIES,
    CLONE_DIR,
    SKIP_PATTERNS,
    JAVA_EXTENSIONS,
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiRepoParser:
    """
    Parse multiple repositories and store in Neo4j
    """

    def __init__(self):
        self.clone_dir = Path(CLONE_DIR)
        self.clone_dir.mkdir(exist_ok=True)

        self.java_parser = JavaParser()
        self.db = Neo4jGraph(
            NEO4J_URI,
            NEO4J_USERNAME,
            NEO4J_PASSWORD,
            None
        )

    def parse_all_repos(self, clear_db=False):
        """
        Parse all repositories defined in config

        Args:
            clear_db: If True, clear database before parsing
        """
        if clear_db:
            logger.info("Clearing database...")
            self.db.clear_database()

        for repo_config in REPOSITORIES:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {repo_config['name']}")
            logger.info(f"{'='*60}")

            try:
                self.parse_repo(repo_config)
            except Exception as e:
                logger.error(f"Failed to parse {repo_config['name']}: {e}")
                continue

        logger.info("\n" + "="*60)
        logger.info("✓ All repositories parsed!")
        logger.info("="*60)

        # Show stats
        stats = self.db.get_stats()
        logger.info(f"\nDatabase Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

    def parse_repo(self, repo_config):
        """
        Parse a single repository

        Args:
            repo_config: Dict with repo configuration
        """
        repo_name = repo_config['name']
        repo_url = repo_config['url']

        # Clone or update repo
        repo_path = self.clone_dir / repo_name

        if repo_path.exists():
            logger.info(f"Repository already cloned: {repo_path}")
            logger.info("Pulling latest changes...")
            self._git_pull(repo_path)
        else:
            logger.info(f"Cloning repository: {repo_url}")
            self._git_clone(repo_url, repo_path)

        # Create Repository entity in Neo4j
        self._create_repository_entity(repo_config, repo_path)

        # Find all Java files
        java_files = self._find_java_files(repo_path)
        logger.info(f"Found {len(java_files)} Java files")

        # Parse each Java file
        for i, java_file in enumerate(java_files, 1):
            if i % 10 == 0:
                logger.info(f"  Parsed {i}/{len(java_files)} files...")

            try:
                self._parse_and_store_file(java_file, repo_name, repo_path)
            except Exception as e:
                logger.warning(f"Failed to parse {java_file}: {e}")
                continue

        logger.info(f"✓ Completed parsing {repo_name}")

    def _git_clone(self, repo_url, target_path):
        """Clone a git repository"""
        subprocess.run(
            ['git', 'clone', repo_url, str(target_path)],
            check=True,
            capture_output=True
        )

    def _git_pull(self, repo_path):
        """Pull latest changes"""
        subprocess.run(
            ['git', 'pull'],
            cwd=str(repo_path),
            check=True,
            capture_output=True
        )

    def _create_repository_entity(self, repo_config, repo_path):
        """Create Repository node in Neo4j"""
        # Get git info
        try:
            # Get last commit
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H|%an|%at'],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash, author, timestamp = result.stdout.strip().split('|')
        except:
            commit_hash = None
            author = None
            timestamp = None

        repo_entity = {
            'name': repo_config['name'],
            'url': repo_config['url'],
            'language': repo_config.get('language', 'java'),
            'type': repo_config.get('type', 'application'),
            'description': repo_config.get('description', ''),
            'last_commit': commit_hash,
            'last_author': author,
            'last_updated': timestamp
        }

        # Create in Neo4j
        self.db.create_entity('repositories', repo_entity)

        logger.info(f"Created Repository entity: {repo_config['name']}")

    def _find_java_files(self, repo_path):
        """Find all Java files in repository"""
        java_files = []

        for root, dirs, files in os.walk(repo_path):
            # Skip directories matching patterns
            dirs[:] = [d for d in dirs if not self._should_skip(os.path.join(root, d))]

            for file in files:
                file_path = Path(root) / file

                # Check if Java file
                if file_path.suffix in JAVA_EXTENSIONS:
                    # Check if should skip
                    if not self._should_skip(file_path):
                        java_files.append(file_path)

        return java_files

    def _should_skip(self, path):
        """Check if path matches skip patterns"""
        path_str = str(path)

        for pattern in SKIP_PATTERNS:
            if fnmatch.fnmatch(path_str, pattern):
                return True

        return False

    def _parse_and_store_file(self, file_path, repo_name, repo_path):
        """Parse a Java file and store in Neo4j"""
        # Get relative path from repo root
        relative_path = file_path.relative_to(repo_path)

        # Parse the file
        result = self.java_parser.parse_file(file_path, repo_name)

        # Store entities
        self._store_entities(result['entities'], repo_name)

        # Store relationships
        self._store_relationships(result['relationships'])

    def _store_entities(self, entities, repo_name):
        """Store all entities in Neo4j"""
        # Store files
        for file_entity in entities['files']:
            self.db.create_entity('files', file_entity)

            # Create relationship: Repository CONTAINS File
            self.db.create_relationship('CONTAINS', {
                'from': repo_name,
                'from_type': 'repository',
                'to': file_entity['path'],
                'to_type': 'file'
            })

        # Store classes
        for class_entity in entities['classes']:
            self.db.create_entity('classes', class_entity)

        # Store interfaces
        for interface_entity in entities['interfaces']:
            self.db.create_entity('interfaces', interface_entity)

        # Store methods
        for method_entity in entities['methods']:
            self.db.create_entity('methods', method_entity)

        # Store exceptions (as simple nodes)
        for exception_name in entities['exceptions']:
            self.db.create_entity('exceptions', {
                'name': exception_name,
                'repository': repo_name
            })

        # Store annotations (as simple nodes)
        for annotation_name in entities['annotations']:
            self.db.create_entity('annotations', {
                'name': annotation_name,
                'repository': repo_name
            })

    def _store_relationships(self, relationships):
        """Store all relationships in Neo4j"""
        for rel_type, rels in relationships.items():
            for rel in rels:
                self.db.create_relationship(rel_type, rel)

    def close(self):
        """Close database connection"""
        self.db.close()