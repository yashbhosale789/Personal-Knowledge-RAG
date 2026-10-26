import logging
import os
import secrets

from langchain_core.documents import Document

from config import ABSTAIN_MESSAGE, ANSWER_TEMPLATE, SYSTEM_PROMPT, TOP_K
from src.llm import usage
from src.llm.client import call_llm
from src.observability import timed
from src.pipeline.citation_verification import verify_citation
from src.pipeline.confidence import score_confidence
from src.pipeline.context_sufficiency import check_sufficiency
from src.pipeline.query_rewriter import rewrite_query
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.reranker import CrossEncoderReranker
from src.retrieval.retriever import retrieve

logger = logging.getLogger(__name__)

# Built lazily on first use (or by warmup() at app startup) — models are expensive
# to reload per request, and importing this module must not load them (F-05).
_bm25: BM25Retriever | None = None
_reranker: CrossEncoderReranker | None = None


def get_bm25() -> BM25Retriever:
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Retriever()
    return _bm25


def get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def warmup() -> None:
    """Builds the BM25 index and loads the reranker so the first request is not cold."""
    get_bm25()
    get_reranker()


def _dense_to_dicts(documents: list[Document], top_k: int) -> list[dict]:
    """
    Converts LangChain Documents to the dict format used by RRF and reranker.
    Adds rank so RRF can treat dense results the same as BM25 results.
    """

    return [
        {
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": 0.0,  # cosine score not exposed by LangChain similarity_search
            "rank": rank,
        }
        for rank, doc in enumerate(documents[:top_k])
    ]


def _build_prompt(query: str, chunks: list[dict]) -> str:
    boundary = secrets.token_hex(4)

    context_blocks = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk["metadata"].get("filename", "unknown")
        block = f"[SOURCE {i} - {source}]\n{chunk['text']}"
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)

    return ANSWER_TEMPLATE.format(boundary=boundary, context=context, query=query)


def retrieve_context(
    query: str, top_k: int = TOP_K, reranker: CrossEncoderReranker | None = None
) -> dict[str, list[dict]]:
    """Stages 2-4: dense + BM25 -> RRF -> rerank. Returns every stage so eval can inspect them."""
    with timed("dense_retrieve"):
        dense = _dense_to_dicts(retrieve(query, top_k=top_k * 4), top_k * 4)
    with timed("bm25"):
        bm25 = get_bm25().retrieve(query, top_k=top_k * 4)
    with timed("fusion"):
        fused = reciprocal_rank_fusion(ranked_lists=[dense, bm25], top_k=top_k * 2)
    with timed("rerank"):
        reranked = (reranker or get_reranker()).rerank(query, candidates=fused)
    return {"dense": dense, "bm25": bm25, "fused": fused, "reranked": reranked}


def run_advanced_rag_pipeline(
    query: str,
    top_k: int = TOP_K,
    return_contexts: bool = False,
    provider: str | None = None,
    rewritten: str | None = None,
) -> dict:
    """
    Advanced RAG pipeline:
    query → rewrite → dense + BM25 → RRF fusion → rerank → prompt → LLM

    The result carries `llm_usage`: tokens and latency of every LLM call it made.
    """
    with usage.track() as calls:
        result = _run(query, top_k, return_contexts, provider, rewritten)
    result["llm_usage"] = usage.summarize(calls)
    return result


def _run(
    query: str,
    top_k: int,
    return_contexts: bool,
    provider: str | None,
    rewritten: str | None,
) -> dict:

    logger.info(f"Advanced RAG pipeline started for : {query[:60]}")

    # Stage 1: Query rewriting
    rewritten = rewritten or rewrite_query(query, provider=provider)

    # Stages 2-4: hybrid retrieval -> RRF fusion -> rerank
    reranked = retrieve_context(rewritten, top_k=top_k)["reranked"]

    if not reranked:
        return {
            "answer": "No relevant documents found in the knoweldge base.",
            "sources": [],
            "chunks_used": 0,
            "query": query,
            "rewritten_query": rewritten,
        }

    # Stage 4.5: Context sufficiency gate
    sufficiency = check_sufficiency(rewritten, reranked, provider=provider)
    if not sufficiency["sufficient"]:
        logger.info(
            f"Sufficiency gate blocked generation (tier={sufficiency['tier']}, reason={sufficiency['reason']})"
        )

        result = {
            "answer": ABSTAIN_MESSAGE,
            "sources": list(
                dict.fromkeys(
                    os.path.basename(c["metadata"].get("filename", "unknown"))
                    for c in reranked
                )
            ),
            "chunks_used": len(reranked),
            "query": query,
            "rewritten_query": rewritten,
            "sufficiency": sufficiency,
            "outcome": "abstain",
        }

        if return_contexts:
            result["contexts"] = [c["text"] for c in reranked]
        return result

    # Stage 5: Prompt + LLM
    prompt = _build_prompt(rewritten, reranked)
    answer = call_llm(prompt, system=SYSTEM_PROMPT, provider=provider, stage="generate")
    answer = answer.replace("【", "[").replace("】", "]")

    # Stage 5.5: Citation Verification
    citation_check = verify_citation(answer, reranked)

    # Stage 5.75: Confidence
    confidence = score_confidence(citation_check)

    if confidence["caveat"]:
        answer = answer + confidence["caveat"]

    if confidence["confidence"] == "low":
        outcome = "answer_low_confidence"
    else:
        outcome = "answer"

    logger.info("Advanced RAG pipeline complete.")

    result = {
        "answer": answer,
        "sources": list(
            dict.fromkeys(
                os.path.basename(c["metadata"].get("filename", "unknown"))
                for c in reranked
            )
        ),
        "chunks_used": len(reranked),
        "query": query,
        "rewritten_query": rewritten,
        "sufficiency": sufficiency,
        "citation_check": citation_check,
        "confidence": confidence["confidence"],
        "outcome": outcome,
    }

    if return_contexts:
        result["contexts"] = [c["text"] for c in reranked]

    return result
