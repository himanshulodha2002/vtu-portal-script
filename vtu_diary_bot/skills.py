from __future__ import annotations

import re
from collections import defaultdict

ALLOWED_SKILLS = [
    "3D PRINTING CONCEPTS, DESIGN AND PRINTING",
    "Android Studio",
    "Angular",
    "AWS",
    "Azure",
    "BIM CONCEPTS WITH MEP AND PRODUCT DESIGN",
    "BIM FOR ARCHITECTURE",
    "BIM FOR CONSTRUCTION",
    "BIM FOR HIGHWAY ENGINEERING",
    "BIM FOR STRUCTURES",
    "C++",
    "CakePHP",
    "Cassandra",
    "Cloud access control",
    "CodeIgniter",
    "computer vision",
    "CSS",
    "D3.js",
    "Data encryption",
    "Data modeling",
    "Data visualization",
    "Database design",
    "Design with FPGA",
    "DevOps",
    "DHCP",
    "Digital Design",
    "Docker",
    "Embedded Systems",
    "FilamentPHP",
    "Firewall configuration",
    "Flutter",
    "Git",
    "Google Cloud",
    "HTML",
    "IaaS",
    "Indexing",
    "Intelligent Machines",
    "INTERIOR AND EXTERIOR DESIGN",
    "IoT",
    "Java",
    "JavaScript",
    "Keras",
    "Kotlin",
    "Kubernetes",
    "LAN",
    "Laravel",
    "Layout Design",
    "Machine learning",
    "Manufacturing",
    "MongoDB",
    "MySQL",
    "Natural language processing",
    "Network architecture",
    "Node.js",
    "NoSQL",
    "Objective-C",
    "PaaS",
    "PHP",
    "Physical Design",
    "PostgreSQL",
    "Power BI",
    "PRODUCT DESIGN & 3D PRINTING",
    "PRODUCT DESIGN & MANUFACTURING",
    "Python",
    "PyTorch",
    "React",
    "React.js",
    "Ruby on Rails",
    "SaaS",
    "scikit-learn",
    "SQL",
    "Statistical analysis",
    "Swift",
    "Tableau",
    "TCP/IP",
    "TensorFlow",
    "TypeScript",
    "Verification & Validations",
    "VLSI Design",
    "VPNs",
    "Vue.js",
    "WAN",
    "WordPress",
    "Xamarin",
    "Xcode",
]

ALLOWED_SKILL_SET = set(ALLOWED_SKILLS)

SOURCE_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("Python",),
    "django": ("Python",),
    "pytest": ("Python",),
    "celery": ("Python",),
    "fastapi": ("Python",),
    "mypy": ("Python",),
    "type hints": ("Python",),
    "django admin": ("Python",),
    "django rest framework": ("Python",),
    "rest apis": ("Python", "SQL"),
    "drf-spectacular": ("Python",),
    "json parsing": ("Python",),
    "code generation": ("Python",),
    "mocking": ("Python",),
    "bug fixing": ("Python",),
    "code reading": ("Python",),
    "aws": ("AWS",),
    "aws bedrock": ("AWS", "Natural language processing"),
    "boto3": ("AWS",),
    "git": ("Git",),
    "github": ("Git",),
    "postgresql": ("PostgreSQL",),
    "pgvector": ("PostgreSQL", "Machine learning"),
    "sql": ("SQL",),
    "docker": ("Docker",),
    "docker compose": ("Docker",),
    "redis": ("NoSQL",),
    "machine learning": ("Machine learning",),
    "xgboost": ("Machine learning",),
    "fasttext": ("Machine learning",),
    "pytorch": ("PyTorch",),
    "tensorflow": ("TensorFlow",),
    "rag": ("Natural language processing", "Machine learning"),
    "agentic ai": ("Natural language processing", "Machine learning"),
    "llm strategy": ("Natural language processing",),
    "llm prompt engineering": ("Natural language processing",),
    "langfuse": ("Natural language processing",),
    "llm tracing": ("Natural language processing",),
    "llm observability": ("Natural language processing",),
    "claude": ("Natural language processing",),
    "titan embeddings": ("Natural language processing",),
    "data modeling": ("Data modeling",),
    "data analysis": ("Statistical analysis",),
    "statistics": ("Statistical analysis",),
    "numerical methods": ("Statistical analysis",),
    "power bi": ("Power BI",),
    "observability": ("Data visualization",),
    "security": ("Data encryption",),
    "security & compliance": ("Data encryption", "Cloud access control"),
    "soc 2": ("Cloud access control",),
    "gdpr": ("Data encryption",),
    "dev experience": ("DevOps",),
    "release management": ("DevOps",),
    "terraform": ("DevOps", "AWS"),
    "performance optimization": ("Python",),
    "html processing": ("HTML",),
    "react": ("React",),
    "typescript": ("TypeScript",),
    "javascript": ("JavaScript",),
    "node.js": ("Node.js",),
    "customer research": ("Data modeling",),
    "metrics": ("Statistical analysis",),
    "caching": ("NoSQL",),
}

TEXT_HINTS: dict[str, tuple[str, ...]] = {
    "AWS": ("aws", "bedrock", "iam", "kms", "cloud", "s3", "ec2"),
    "Cloud access control": ("soc 2", "gdpr", "access control", "compliance", "permissions", "iam"),
    "Data encryption": ("pii", "encryption", "redaction", "security", "gdpr", "soc 2"),
    "Data modeling": ("data model", "schema", "jsonb", "migration", "priorityscheme", "model spec"),
    "Data visualization": ("dashboard", "visualization", "analytics", "observability", "report"),
    "Database design": ("database design", "schema docs", "schema", "postgres schema"),
    "DevOps": ("dev setup", "one-click setup", "docker compose", "deployment", "release", "ci", "pre-commit"),
    "Docker": ("docker", "compose", "container"),
    "Git": ("git", "github", "pull request", "pr ", "review comments", "merged"),
    "Machine learning": ("machine learning", "model", "classifier", "xgboost", "fasttext", "evaluation", "confidence score"),
    "Natural language processing": ("llm", "prompt", "claude", "language", "rag", "embedding", "embeddings", "langfuse", "ticket summarization", "agentic ai"),
    "NoSQL": ("redis", "cassandra", "mongodb", "cache"),
    "Node.js": ("node.js",),
    "PostgreSQL": ("postgres", "postgresql", "jsonb"),
    "Power BI": ("power bi",),
    "PyTorch": ("pytorch",),
    "Python": ("python", "django", "fastapi", "celery", "pytest", "mypy", "management command", "serializer", "drf"),
    "React": ("react",),
    "SQL": ("sql", "query", "queries", "migration", "index", "indexing"),
    "Statistical analysis": ("metrics", "analysis", "accuracy", "cost model", "statistics", "quantitative"),
    "TensorFlow": ("tensorflow",),
    "TypeScript": ("typescript",),
}


def normalize_skill_name(value: str) -> str:
    return re.sub(r"[^a-z0-9+]+", " ", value.strip().lower()).strip()


def _append_unique(target: list[str], values: tuple[str, ...] | list[str] | str) -> None:
    if isinstance(values, str):
        values = [values]
    for value in values:
        if value in ALLOWED_SKILL_SET and value not in target:
            target.append(value)


def infer_skills(source_skills: list[str], *text_fragments: str, limit: int = 3) -> list[str]:
    selected: list[str] = []
    for skill in source_skills:
        normalized = normalize_skill_name(skill)
        if skill in ALLOWED_SKILL_SET:
            _append_unique(selected, skill)
            continue
        aliases = SOURCE_SKILL_ALIASES.get(normalized)
        if aliases:
            _append_unique(selected, aliases)
        elif normalized in {normalize_skill_name(item) for item in ALLOWED_SKILLS}:
            exact = next(item for item in ALLOWED_SKILLS if normalize_skill_name(item) == normalized)
            _append_unique(selected, exact)

    text = " ".join(fragment for fragment in text_fragments if fragment).lower()
    scores: dict[str, int] = defaultdict(int)
    for skill, hints in TEXT_HINTS.items():
        for hint in hints:
            if hint in text:
                scores[skill] += 2 if " " in hint else 1

    for skill, _score in sorted(scores.items(), key=lambda item: (-item[1], item[0])):
        _append_unique(selected, skill)

    if not selected:
        selected.append("Python")
    return selected[:limit]

