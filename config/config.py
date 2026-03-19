import os

REPOSITORIES = [
    {
        'name': 'spring-petclinic',
        'url': 'https://github.com/spring-projects/spring-petclinic.git',
        'language': 'java',
        'type': 'application',
        'description': 'Spring Boot sample application'
    },
    {
        'name': 'spring-boot-examples',
        'url': 'https://github.com/ityouknow/spring-boot-examples.git',
        'language': 'java',
        'type': 'examples',
        'description': 'Spring Boot examples and tutorials'
    },
]

# Neo4j connection settings (can be overridden by environment variables)
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

CLONE_DIR = "./repos"  # Where to clone repos
SKIP_PATTERNS = [
    '*/test/*',
    '*/tests/*',
    '*Test.java',
    '*Tests.java',
    '*/target/*',
    '*/build/*',
    '*/node_modules/*',
    '*.class',
    '*.jar'
]

# File extensions to parse
JAVA_EXTENSIONS = ['.java']