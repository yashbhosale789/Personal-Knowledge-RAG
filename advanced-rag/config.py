from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "documents"
STORAGE_DIR = BASE_DIR / "storage" / "chroma"

# Enbeddings
EMBEDDINGS_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIAMENSION = 384  # bge small output size

# Chunking
CHUNK_SIZE = 512  # tokens (approximate — we use character count)
CHUNK_OVERLAP = 64  # overlap between adjacent chunks
CHUNKS_PATH = BASE_DIR / "storage" / "chunks.json"  # Storage

# Retrival
TOP_K = 5  # number of chunks to retrieve
RRF_K = 60  # Number of Reciprocal Rank Fusion to retrieve
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2" 

# Chroma
CHROMA_COLLECTION = "personal_kb"

# LLM
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"        # Use till it expires
# OPENROUTER_MODEL = "inclusionai/ling-3.0-flash:free"            # second option

# PROMPTS

REWRITE_SYSTEM = """You are a search query optimizer.
Your job is to rewrite a user's conversational question into a precise, self-contained search query.

Rules:
- Remove conversational filler (what did you say, can you tell me, etc.)
- Expand abbreviations and resolve ambiguous pronouns
- Make the query document-shaped — use the terminology that would appear in an answer
- Return ONLY the rewritten query. No explanation. No punctuation at the end."""

SYSTEM_PROMPT = """You are a precise question-answering assistant.
You answer questions strictly based on the provided context.
If the context does not contain enough information to answer the question, 
say "I don't have enough information in my knowledge base to answer this."
Do not use any knowledge outside the provided context."""
