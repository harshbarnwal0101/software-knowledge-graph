from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

# Search for .env file in current dir, then parent dirs
def _find_env_file() -> str:
    current = Path(__file__).parent
    for _ in range(4):  # walk up up to 4 levels
        candidate = current / ".env"
        if candidate.exists():
            return str(candidate)
        current = current.parent
    return ".env"  # fallback


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change-me-to-a-random-secret"
    access_token_expire_minutes: int = 60 * 24  # 1 day

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://skguser:skgpassword@localhost:5432/software_knowledge_graph"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4jpassword"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # GitHub
    github_token: str = ""

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"]

    class Config:
        env_file = _find_env_file()
        extra = "ignore"


settings = Settings()
