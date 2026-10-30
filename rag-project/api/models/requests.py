from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

import config


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to answer using the RAG pipeline.",
        examples=["How do i change a tyre on an Aventro Motors Vehicle?"],
    )

    provider: Literal["groq", "openrouter", "gemini", "ollama"] | None = Field(
        default=None,
        description="Override the LLM Provider for this request. If not set, use PIPELINE_PROVIDER from config.",
        examples=["groq", "openrouter", "gemini", "ollama"],
    )

    return_contexts: bool = Field(
        default=True,
        description="Whether to include retrieved source chunks in the response.",
    )


class FeedbackRequest(BaseModel):
    # Nothing the client says about the answer is accepted: it comes from the server's grounding.
    model_config = ConfigDict(extra="forbid")

    request_id: UUID = Field(
        ..., description="The query_id from the /query response being rated."
    )

    rating: Literal["up", "down"] = Field(..., description="Thumbs up or down.")

    comment: str | None = Field(
        default=None,
        max_length=config.FEEDBACK_COMMENT_MAX_CHARS,
        description="Optional free text. Untrusted: stored as plain text, never put into prompts.",
    )


class IngestRequest(BaseModel):
    file_path: str = Field(
        ...,
        description="Absolute or relative path to the document to ingest.",
        examples=["/data/documents/manual.pdf"],
    )

    force_reingest: bool = Field(
        default=False,
        description="If true, re-ingest even if the document was previously processed.",
    )
