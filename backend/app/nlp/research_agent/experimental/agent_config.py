"""
DeepAgents Configuration

Configuration for the qualitative research agent including LLM settings,
tools, and agent behavior.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for the research agent."""

    # LLM Configuration
    model: str = Field(default="gpt-4", description="LLM model to use")
    temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="LLM temperature"
    )
    max_tokens: int = Field(
        default=4000, gt=0, description="Maximum tokens per response"
    )

    # Agent Behavior
    timeout_seconds: int = Field(
        default=300, gt=0, description="Agent timeout in seconds"
    )
    retry_attempts: int = Field(default=3, ge=0, description="Number of retry attempts")

    # Caching
    cache_ttl_hours: int = Field(
        default=168, gt=0, description="Cache TTL in hours (default: 7 days)"
    )

    # Cost Management
    max_cost_per_report_usd: float = Field(
        default=0.50, gt=0, description="Maximum cost per report"
    )

    class Config:
        frozen = True


# Default configuration
DEFAULT_CONFIG = AgentConfig()


# TODO: Implement agent initialization
# from deepagents import Agent
#
# def create_research_agent(config: AgentConfig = DEFAULT_CONFIG) -> Agent:
#     """Create and configure a research agent."""
#     pass
