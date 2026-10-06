"""Environment configuration. Secrets never appear in diagnostics."""

from pathlib import Path

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    openai_api_key: SecretStr | None = None
    openai_model_extract: str = ""
    openai_model_reason: str = ""
    openai_model_transcribe: str = ""
    openai_model_image: str = ""
    openai_model_embed: str = ""
    openai_router_effort: str = "none"
    openai_composer_effort: str = "low"
    openai_schema_warmup: bool = True
    cors_origins: list[str] = []
    content_policy_path: Path = ROOT / "api/policy/content_policy.yaml"
    tuning_path: Path = ROOT / "api/tuning.yaml"
    build_sha: str = ""
    render_git_commit: str = ""
    health_only: bool = False
    allow_pending_review: bool = False
    private_corpus_path: Path | None = None
    private_hadith_path: Path | None = None
    private_short_index_dir: Path | None = None
    private_bayyinat_sha256: str = ""
    private_glossary_sha256: str = ""
    corpus_manifest_path: Path = ROOT / "corpus/manifest.json"
    islamic_content_mcp_url: str = "https://mcp.islamiccontent.org/mcp"
    enable_islamic_content_mcp: bool = False

    @field_validator("islamic_content_mcp_url")
    @classmethod
    def fixed_mcp_endpoint(cls, value: str) -> str:
        if value not in {"", "https://mcp.islamiccontent.org/mcp"}:
            raise ValueError("ISLAMIC_CONTENT_MCP_URL must be the approved endpoint")
        return value

    @model_validator(mode="after")
    def default_build_sha(self) -> "Settings":
        # Render sets RENDER_GIT_COMMIT on every deploy; BUILD_SHA overrides it when set.
        if not self.build_sha:
            self.build_sha = self.render_git_commit[:7] or "unknown"
        return self

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins")
        return origins

    def require_key(self) -> None:
        if self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip():
            raise RuntimeError("OPENAI_API_KEY is required; set it in the environment")
