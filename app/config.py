# app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr


class Settings(BaseSettings):
    """
    Centralized application settings loaded from environment or .env file.
    """

    # ─── Directory to watch for new files ───────────────────────────────────────
    watch_dir: str = Field(default="/data/incoming", env="WATCH_DIR")

    # ─── Vector DB connection ───────────────────────────────────────────────────
    vector_db_url: str = Field(..., env="VECTOR_DB_URL")

    # ─── LLM Router endpoint & auth ────────────────────────────────────────────
    router_url: str = Field(default="http://localhost:8080/v1/embeddings", env="ROUTER_URL")
    llm_router_api_key: SecretStr = Field(..., env="LLM_ROUTER_API_KEY")

    # ─── Chunker parameters ─────────────────────────────────────────────────────
    chunk_size: int = Field(default=500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")

    # ─── HTTP timeouts (seconds) ───────────────────────────────────────────────
    token_timeout: float = Field(default=10.0, env="TOKEN_TIMEOUT")
    embed_timeout: float = Field(default=60.0, env="EMBED_TIMEOUT")

    class Config:
        # Load from `.env` in the project root
        env_file = ".env"
        env_file_encoding = "utf-8"


# instantiate a singleton for import elsewhere
settings = Settings()
