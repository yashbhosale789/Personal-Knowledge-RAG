import json
import logging 

from src.llm.client import call_llm
from config import CITATION_VERIFIER_SYSTEM, EVAL_PROVIDER

logger = logging.getLogger(__name__)