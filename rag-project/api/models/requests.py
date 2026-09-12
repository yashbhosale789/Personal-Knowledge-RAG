from pydantic import BaseModel, Field
from typing import Optional, Literal


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to answer using the RAG pipeline.",
        examples=["How do i change a tyre on an Aventro Motors Vehicle?"],
    )

    provider: Optional[Literal["groq", "openrouter", "gemini", "ollama"]] = Field(
        default=None,
        description="Override the LLM Provider for this request. If not set, use PIPELINE_PROVIDER from config.",
        examples=["groq", "openrouter", "gemini", "ollama"],
    )

    return_contexts: bool = Field(
        default=True,
        description="Whether to include retrieved source chunks in the response.",
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
