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
RRF_K = 60

# Chroma
CHROMA_COLLECTION = "personal_kb"

# LLM
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"        # Use till it expires
# OPENROUTER_MODEL = "inclusionai/ling-3.0-flash:free"            # second option
