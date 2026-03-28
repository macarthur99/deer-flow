from typing import Literal
from pydantic import BaseModel, Field


class CitationVerificationConfig(BaseModel):
    """Configuration for citation verification middleware."""

    enabled: bool = Field(default=False, description="Enable citation verification")
    strictness: Literal["off", "warn", "strict"] = Field(default="warn", description="Verification strictness level")
    long_text_threshold: int = Field(default=1000, description="Character count threshold for long text warnings")
    tracked_tools: list[str] = Field(
        default=["web_search", "web_fetch", "jina_fetch"],
        description="Tool names to track for citation verification"
    )
