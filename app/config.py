"""
Secure RAG MVP — Application Configuration
Uses pydantic-settings to load from .env with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- LLM (Ollama) ---
    ollama_host: str = Field(default="http://ollama:11434", description="Ollama server URL")
    llm_model: str = Field(default="llama3.2:3b", description="LLM model name")
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model name")
    llm_context_window: int = Field(default=4096, description="Context window size")
    llm_temperature: float = Field(default=0.1, description="LLM temperature (lower = more deterministic)")

    # --- Storage ---
    chroma_persist_dir: str = Field(default="/app/data/chroma", description="ChromaDB persistence directory")
    sqlite_path: str = Field(default="/app/data/sqlite/app.db", description="SQLite database path")
    log_dir: str = Field(default="/app/data/logs", description="Log output directory")

    # --- Security ---
    trust_threshold: float = Field(default=0.7, description="Minimum trust score (0-1) for trusted collection")
    url_allowlist: str = Field(default="example.com,internal.company.com", description="Comma-separated allowed domains")
    custom_sensitive_patterns: str = Field(default="", description="Comma-separated custom sensitive regex patterns or keywords to redact")
    enable_ai_scanner: bool = Field(default=False, description="Whether to enable local LLM prompt injection verification")
    max_chunk_size: int = Field(default=500, description="Maximum chunk size in tokens")
    chunk_overlap: int = Field(default=50, description="Overlap between chunks")

    # --- Retrieval ---
    retrieval_top_k: int = Field(default=5, description="Number of chunks to retrieve")

    # --- API ---
    api_port: int = Field(default=8000, description="API server port")
    log_level: str = Field(default="INFO", description="Logging level")
    app_env: str = Field(default="development", description="Application environment")

    @property
    def url_allowlist_set(self) -> set:
        """Parse URL allowlist into a set."""
        return set(domain.strip() for domain in self.url_allowlist.split(",") if domain.strip())

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
