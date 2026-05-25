"""Pydantic models for Clipper Agency configuration."""

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    """OpenRouter LLM routing configuration."""

    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048


class SafetyConfig(BaseModel):
    """Safety gate configuration."""

    enabled: bool = True
    blocked_categories: list[str] = Field(default_factory=lambda: ["politics", "religion", "nsfw"])


class NicheConfig(BaseModel):
    """Niche profile — content rules and constraints."""

    name: str
    language: str = "id"
    tone: str = "casual_tiktok"
    video_length: dict = Field(default_factory=lambda: {"target": 30, "hard_limit": 60})
    safety_rules: list[str] = Field(default_factory=list)


class TemplateConfig(BaseModel):
    """Video template configuration."""

    name: str
    type: str  # news_card | b_roll_narration | rapid_update
    duration: int = 30
    assets_required: list[str] = Field(default_factory=list)


class AppSettings(BaseSettings):
    """Application-level settings loaded from .env / environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API keys
    openrouter_api_key: str = ""
    elevenlabs_api_key: str = ""
    pexels_api_key: str = ""
    firecrawl_api_key: str = ""
    scrapecreators_api_key: str = ""

    # Paths
    data_dir: Path = Field(default=Path("data"))
    assets_cache: Path = Field(default=Path("assets/cache"))
    output_dir: Path = Field(default=Path("outputs"))

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///data/clipper.db")

    # Default LLM
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # Debug / dev
    debug: bool = False
    dry_run: bool = False
