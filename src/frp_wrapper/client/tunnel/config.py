"""Tunnel configuration model."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TunnelConfig(BaseModel):
    """Configuration for creating and managing tunnels."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    server_host: str = Field(min_length=1, description="FRP server hostname")
    auth_token: str | None = Field(None, description="Authentication token")
    default_domain: str | None = Field(
        None, description="Default domain for HTTP tunnels"
    )
    max_tunnels: int = Field(
        default=10, ge=1, le=100, description="Maximum concurrent tunnels"
    )

    @field_validator("server_host")
    @classmethod
    def validate_server_host(cls, v: str) -> str:
        """Validate server hostname format."""
        if not v.replace(".", "").replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Hostname must contain only alphanumeric characters, dots, hyphens, and underscores"
            )
        return v
