"""Configuration for the canonical Product API client."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClientConfig:
    base_url: str
    access_token: str = ""
    api_version: str = "v1"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    user_agent: str = "zaicoder-client/1"

    def __post_init__(self) -> None:
        normalized = self.base_url.strip().rstrip("/")
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("base_url must use http or https")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if not self.api_version.strip():
            raise ValueError("api_version must not be empty")
        object.__setattr__(self, "base_url", normalized)

    def endpoint(self, path: str) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}/{self.api_version}{clean_path}"
