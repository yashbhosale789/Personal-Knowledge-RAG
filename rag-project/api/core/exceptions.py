from typing import Optional


class RAGException(Exception):
    # Base Exceptionfor all RAG API Errors.

    def __init__(
        self, message: str, status_code: int = 500, details: Optional[dict] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class PipelineNotReadyError(RAGException):
    def __init__(self, message: str = "RAG pipeline is not initialized."):
        super().__init__(message, status_code=503)


class ProviderError(RAGException):
    def __init__(self, message: str, provider: str, retries_exhausted: bool = False):
        super().__init__(
            message,
            status_code=502,
            details={"provider": provider, "retries_exhausted": retries_exhausted},
        )
        self.provider = provider
        self.retries_exhausted = retries_exhausted


class IngestError(RAGException):
    def __init__(self, message, file_path: str):
        super().__init__(message, status_code=422, details={"file_path": file_path})


class QueryValidationError(RAGException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
