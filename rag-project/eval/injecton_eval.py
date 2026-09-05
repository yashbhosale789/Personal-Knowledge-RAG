import json
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent.parent))

from src.pipeline.advanced_rag import _build_prompt
from src.llm.client import call_llm
from config import SYSTEM_PROMPT